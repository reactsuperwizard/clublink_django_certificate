from django import forms
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from clublink.certificates.models import Certificate, CertificateType, EmailSignature
from clublink.clubs.models import Club, Department
from clublink.users.models import User

from .constants import DOLLAR_VALUE_CATEGORIES

class RecipientForm(forms.Form):
    language = forms.ChoiceField (label=_ ('Language'), choices=settings.LANGUAGES)
    account_number = forms.CharField(label=_('Account Number (Optional)'), required=False)
    account_name = forms.CharField(label=_('Account Name (Optional)'), required=False)
    recipient_name = forms.CharField(label=_('Recipient Name'))
    recipient_email = forms.EmailField(label=_('Recipient Email'))

    def __init__(self, user, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user
        self.request = request

        data = self.data or self.initial

        self.departments = Department.objects.for_user(user).filter(hidden=False)
        department_choices = [(d.pk, d.name,) for d in self.departments]
        self.fields['department'] = forms.ChoiceField(
            label=_('Department'), choices=department_choices)

        department = self.departments.first()
        if 'department' in data:
            try:
                department = self.departments.get(pk=data['department'])
            except Department.DoesNotExist:
                pass

        self.signatures = EmailSignature.objects.filter(
            Q(department=department) | Q(department=None))

        signature_choices = [(s.pk, s.name,) for s in self.signatures if s.department is not None]
        signature_choices += [(s.pk, s.name,) for s in self.signatures if s.department is None]
        self.fields['email_signature'] = forms.ChoiceField(
            label=_('Email Signature'), choices=signature_choices)

    def clean_account_number(self):
        data = self.cleaned_data['account_number']

        if data:
            try:
                User.objects.get(membership_number=data)
            except User.DoesNotExist:
                if data != settings.DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER:
                    raise forms.ValidationError(_('Invalid account number.'))
        else:
            data = settings.DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER
            if self.request:
                messages.warning(
                    self.request,
                    _('Default account number ({}) was selected.'.format(data)))

        return data

    def clean_department(self):
        data = self.cleaned_data['department']

        if data:
            try:
                data = self.departments.get(pk=data)
            except Department.DoesNotExist:
                raise forms.ValidationError(_('Invalid department.'))
        else:
            raise forms.ValidationError(_('This field is required.'))

        return data

    def clean_email_signature(self):
        data = self.cleaned_data['email_signature']

        if data:
            try:
                data = self.signatures.get(pk=data)
            except Department.DoesNotExist:
                raise forms.ValidationError(_('Invalid email signature.'))
        else:
            raise forms.ValidationError(_('This field is required.'))

        return data


class CertificateForm(forms.Form):
    expiry_date = forms.DateField(input_formats=['%d/%m/%Y'],
                                  widget=forms.DateInput(attrs={'data-pikaday': True}))
    quantity = forms.TypedChoiceField(label=_('Number of Players'), coerce=int,
                                      choices=[('', '',)] + [(i, i,) for i in range(1, 5)])
    power_cart = forms.TypedChoiceField(label=_('Power Cart'), coerce=int,
                                        choices=Certificate.POWER_CART_CHOICES)
    message = forms.CharField(label=_('Custom Message'), max_length=250,
                              widget=forms.Textarea(), required=False)
    note = forms.CharField(label=_('Note'), max_length=255, required=False)

    def __init__(self, user, department, *args, index=1, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user
        self.department = department

        cert_type = None

        if 'initial' in kwargs or self.data:
            data = self.data if self.data else kwargs['initial']
            data_key = '{}-type'.format(self.prefix) if self.data else 'type'
            if data_key in data and data[data_key]:
                try:
                    cert_type = CertificateType.objects.get(pk=data[data_key])
                except CertificateType.DoesNotExist:
                    pass

        initial_quantity = kwargs.get('initial', {}).get('quantity', None)
        if initial_quantity and cert_type and cert_type.category not in DOLLAR_VALUE_CATEGORIES:
            kwargs['initial']['quantity'] = int(initial_quantity)

        if cert_type and cert_type.category in DOLLAR_VALUE_CATEGORIES:
            self.fields['quantity'] = forms.DecimalField(
                label=_('Dollar Value'), max_value=500, min_value=0, widget=forms.TextInput())

            self.fields['expiry_date'].required = False

        if 'initial' in kwargs and cert_type:
            if cert_type.quantity:
                if cert_type.category in DOLLAR_VALUE_CATEGORIES:
                    self.fields['quantity'].initial = cert_type.quantity
                else:
                    self.fields['quantity'].initial = int(cert_type.quantity)

            self.fields['power_cart'].initial = cert_type.power_cart or False

            if cert_type.expiry_date:
                self.fields['expiry_date'].initial = cert_type.expiry_date.strftime(
                    '%d/%m/%Y')
            elif cert_type.dynamic_expiry == CertificateType.ONE_YEAR_EXPIRY:
                next_year = timezone.now() + timezone.timedelta(days=366)
                self.fields['expiry_date'].initial = next_year.strftime('%d/%m/%Y')

        self.index = index
        self.title = _('Gift Certificate #{index}').format(index=index)

        types = CertificateType.objects.filter(departments__in=[department])
        self.fields['type'] = forms.ChoiceField(
            label=_('Gift Certificate Type'),
            choices=[('', '',)] + [(t.pk, t.name,) for t in types])

        clubs = department.clubs.all()

        self.fields['club'] = forms.ChoiceField(
            label=_('Course'), choices=[('', '',)] + [(c.pk, c.name,) for c in clubs])

        if cert_type:
            self.fields['club'].initial = cert_type.club.pk if cert_type.club else None

            # NOTE: Logic is being left in the form, whereas this should be placed in the views. Nested if for clarity, but should be refactored  or rewritten altogether.
            if cert_type.category != CertificateType.DEFAULT_CATEGORY:
                self.fields['message'] = forms.CharField(
                    label=_('Custom Message'),
                    max_length=1000,
                    widget=forms.Textarea(),
                    required=False)

        if clubs.count() == 1:
            self.fields['club'].initial = clubs.first().pk

        self.fields['club_secondary'] = forms.ChoiceField(
            label=_('Secondary Course'), choices=[('', '',)] + [(c.pk, c.name,) for c in clubs],
            required=False)

    def clean_type(self):
        data = self.cleaned_data['type']

        if data:
            try:
                data = CertificateType.objects.get(pk=data)
            except CertificateType.DoesNotExist:
                raise forms.ValidationError(_('Invalid gift certificate type.'))
        else:
            raise forms.ValidationError(_('This field is required.'))

        return data

    def clean_club(self):
        data = self.cleaned_data['club']

        if data:
            try:
                data = Club.objects.get(pk=data)
            except Club.DoesNotExist:
                raise forms.ValidationError(_('Invalid course.'))
        else:
            raise forms.ValidationError(_('This field is required.'))

        return data

    def clean_club_secondary(self):
        data = self.cleaned_data['club_secondary']

        if data:
            try:
                data = Club.objects.get(pk=data)
            except Club.DoesNotExist:
                raise forms.ValidationError(_('Invalid course.'))
        else:
            return None

        return data
