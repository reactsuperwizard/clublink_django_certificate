import datetime

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, exceptions
from clublink.certificates.models import Certificate, CertificateType, EmailSignature
from clublink.clubs.models import Club, Department
from clublink.users.models import User
from clublink.certificates.constants import DOLLAR_VALUE_CATEGORIES



class CertificateSerializer(serializers.Serializer):
    """
    This is the Gift Certificates REST API layer
    """

    language = serializers.ChoiceField(choices=settings.LANGUAGES, required=True)
    account_number = serializers.RegexField(regex='^[a-zA-Z0-9]{1,10}$', allow_blank=False, required=False)
    recipient_name = serializers.CharField(max_length=60, required=True)
    recipient_email = serializers.EmailField(required=True)
    department_id = serializers.UUIDField(format='hex_verbose', required=True)
    email_signature = serializers.IntegerField(required=True)
    cert_type = serializers.IntegerField(required=True)
    primary_course = serializers.IntegerField(required=True)

    secondary_course = serializers.IntegerField(required=False)
    expiry_date = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d'], required=False)
    quantity = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    power_cart = serializers.ChoiceField(choices=Certificate.POWER_CART_CHOICES, required=False)
    note = serializers.CharField(max_length=255, required=False)
    message = serializers.CharField(max_length=250, required=False)

    def validate(self, data):
        self.certificate_batch_data = {}
        self.certificate_data = {}

        if data.get('language') is not None:
            self.certificate_batch_data['language'] = data.get('language')

        if data.get('recipient_name') is not None:
            self.certificate_batch_data['recipient_name'] = data.get('recipient_name')

        if data.get('recipient_email') is not None:
            self.certificate_batch_data['recipient_email'] = data.get('recipient_email')

        if data.get('note') is not None:
            self.certificate_data['note'] = data.get('note')

        if data.get('message') is not None:
            self.certificate_data['message'] = data.get('message')

        # Account Number
        if data.get('account_number') is not None:
            try:
                User.objects.get(membership_number=data.get('account_number'))
                self.certificate_batch_data['account_number'] = data.get('account_number')
            except User.DoesNotExist:
                if data.get('account_number') != settings.DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER:
                    raise serializers.ValidationError({"account_number": _('Account number does not exist')})
            else:
                self.certificate_batch_data['account_number'] = settings.DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER
        else:
            self.certificate_batch_data['account_number'] = settings.DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER

        # Department
        try:
            self.certificate_batch_data['department'] = Department.objects.get(pk=data.get('department_id'))
        except Department.DoesNotExist:
            raise serializers.ValidationError({"department_id":_('Invalid department.')})

        # TODO: This will come with the authentication layer
        # if not Department.objects.filter(admins__in=self.context['employee']):
        #     raise serializers.ValidationError({"department_id":_('Employee does not have access to this department')})

        # Email Signature ( 1 is the default email_signature that gives access to all GC)
        if data.get('email_signature') is not None and data.get('email_signature') != 1:
            try:
                self.certificate_batch_data['email_signature'] = EmailSignature.objects.\
                    get(id=data.get('email_signature'), department=self.certificate_batch_data['department'])
            except EmailSignature.DoesNotExist:
                raise serializers.ValidationError({"email_signature":_('Email signature invalid access')})

        # Certificate Type
        try:
            self.certificate_data['type'] = CertificateType.objects.get(pk=data.get('cert_type'))
        except CertificateType.DoesNotExist:
            raise serializers.ValidationError({"cert_type":_('Certificate type does not exist')})

        # Primary Course
        try:
            self.certificate_data['club'] = Club.objects.get(pk=data.get('primary_course'))
        except Club.DoesNotExist:
            raise serializers.ValidationError({"primary_course":_('Invalid primary course')})

        # Secondary Course
        if data.get('secondary_course') is not None:
            try:
                self.certificate_data['club_secondary'] = Club.objects.get(pk=data.get('secondary_course'))
            except Club.DoesNotExist:
                raise serializers.ValidationError({"secondary_course":_('Invalid secondary course')})

        # Quantity
        if data.get('quantity') is None:
            if self.certificate_data['type'].quantity:
                if self.certificate_data['type'].category in DOLLAR_VALUE_CATEGORIES:
                    self.certificate_data['quantity'] = self.certificate_data['type'].quantity
                else:
                    self.certificate_data['quantity'] = int(self.certificate_data['type'].quantity)
            else:
                raise serializers.ValidationError({"quantity":_('quantity can not be empty.')})
        else:
            if self.certificate_data['type'].category in DOLLAR_VALUE_CATEGORIES:
                self.certificate_data['quantity'] = data.get('quantity')
            else:
                self.certificate_data['quantity'] = int(data.get('quantity'))

        # Expiry Date
        if data.get('expiry_date') is None:
            if self.certificate_data['type'].expiry_date:
                self.certificate_data['expiry_date'] = self.certificate_data['type'].expiry_date
            else:
                raise serializers.ValidationError({"expiry_date":_('expiry_date can not be empty.')})
        else:
            if data.get('expiry_date') < datetime.date.today():
                raise serializers.ValidationError({"expiry_date": _('expiry_date must be after today.')})
            self.certificate_data['expiry_date'] = data.get('expiry_date')

        # Power Cart
        if data.get('power_cart') is None:
            if self.certificate_data['type'].power_cart:
                self.certificate_data['power_cart'] = self.certificate_data['type'].power_cart
            else:
                raise serializers.ValidationError({"power_cart":_('power_cart can not be empty.')})
        else:
            self.certificate_data['power_cart'] = data.get('power_cart')

        return data
