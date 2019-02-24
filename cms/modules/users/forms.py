from django import forms
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from clublink.clubs.models import Club
from clublink.cms import fields
from clublink.users.models import User, UserType, UserCategory, ClubCorp


class UserForm(forms.Form):
    username = fields.CharField(max_length=48)
    password = fields.CharField(min_length=6, required=False, widget=forms.PasswordInput())
    first_name = fields.CharField(required=False)
    last_name = fields.CharField(required=False)
    middle_name = fields.CharField(required=False)
    email = fields.EmailField()
    membership_number = fields.CharField(max_length=15, required=False)
    employee_number = fields.CharField(max_length=15, required=False)
    is_superuser = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=False,
        required=False)
    is_staff = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=False,
        required=False)
    preferred_language = fields.ChoiceField(
        choices=settings.LANGUAGES, initial=settings.LANGUAGE_CODE)
    status = fields.ChoiceField(choices=User.STATUSES)
    clubcorp = fields.ChoiceField(choices=[(None, '')], required=False)
    clubcorp_number = fields.CharField(max_length=5, required=False)
    type = fields.ChoiceField(choices=[(None, '')], required=False)
    category = fields.ChoiceField(choices=[(None, '')], required=False)
    home_club = fields.ChoiceField(choices=[(None, '')], required=False)
    option_club = fields.ChoiceField(choices=[(None, '')], required=False)
    home_club_alternate_1 = fields.ChoiceField(choices=[(None, '')], required=False)
    home_club_alternate_2 = fields.ChoiceField(choices=[(None, '')], required=False)

    def __init__(self, *args, **kwargs):
        self.user = None

        if kwargs.get('user'):
            self.user = kwargs.pop('user')
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'username': self.user.username,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'middle_name': self.user.middle_name,
                'email': self.user.email,
                'membership_number': self.user.membership_number,
                'employee_number': self.user.employee_number,
                'is_superuser': self.user.is_superuser,
                'is_staff': self.user.is_staff,
                'preferred_language': self.user.preferred_language,
                'status': self.user.status,
                'clubcorp': getattr(self.user.home_club, 'id', None),
                'clubcorp_number': self.user.clubcorp_number,
                'category': getattr(self.user.category, 'id', None),
                'type': getattr(self.user.type, 'id', None),
                'home_club': getattr(self.user.home_club, 'pk', None),
                'option_club': getattr(self.user.option_club, 'pk', None),
                'home_club_alternate_1': getattr(self.user.home_club_alternate_1, 'pk', None),
                'home_club_alternate_2': getattr(self.user.home_club_alternate_2, 'pk', None),
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        self.fields['clubcorp'].choices += [(c.id, c.name) for c in ClubCorp.objects.all()]
        self.fields['type'].choices += [(t.id, t.name) for t in UserType.objects.all()]
        self.fields['clubcorp'].choices += [(c.id, c.name) for c in UserCategory.objects.all()]

        self.fields['home_club'].choices += [(c.pk, c.name) for c in Club.objects.all()]
        self.fields['option_club'].choices += [(c.pk, c.name) for c in Club.objects.all()]
        self.fields['home_club_alternate_1'].choices += [
            (c.pk, c.name) for c in Club.objects.all()]
        self.fields['home_club_alternate_2'].choices += [
            (c.pk, c.name) for c in Club.objects.all()]

    def clean_username(self):
        data = self.cleaned_data['username']

        users = User.objects.all()

        if self.user:
            users = users.exclude(pk=self.user.pk)

        try:
            users.get(username=data)
        except User.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(_('Username is already in use.'))

        return data

    def clean_password(self):
        data = self.cleaned_data['password']
        return data if data else None

    def clean_membership_number(self):
        data = self.cleaned_data['membership_number']
        return data if data else None

    def clean_employee_number(self):
        data = self.cleaned_data['employee_number']
        return data if data else None

    def clean_is_staff(self):
        is_superuser = self.cleaned_data['is_superuser']
        is_staff = self.cleaned_data['is_staff']
        return is_staff or is_superuser

    def validate_fk(self, data, klass):
        if data:
            try:
                data = klass.objects.get(pk=data)
            except klass.DoesNotExist:
                raise forms.ValidationError(_('Invalid entry.'))
        else:
            data = None
        return data

    def clean_clubcorp(self):
        data = self.cleaned_data['clubcorp']
        return self.validate_fk(data, ClubCorp)

    def clean_category(self):
        data = self.cleaned_data['category']
        return self.validate_fk(data, UserCategory)

    def clean_type(self):
        data = self.cleaned_data['type']
        return self.validate_fk(data, UserType)

    def clean_home_club(self):
        data = self.cleaned_data['home_club']
        return self.validate_fk(data, Club)

    def clean_option_club(self):
        data = self.cleaned_data['option_club']
        return self.validate_fk(data, Club)

    def clean_home_club_alternate_1(self):
        data = self.cleaned_data['home_club_alternate_1']
        return self.validate_fk(data, Club)

    def clean_home_club_alternate_2(self):
        data = self.cleaned_data['home_club_alternate_2']
        return self.validate_fk(data, Club)


class AccountsFilterForm(forms.Form):
    STAFF_ONLY = 'STAFF'
    SUPERUSERS_ONLY = 'SUPERUSERS'
    SHOW_ONLY_CHOICES = (
        ('', _('Show Only')),
        (STAFF_ONLY, _('Staff users')),
        (SUPERUSERS_ONLY, _('Superusers')),
    )

    show_only = fields.ChoiceField(choices=SHOW_ONLY_CHOICES, required=False)


class UserSearchForm(forms.Form):
    query = fields.CharField(label=_('Search for User.... (or type the club name - ex. woodlands)'), min_length=3)

    def clean(self):
        super().clean()

        query = self.cleaned_data.get('query')

        if query:
            users = User.objects.filter(
                Q(username__icontains=query) | Q(membership_number=query) |
                Q(first_name__icontains=query) | Q(last_name__icontains=query) | 
                Q(home_club__name__icontains=query)
                )

            users = users.exclude(membership_number=None)

            self.cleaned_data['results'] = users

        return self.cleaned_data


class MyAccountForm(forms.Form):
    first_name = fields.CharField()
    middle_name = fields.CharField(required=False)
    last_name = fields.CharField()
    email = fields.EmailField()
    password = fields.CharField(required=False, widget=forms.PasswordInput())
    preferred_language = fields.ChoiceField(
        choices=settings.LANGUAGES, initial=settings.LANGUAGE_CODE)

    def __init__(self, *args, **kwargs):
        self.user = None

        if 'user' in kwargs:
            self.user = kwargs.pop('user')
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'middle_name': self.user.middle_name,
                'email': self.user.email,
                'preferred_language': self.user.preferred_language,
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)


class PermissionsForm(forms.Form):
    can_access_cms = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=False,
        required=False)
    can_impersonate_user = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=False,
        required=False)

    def __init__(self, *args, **kwargs):
        self.user = None

        if 'user' in kwargs:
            self.user = kwargs.pop('user')
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'can_access_cms': self.user.permissions.can_access_cms,
                'can_impersonate_user': self.user.permissions.can_impersonate_user,
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)
