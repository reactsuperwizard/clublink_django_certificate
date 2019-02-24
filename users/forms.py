import re

from urllib.request import quote

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from clublink.users.models import User


class NullPasswordLogin(Exception):
    pass


class LoginForm(forms.Form):
    username = forms.CharField(label=_('Username'))
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput())

    user = None
    INVALID_CREDENTIALS_MESSAGE = _('Invalid username or password.')

    class NullPasswordLogin(NullPasswordLogin):
        pass

    def clean(self):
        super().clean()

        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username:
            try:
                matched_user = User.objects.get(membership_number=username)
                username = matched_user.username
            except User.DoesNotExist:
                try:
                    matched_user = User.objects.get(username=username)
                except User.DoesNotExist:
                    raise forms.ValidationError(self.INVALID_CREDENTIALS_MESSAGE)

            if not matched_user.password:
                self.user = matched_user
                raise self.NullPasswordLogin()

            self.user = authenticate(username=username, password=password)

            if self.user is None:
                raise forms.ValidationError(self.INVALID_CREDENTIALS_MESSAGE)
            elif not self.user.is_active:
                raise forms.ValidationError(_('User account has been disabled.'))

        return self.cleaned_data

    def get_user(self):
        return self.user


class MemberIDLoginForm(LoginForm):
    username = forms.CharField(label=_('Membership Number'))

    INVALID_CREDENTIALS_MESSAGE = _('Invalid membership number or password.')


class MemberIDForgotForm(forms.Form):
    username = forms.CharField(label=_('Membership Number'))

    user = None

    def clean_username(self):
        username = self.cleaned_data.get('username')

        try:
            self.user = User.objects.get(membership_number=username)
        except User.DoesNotExist:
            try:
                self.user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise forms.ValidationError(_(MemberIDLoginForm.INVALID_CREDENTIALS_MESSAGE))

        return self.user.username

    def get_user(self):
        return self.user

    def send_reset_email(self, request):
        self.user.refresh_from_db()

        url = '{}?token={}'.format(reverse('login.reset'), quote(self.user.generate_reset_token()))

        context = {
            'user': self.user,
            'reset_url': request.build_absolute_uri(url)
        }

        locale = self.user.preferred_language.lower()

        message = render_to_string('users/email/reset_{}.txt'.format(locale), context=context)
        message_html = render_to_string('users/email/reset_{}.jinja'.format(locale),
                                        context=context)

        if locale == 'fr':
            subject = 'Réinitialisez votre mot de passe'
        else:
            subject = 'Reset your password'

        from_email = 'ClubLink <{}>'.format(getattr(settings, 'MEMBER_SERVICES_EMAIL_ADDRESS'))

        if getattr(settings, 'PASSWORD_RESET_DEBUG'):
            to = getattr(settings, 'PASSWORD_RESET_DEBUG_EMAIL_ADDRESSES')
        else:
            to = [self.user.email]

        email = EmailMultiAlternatives(
            subject=subject, body=message, to=to, from_email=from_email)

        email.attach_alternative(message_html, 'text/html')

        email.send()

class UsaMemberChallengeForm(forms.Form):
    last_name = forms.CharField(label=_('Last Name'))
    postal_code = forms.CharField(label=_('zip Code'))

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    @staticmethod
    def normalize_zip_code(code):
        return code.lower().replace(' ', '')

    def clean(self):
        super().clean()

        zip_code = self.normalize_zip_code(self.cleaned_data.get('zip_code', ''))
        last_name = self.cleaned_data.get('last_name')

        if zip_code and last_name:
            zip_codes = []

            for address in self.user.addresses.all():
                if address.zip_code:
                    zip_codes.append(self.normalize_zip_code(address.zip_code))

            if zip_code not in zip_codes or last_name.lower() != self.user.last_name.lower():
                raise forms.ValidationError(_('Details provided do not match our records.'))

        return self.cleaned_data

class MemberChallengeForm(forms.Form):
    last_name = forms.CharField(label=_('Last Name'))
    postal_code = forms.CharField(label=_('Postal Code'))

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    @staticmethod
    def normalize_postal_code(code):
        return code.lower().replace(' ', '')

    def clean(self):
        super().clean()

        postal_code = self.normalize_postal_code(self.cleaned_data.get('postal_code', ''))
        last_name = self.cleaned_data.get('last_name')

        if postal_code and last_name:
            postal_codes = []

            for address in self.user.addresses.all():
                if address.postal_code:
                    postal_codes.append(self.normalize_postal_code(address.postal_code))

            if postal_code not in postal_codes or last_name.lower() != self.user.last_name.lower():
                raise forms.ValidationError(_('Details provided do not match our records.'))

        return self.cleaned_data


class PasswordResetForm(forms.Form):
    email = forms.EmailField(label=_('Email Address'))
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput())
    password_confirm = forms.CharField(label=_('Confirm Password'), widget=forms.PasswordInput())

    def __init__(self, user, *args, **kwargs):
        self.user = user

        initial = {
            'email': self.user.email
        }
        initial.update(kwargs.get('initial', {}))
        kwargs['initial'] = initial

        super().__init__(*args, **kwargs)

        if self.user.password:
            self.fields.pop('email')

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if len(password) < 8:
            raise forms.ValidationError(_('Password must be at least 8 characters.'))

        mixed_case = re.search(r'[A-Z]', password) and re.search(r'[a-z]', password)
        number = re.search(r'[0-9]', password)

        if not (mixed_case and number):
            raise forms.ValidationError(_('Password must have at least one uppercase letter, one '
                                          'lowercase letter and one number.'))

        return password

    def clean(self):
        super().clean()

        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')

        if password and password != password_confirm:
            raise forms.ValidationError(_('Passwords do not match.'))

        return self.cleaned_data

    def send_confirm_email(self, request):
        self.user.refresh_from_db()

        context = {
            'user': self.user,
        }

        locale = self.user.preferred_language.lower()

        message = render_to_string('users/email/reset_confirm_{}.txt'.format(locale),
                                   context=context)
        message_html = render_to_string('users/email/reset_confirm_{}.jinja'.format(locale),
                                        context=context)

        if locale == 'fr':
            subject = 'Avis de réinitialisation de mot de passe'
        else:
            subject = 'Password reset notification'

        from_email = 'ClubLink <{}>'.format(getattr(settings, 'MEMBER_SERVICES_EMAIL_ADDRESS'))

        if getattr(settings, 'PASSWORD_RESET_DEBUG'):
            to = getattr(settings, 'PASSWORD_RESET_DEBUG_EMAIL_ADDRESSES')
        else:
            to = [self.user.email]

        email = EmailMultiAlternatives(
            subject=subject, body=message, to=to, from_email=from_email)

        email.attach_alternative(message_html, 'text/html')

        email.send()
