from django import forms
from django.utils.translation import ugettext_lazy as _

from clublink.cms import fields
from clublink.users.forms import LoginForm as UserLoginForm


class LoginForm(UserLoginForm):
    username = fields.CharField(label=_('Username'))
    password = fields.CharField(label=_('Password'), widget=forms.PasswordInput())


class ImageUploadForm(forms.Form):
    image = forms.ImageField()
