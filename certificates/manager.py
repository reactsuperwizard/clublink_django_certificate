import logging
logger = logging.getLogger(__name__)

from urllib.parse import urljoin

from dicttoxml import dicttoxml
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from raven.contrib.django.raven_compat.models import client as raven_client
from django.db import transaction

from raven.contrib.django.raven_compat.models import client as raven_client

from clublink.certificates.models import (
    Certificate,
    CertificateBatch,
    CertificateGroup,
    CertificateType,
    DepartmentCertificateType
)
from .constants import DOLLAR_VALUE_CATEGORIES

class CertificatesManager(object):

    def _generate_certificate_batch_xml (self, client, batch, **kwargs):
        """Generates XML for a certificate batch."""
        ignore_cache = kwargs.get ('ignore_cache', False)
        batch_date = kwargs.get ('batch_date', batch.created)

        # Get the tender methods for the department
        TENDER_METHODS_CACHE_KEY = 'tender_methods_department_{}'.format (batch.department.id)
        tender_methods = cache.get (TENDER_METHODS_CACHE_KEY) if not ignore_cache else None

        if not tender_methods:
            tender_methods = client.get_tender_methods_for_department (batch.department)
            cache.set (TENDER_METHODS_CACHE_KEY, tender_methods, 1800)

        default_employee = settings.DEFAULT_CERTIFICATE_EMPLOYEE_NUMBER

        # Generate Items and Tenders XML and tax amount
        items = []
        tenders = {}
        for certificate in batch.certificates.order_by ('created'):
            dct = DepartmentCertificateType.objects.get (
                department=batch.department, certificate_type=certificate.type)

            if certificate.club.state == 'QC':
                tax_rate = 0.14975
            else:
                tax_rate = 0.13

            if certificate.type.category in DOLLAR_VALUE_CATEGORIES:
                price = float (certificate.quantity)

                if certificate.type.category == CertificateType.RAIN_CHECK_CATEGORY:
                    certificate.tax = round (price * tax_rate, 2)
                    certificate.save ()
                    price += certificate.tax
            else:
                price = 0.01 * int (certificate.quantity)

            if certificate.type.category == CertificateType.RAIN_CHECK_CATEGORY:
                tender_amount = price - certificate.tax
            else:
                tender_amount = price

            items.append ({
                'uidInvItemID': dct.guid,
                'Price': round (price, 2),
                'Quantity': 1,
                'Purchaser': batch.account_number,
                'Receiver': batch.recipient_name,
                'CertificateNumber': certificate.code,
            })

            tender_id = ''
            for t in tender_methods:
                if certificate.type.category == CertificateType.PRESTIGE_50_CATEGORY:
                    if t['Name'] == 'Prestige $50 Activation':
                        tender_id = t['guid']
                        break
                elif certificate.type.category == CertificateType.RAIN_CHECK_CATEGORY:
                    if t['Name'] == 'Rain Credit Issued':
                        tender_id = t['guid']
                        break
                elif certificate.type.category in DOLLAR_VALUE_CATEGORIES:
                    if t['Procedure'] == 'Member':
                        tender_id = t['guid']
                        break
                else:
                    if t['Name'] == 'Comp Round Certificate Activation':
                        tender_id = t['guid']
                        break

            if tender_id in tenders:
                tenders[tender_id] += tender_amount
            else:
                tenders[tender_id] = tender_amount

            # Tax tenders
            if certificate.type.category == CertificateType.RAIN_CHECK_CATEGORY:
                tender_id = ''

                for t in tender_methods:
                    if certificate.club.state == 'QC':
                        if t['Name'] == 'Rain Credit Issued QST':
                            tender_id = t['guid']
                            break
                    else:
                        if t['Name'] == 'Rain Credit Issued HST':
                            tender_id = t['guid']
                            break

                if tender_id in tenders:
                    tenders[tender_id] += certificate.tax
                else:
                    tenders[tender_id] = certificate.tax

        tender_objects = []
        for id in tenders.keys ():
            tender_objects.append ({
                'uidTenderID': id,
                'TenderAmount': round (tenders[id], 2),
            })

        items_xml = dicttoxml (
            items, root=False, attr_type=False, item_func=lambda x: 'Items').decode ()

        tenders_xml = dicttoxml (
            tender_objects, root=False, attr_type=False, item_func=lambda x: 'Tenders').decode ()

        batch_details = {
            'EmplNumber': batch.creator.employee_number or default_employee,
            'MemberNumber': batch.account_number,
            'MemberExtension': '000',
            'TranID': 'Certificate Batch Transaction: {}'.format (batch.pk),
        }

        batch = {
            'Root': {
                'Details': {
                    'BatchName': 'Certificate Batch {}'.format (batch.pk),
                    'BatchDate': timezone.localtime (batch_date).strftime ('%-m/%-d/%Y'),
                    'DeptNumber': batch.department.number,
                    'BatchDetails': batch_details,
                }
            }
        }

        # Construct batch XML string
        batch_xml = dicttoxml (batch, root=False, attr_type=False).decode ()
        batch_xml = batch_xml.replace ('</BatchDetails>', '{}</BatchDetails>'.format (items_xml))
        batch_xml = batch_xml.replace ('</BatchDetails>', '{}</BatchDetails>'.format (tenders_xml))

        return batch_xml

    def _register_certificate_batch (self, client, batch, **kwargs):
        """Create a ticket for the certificate batch."""
        batch_xml = self._generate_certificate_batch_xml(client, batch, **kwargs)

        raven_client.context.merge ({
            'extra': {
                'xml_batch': batch_xml,
            }
        })

        return client.create_ticket(batch_xml=batch_xml)

    def _create_certificate (self, batch, certificate_data):
        """Creates the certificate objects."""
        with transaction.atomic ():
            certificate = Certificate.objects.create (batch=batch, **certificate_data)

        return certificate

    def create_certificate_batch (self, request, batch_data, certificate_data):
        """Creates the certificate objects."""
        with transaction.atomic ():
            batch = CertificateBatch.objects.create (creator=request.user, **batch_data)

            self._create_certificate(batch, certificate_data)
        return batch

    def register_certificate (self, ibs_client, batch):
        errors = []

        # Start from the default scenario
        status = False

        try:
            raven_client.context.activate ()

            response = self._register_certificate_batch (ibs_client, batch)

            logger.info ('Certificate batch response',
                             extra={
                                 'response': response
                             }
                         )

            status = response['CreateTicketsResult']

            if status is False:
                if 'a_sMessage' in response:
                    try:
                        message = ElementTree.fromstring (response['a_sMessage'])
                    except ElementTree.ParseError:
                        errors.append (response['a_sMessage'])
                    else:
                        for child in message:
                            if child.tag == 'Error':
                                errors.append (child.find ('ErrorMessage').text)

                    raven_client.context.merge ({
                        'extra': {
                            'response': response,
                        }
                    })

                    raven_client.captureMessage ('Certificate creation failed.')
                    raven_client.context.clear ()

        except Exception as exc:
            logger.exception (
                'Register certificate exception'
            )
            status = False
            errors = ['An unknown error occured during certificate registration.']
            if settings.DEBUG:
                print(exc)
            raven_client.captureException ()

        return (status, errors)

    def send_certificate_batch_email(self, batch, delay=None, **kwargs):
        download_url = urljoin(getattr(settings, 'GIFT_CERTIFICATE_SITE_URL'),
                               reverse('download', urlconf='clublink.urls.gc', args=[batch.download_code]))

        subject = _ ('ClubLink Certificate')

        context = {
            'name': batch.recipient_name,
            'signature': batch.email_signature,
            'subject': subject,
            'download_url': download_url,
        }

        message = render_to_string (
            'certificates/emails/certificate-{}.txt'.format (batch.language), context=context)
        message_html = render_to_string (
            'certificates/emails/certificate-{}.jinja'.format (batch.language), context=context)

        bcc = []
        if not kwargs.get ('skip_bcc', False):
            if batch.department.director_email:
                bcc.append (batch.department.director_email)

            if batch.creator.email:
                bcc.append (batch.creator.email)

        to = [kwargs.get ('recipient_email', batch.recipient_email)]


        if delay:
            from clublink.celery import send_email_later
            body = message
            send_email_later.apply_async(
                countdown=delay,
                kwargs={
                    'subject':subject,
                    'body':message,
                    'to':to,
                    'bcc':bcc,
                    'from_email':'ClubLink <{}>'.format(
                        getattr(settings, 'GIFT_CERTIFICATE_EMAIL_ADDRESS')),
                    'message_html': message_html
                }
            )

        else:
            email = EmailMultiAlternatives (
                subject=subject, body=message, to=to, bcc=bcc,
                from_email='ClubLink <{}>'.format (getattr (settings, 'GIFT_CERTIFICATE_EMAIL_ADDRESS')))

            email.attach_alternative (message_html, 'text/html')

            email.send()