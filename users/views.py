from email.errors import HeaderParseError
from smtplib import SMTPRecipientsRefused
from urllib.request import quote

from django import views
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    login as auth_login,
    REDIRECT_FIELD_NAME
)
from django.shortcuts import redirect, render, resolve_url, reverse
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _

from clublink.base.templatetags import club_url
from clublink.users.forms import (
    MemberChallengeForm,
    UsaMemberChallengeForm,
    MemberIDForgotForm,
    MemberIDLoginForm,
    PasswordResetForm,
)
from clublink.users.models import User


class GenericPageView(views.View):
    template = None
    extra_context = {}
    redirect_to = None

    def process_request(self, request, *args, **kwargs):
        self.redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')

        # Ensure the user-originating redirection URL is safe.
        if not is_safe_url(url=self.redirect_to, host=request.get_host()):
            self.redirect_to = resolve_url(reverse('home'))

        if request.user.is_authenticated:
            if self.redirect_to == request.path:
                return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))
            return redirect(self.redirect_to)

    def get_extra_context(self, request, *args, **kwargs):
        self.extra_context.update({
            'base_template': kwargs.get('base_template', '')
        })
        return self.extra_context

    def get(self, request, *args, **kwargs):
        context = {}
        context.update(self.get_extra_context(request, *args, **kwargs))
        return render(request, self.template, context)

    def dispatch(self, request, *args, **kwargs):
        response = self.process_request(request, *args, **kwargs)
        if response:
            return response

        return super().dispatch(request, *args, **kwargs)


class LoginView(GenericPageView):
    template = 'users/login/login.jinja'
    form = None

    def get_extra_context(self, request, *args, **kwargs):
        if not self.form:
            self.form = MemberIDLoginForm()

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
            'redirect_to': self.form,
            'redirect_field_name': REDIRECT_FIELD_NAME,
        })
        return extra_context

    def post(self, request, *args, **kwargs):
        self.form = MemberIDLoginForm(request.POST)

        try:
            if self.form.is_valid():
                user = self.form.get_user()
                auth_login(request, user)

                if not user.is_staff:
                    if user.option_club:
                        self.redirect_to = club_url(user.option_club, 'home')
                    elif user.home_club:
                        self.redirect_to = club_url(user.home_club, 'home')

                return redirect(self.redirect_to)
        except self.form.NullPasswordLogin:
            url = '{}?k={}'.format(reverse('login.challenge'),
                                   quote(self.form.user.encrypted_membership_number))
            return redirect(url)

        return self.get(request, *args, **kwargs)


class ForgotPasswordView(GenericPageView):
    template = 'users/login/forgot.jinja'
    form = None

    def get_extra_context(self, request, *args, **kwargs):
        if not self.form:
            self.form = MemberIDForgotForm()

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
        })
        return extra_context

    def post(self, request, *args, **kwargs):
        self.form = MemberIDForgotForm(request.POST)

        if self.form.is_valid():
            if self.form.user.email:
                try:
                    self.form.send_reset_email(request)
                except (HeaderParseError, SMTPRecipientsRefused):
                    pass
                else:
                    return redirect(reverse('login.forgot-success'))

            return redirect(reverse('login.forgot-failure'))

        return self.get(request, *args, **kwargs)


class ForgotPasswordSuccessView(GenericPageView):
    template = 'users/login/forgot-success.jinja'


class ForgotPasswordFailureView(GenericPageView):
    template = 'users/login/forgot-failure.jinja'


class LoginChallengeView(GenericPageView):
    template = 'users/login/challenge.jinja'
    user = None
    form = None
    emailed = False

    def process_request(self, request, *args, **kwargs):
        super().process_request(request, *args, **kwargs)

        try:
            membership_number = User.decrypt_membership_number(request.GET.get('k'))
        except:
            return redirect(reverse('login'))

        try:
            self.user = User.objects.get(membership_number=membership_number)
        except User.DoesNotExist:
            return redirect(reverse('login'))

        self.emailed = kwargs.get('emailed', False)

        if self.user.email and not self.emailed:
            forgot_form = MemberIDForgotForm({'username': self.user.username})
            if forgot_form.is_valid():
                try:
                    forgot_form.send_reset_email(request)
                except (HeaderParseError, SMTPRecipientsRefused):
                    # User has an invalid email so proceed with challenge
                    pass
                else:
                    return redirect(reverse('login.challenge-success'))

        if request.site.id == 1:
            self.form = MemberChallengeForm(self.user)
        else:
            self.form = UsaMemberChallengeForm(self.user)

    def post(self, request, *args, **kwargs):

        if request.site.id == 1:
            self.form = MemberChallengeForm(self.user, request.POST)
        else:
            self.form = UsaMemberChallengeForm(self.user, request.POST)

        if self.form.is_valid():
            url = '{}?token={}'.format(reverse('login.reset'),
                                       quote(self.user.generate_reset_token()))
            return redirect(url)

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
            'emailed': self.emailed,
        })
        return extra_context


class LoginChallengeSuccessView(GenericPageView):
    template = 'users/login/challenge-success.jinja'


class ResetPasswordView(GenericPageView):
    template = 'users/login/reset.jinja'
    user = None
    form = None

    def _validate_token(self, request, token, attempt_fix=True):
        try:
            self.user = User.parse_reset_token(token)
        except User.ExpiredToken:
            messages.add_message(
                request, messages.ERROR,
                _('Your token has expired. Please use "Forgot your password" to get a new token.'))
            return False
        except User.InvalidToken:
            if attempt_fix:
                # Attempt to fix the token from bad registration emails
                token = token[2:-1].replace(' ', '+')
                return self._validate_token(request, token, attempt_fix=False)
            messages.add_message(
                request, messages.ERROR, _('Your password reset token is invalid.'))
            return False
        else:
            return True

    def process_request(self, request, *args, **kwargs):
        super().process_request(request, *args, **kwargs)

        is_valid = self._validate_token(request, request.GET.get('token'))
        if not is_valid:
            return redirect(reverse('login'))

        self.form = PasswordResetForm(self.user)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
            'registering': not self.user.password,
        })
        return extra_context

    def post(self, request, *args, **kwargs):
        self.form = PasswordResetForm(self.user, request.POST)

        if self.form.is_valid():
            if 'email' in self.form.cleaned_data:
                self.user.email = self.form.cleaned_data.get('email')
            self.user.set_password(self.form.cleaned_data.get('password'))
            self.user.save()

            self.form.send_confirm_email(request)
            messages.add_message(request, messages.SUCCESS, _('Your password has been reset.'))
            return redirect(reverse('login'))

        return self.get(request, *args, **kwargs)
