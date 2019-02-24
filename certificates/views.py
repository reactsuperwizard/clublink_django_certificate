import base64
import decimal
import time
import zipfile
import logging

logger = logging.getLogger(__name__)

from collections import OrderedDict
from io import BytesIO
from smtplib import SMTPException
from urllib.parse import quote
from xml.etree import ElementTree

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    login as auth_login,
    logout as auth_logout,
    REDIRECT_FIELD_NAME
)
from django.core.cache import cache
from django.db import transaction
from django.db.models import Value, Q
from django.db.models.functions import Concat
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render, resolve_url, reverse
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.views.defaults import page_not_found, permission_denied
from raven.contrib.django.raven_compat.models import client as raven_client

from clublink.base.clients.ibs import WebMemberClient
from clublink.base.decorators import staff_required
from clublink.certificates.decorators import ip_whitelist_only
from clublink.certificates.forms import CertificateForm, RecipientForm
from clublink.certificates.models import (
    Certificate,
    CertificateBatch,
    CertificateGroup,
    CertificateType
)
from clublink.certificates.utils import register_certificate_batch, send_certificate_batch_email
from clublink.users.forms import LoginForm
from clublink.users.models import User


def login(request):
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')

    # Ensure the user-originating redirection URL is safe.
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = resolve_url(getattr(settings, 'GC_LOGIN_REDIRECT_URL', reverse('home')))
    form = LoginForm()

    if request.user.is_authenticated:
        if redirect_to == request.path:
            return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))
        return redirect(redirect_to)
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect(redirect_to)

    return render(request, 'certificates/login.jinja', {'form': form})


def logout(request):
    auth_logout(request)
    return redirect(reverse('login'))


@staff_required
@ip_whitelist_only
def step1(request):
    form = RecipientForm(request.user, request.session.get('gc_step1_data'))
    users = None

    if request.method == 'POST':
        if 'reload' in request.POST:
            form = RecipientForm(request.user, initial=request.POST)
        elif 'reset' in request.POST:
            if 'gc_step1_data' in request.session:
                del request.session['gc_step1_data']
            return redirect(reverse('step1'))
        elif 'lookup' in request.POST or 'select_user' in request.POST:
            data = request.POST.copy()

            if 'lookup' in request.POST:
                queries = []
                account_number = request.POST.get('account_number')
                account_name = request.POST.get('account_name')

                if account_number:
                    queries.append(Q(membership_number=account_number))

                if account_name:
                    queries.append(Q(full_name__icontains=account_name))

                if queries:
                    query = queries.pop()
                    for f in queries:
                        query |= f

                    users = User.objects.annotate(
                        full_name=Concat('first_name', Value(' '), 'last_name'))
                    users = users.filter(query)
            elif 'select_user' in request.POST:
                users = User.objects.filter(id=request.POST.get('select_user'))

            if users and users.count() == 1:
                user = users.first()
                data['account_number'] = user.membership_number
                data['account_name'] = user.get_full_name()
                data['recipient_email'] = user.email
                data['recipient_name'] = user.first_name

            form = RecipientForm(request.user, initial=data)
        else:
            form = RecipientForm(request.user, request.POST, request=request)
            if form.is_valid():
                data = form.cleaned_data
                request.session['gc_step1_data'] = request.POST.copy()
                request.session['gc_step1_data']['account_number'] = data['account_number']
                return redirect(reverse('step2'))

    return render(request, 'certificates/step1.jinja', {'form': form, 'users': users})


@staff_required
@ip_whitelist_only
def preview(request, pk):
    try:
        certificate = Certificate.objects.get(pk=pk)
    except Certificate.DoesNotExist:
        certificate = get_object_or_404(Certificate, code=pk)
    response = HttpResponse(content_type='application/pdf')
    response.write(certificate.generate_pdf())
    return response


@method_decorator(staff_required, name='dispatch')
@method_decorator(ip_whitelist_only, name='dispatch')
class Step2View(View):
    department = None
    groups = None
    recipient_form = None
    ibs_client = None
    forms = OrderedDict()

    def _get_normalized_form_data(self, form, key):
        """Gets a dict of form data with normalized field names."""
        data = {} if form.data else form.initial
        prefix = 'gc{}-'.format(key)

        for field_name in form.data:
            normalized_field_name = field_name[len(prefix):]

            if field_name in form.data and field_name.startswith(prefix) and form.data[field_name]:
                data[normalized_field_name] = form.data[field_name]

        for field_name in data:
            if field_name == 'quantity':
                data[field_name] = str(data[field_name])

        return data

    def _forms_to_session_data(self, forms):
        """Converts an ordered dict of forms to a list of data to be stored in the session."""
        session_data = []

        for key in forms:
            data = self._get_normalized_form_data(forms[key], key)

            # Store a key/data pair in the session data
            session_data.append([str(key), data])

        return session_data

    def _create_certificate_form(self, user, department, data=None, index=1, key=None):
        """Creates a new certificate form."""
        key = key or time.time()
        form = CertificateForm(user, department, data, prefix='gc{}'.format(key), index=index)
        return key, form

    def _session_data_to_forms(self, user, department, session_data):
        """Converts session data to an ordered dict of forms."""
        forms = OrderedDict()

        if not session_data:
            key, form = self._create_certificate_form(user, department)
            forms.update({key: form})
        else:
            for index, (key, form_data) in enumerate(session_data):
                for data_key in form_data:
                    if data_key == 'quantity':
                        try:
                            form_data[data_key] = decimal.Decimal(form_data[data_key])
                        except decimal.InvalidOperation:
                            form_data[data_key] = ''

                form = CertificateForm(user, department, initial=form_data,
                                       prefix='gc{}'.format(key), index=index + 1)
                forms.update({key: form})

        return forms

    def _create_certificate_batch(self, request):
        """Creates the certificate objects."""
        with transaction.atomic():
            batch = CertificateBatch.objects.create(
                creator=request.user, **self.recipient_form.cleaned_data)

            # Create certificates
            for key in self.forms:
                Certificate.objects.create(batch=batch, **self.forms[key].cleaned_data)

        return batch

    def _register_certificates(self, batch):
        errors = []

        # Start from the default scenario
        status = False

        try:
            raven_client.context.activate()

            response = register_certificate_batch(self.ibs_client, batch)

            logger.info('Certificate batch response',
            extra={
                'response': response
            }
            )

            status = response['CreateTicketsResult']

            if status is False:
                if 'a_sMessage' in response:
                    try:
                        message = ElementTree.fromstring(response['a_sMessage'])
                    except ElementTree.ParseError:
                        errors.append(response['a_sMessage'])
                    else:
                        for child in message:
                            if child.tag == 'Error':
                                errors.append(child.find('ErrorMessage').text)

                    raven_client.context.merge({
                        'extra': {
                            'response': response,
                        }
                    })

                    raven_client.captureMessage('Certificate creation failed.')
                    raven_client.context.clear()

        except Exception as exc:
            logger.exception(
                'Register certificate exception'
            )
            status = False
            errors = ['An unknown error occured.']
            if settings.DEBUG:
                print(exc)
            raven_client.captureException()

        print(status, errors)

        return (status, errors)

    def get(self, request):
        # Store the form data to the session
        request.session['gc_step2_data'] = self._forms_to_session_data(self.forms)
        return render(request, 'certificates/step2.jinja', {
            'forms': self.forms, 'groups': self.groups})

    def post(self, request):
        data = request.POST

        if 'reset' in data:
            if 'gc_step1_data' in request.session:
                del request.session['gc_step2_data']
            if 'gc_template_group' in request.session:
                del request.session['gc_template_group']
            return redirect(reverse('step2'))

        if 'group' in data:
            try:
                group = self.groups.get(pk=data['group'])
                request.session['gc_template_group'] = group.name
            except CertificateGroup.DoesNotExist():
                pass
            else:
                session_data = []

                for tpl in group.templates.all():
                    for i in range(0, tpl.count):
                        key = str(time.time())

                        data = {'type': tpl.type.pk}
                        if tpl.club:
                            data['club'] = tpl.club.pk
                        if tpl.club_secondary:
                            data['club_secondary'] = tpl.club_secondary.pk
                        if tpl.quantity:
                            data['quantity'] = str(tpl.quantity)
                        if tpl.note:
                            data['note'] = tpl.note
                        if tpl.message:
                            data['message'] = tpl.message
                        if tpl.power_cart is not None:
                            data['power_cart'] = tpl.power_cart
                        if tpl.expiry_date:
                            data['expiry_date'] = tpl.expiry_date.strftime('%d/%m/%Y')

                        session_data.append([key, data])

                request.session['gc_step2_data'] = session_data

            return redirect(reverse('step2'))

        # Pass POSTed data to the forms
        for key in self.forms:
            key, new_form = self._create_certificate_form(
                request.user, self.department, data, self.forms[key].index, key)
            self.forms.update({key: new_form})

        refocus_key = None

        # Handle Add, Duplicate and Delete requests
        CERTIFICATE_LIMIT_MESSAGE = _('You cannot create more than {limit} certificates').format(
            limit=settings.CERTIFICATES_BATCH_LIMIT)
        if 'add' in data:
            if len(self.forms.items()) < settings.CERTIFICATES_BATCH_LIMIT:
                refocus_key, new_form = self._create_certificate_form(
                    request.user, self.department, index=len(self.forms) + 1)
                self.forms.update({refocus_key: new_form})
            else:
                refocus_key = data['add']
                messages.warning(request, CERTIFICATE_LIMIT_MESSAGE)
        elif 'duplicate' in data:
            duplicate_key = data['duplicate']
            form_data = self._get_normalized_form_data(self.forms[duplicate_key], duplicate_key)

            try:
                count = int(data.get('duplicate-count-{}'.format(duplicate_key), 1))
            except ValueError:
                count = 1

            if len(self.forms.items()) + count <= settings.CERTIFICATES_BATCH_LIMIT:
                for i in range(count):
                    new_key, new_form = self._create_certificate_form(
                        request.user, self.department, index=len(self.forms) + 1)
                    new_form.initial = form_data

                    if refocus_key is None:
                        refocus_key = new_key

                    self.forms.update({new_key: new_form})
            else:
                refocus_key = duplicate_key
                messages.warning(request, CERTIFICATE_LIMIT_MESSAGE)
        elif 'delete' in data:
            refocus_key = data['delete']
            if len(self.forms.items()) > 1:
                if refocus_key in self.forms:
                    self.forms.pop(refocus_key)
            else:
                messages.warning(request, _('You must have at least one certificate.'))
        elif 'reload' in data:
            refocus_key = data['reload']

        # Store the form data to the session
        request.session['gc_step2_data'] = self._forms_to_session_data(self.forms)

        # Redirect to self if an action was requested
        if refocus_key:
            return redirect('{}#gc-{}'.format(reverse('step2'), refocus_key))

        # Ensure submitted forms are valid
        is_valid = self.recipient_form.is_valid()
        for key in self.forms:
            is_valid &= self.forms[key].is_valid()

        '''
        NEW: Prevent creation of certificates if there are failures at the IBS level, so that faulty certificates are not created and emailed out.
        '''
        # Ensure a connection to IBS is possible
        self.ibs_client = WebMemberClient()
        if not self.ibs_client.ping() and False:
            messages.warning(request, _('Unable to connect to IBS.'))
            return redirect(reverse('step2'))
        elif is_valid:
            batch = self._create_certificate_batch(request)

            # Check for a specific type of status
            status, errors = self._register_certificates(batch)

            request.session['gc_status'] = status
            request.session['gc_errors'] = errors
            request.session['gc_batch_id'] = batch.pk


            if status and not errors:
                logger.info(
                    'Step 2 Gift Certificates - status but no errors',
                    extra = {
                        'request': request,
                        'status': status,
                        'errors': errors
                    }
                )
                try:
                    send_certificate_batch_email(request.build_absolute_uri(), batch)
                except SMTPException:
                    raven_client.captureException()
                    request.session['gc_emailed_to'] = None
                else:
                    recipient_email = self.recipient_form.cleaned_data['recipient_email']
                    request.session['gc_emailed_to'] = recipient_email

                # Clear form data from session
                del request.session['gc_step1_data']
                del request.session['gc_step2_data']

                if 'gc_template_group' in request.session:
                    del request.session['gc_template_group']
            else:
                logger.exception('Error from IBS')
                batch.delete()

            return redirect(reverse('confirm'))

        return render(request, 'certificates/step2.jinja', {
            'forms': self.forms, 'groups': self.groups})

    def dispatch(self, request, *args, **kwargs):
        # Check for data from Step 1 and validate
        self.recipient_form = RecipientForm(request.user, request.session.get('gc_step1_data', {}))

        if not self.recipient_form.is_valid():
            messages.warning(request, _('You must complete this step before proceeding.'))
            return redirect(reverse('step1'))

        self.department = self.recipient_form.cleaned_data['department']
        self.groups = CertificateGroup.objects.filter(
            department=self.department)

        # Populate forms from the session
        self.forms = self._session_data_to_forms(request.user, self.department,
                                                 request.session.get('gc_step2_data'))

        return super().dispatch(request, *args, **kwargs)


@staff_required
@ip_whitelist_only
def confirm(request):
    if 'gc_emailed_to' not in request.session and 'gc_status' not in request.session:
        return redirect(reverse('step1'))

    batch_id = request.session.get('gc_batch_id')
    email = request.session.get('gc_emailed_to')
    status = request.session.get('gc_status')
    errors = request.session.get('gc_errors')

    error_messages = []
    for e in errors:
        if e not in error_messages:
            error_messages.append(e)
            messages.add_message(request, messages.ERROR, e)

    return render(request, 'certificates/confirm.jinja', {
        'batch_id': batch_id, 'email': email, 'status': status})


def download(request, code):
    try:
        pk, email = base64.urlsafe_b64decode(code.encode()).decode().split(':')
        batch = get_object_or_404(CertificateBatch, pk=pk, recipient_email=email)
    except ValueError:
        raise Http404()

    certificate_files = []

    for certificate in batch.certificates.select_related('type', 'club', 'batch', 'club_secondary'):
        if certificate.type.template == CertificateType.AG30_TEMPLATE:
            prefix = 'AG30'
        else:
            prefix = certificate.club.name.replace(' ', '_')

        # cache_key = 'certificate_pdf_{}'.format(certificate.pk)
        # data = cache.get(cache_key)

        # if not data:
        data = certificate.generate_pdf()
        # cache.set(cache_key, data, 300)

        fn = '{}_{}.pdf'.format(prefix, certificate.code[-6:])
        certificate_files.append({
            'filename': fn,
            'data': data
        })

    if len(certificate_files) == 1:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            quote(certificate_files[0]['filename']))
        response.write(certificate_files[0]['data'])
    else:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'a', zipfile.ZIP_DEFLATED, False) as zf:
            for content in certificate_files:
                zf.writestr(content['filename'], content['data'])

        response = HttpResponse(content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="certificates.zip"'
        response.write(buffer.getvalue())
        buffer.close()

    return response


def handler403(request, exception=None):
    return permission_denied(request, exception, template_name='certificates/403.jinja')


def handler404(request, exception=None):
    return page_not_found(request, exception, template_name='certificates/404.jinja')


def handler500(request):
    return render(request, 'certificates/500.jinja', status=500,
    context = {'request': request}
    )
