import re

from django import forms
from django.conf import settings

from django.utils.translation import ugettext_lazy as _

from clublink.users.models import Address, User


class UserForm(forms.Form):
    first_name = forms.CharField(disabled=True)
    last_name = forms.CharField(disabled=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=False)
    password_confirm = forms.CharField(label=_('Confirm Password'), widget=forms.PasswordInput(),
                                       required=False)
    preferred_language = forms.ChoiceField(choices=settings.LANGUAGES)
    email = forms.EmailField(max_length=60)

    def __init__(self, user, *args, **kwargs):
        kw_initial = kwargs.get('initial', {})

        kwargs['initial'] = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'preferred_language': user.preferred_language,
            'email': user.email,
        }

        kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if password:
            if len(password) < 8:
                raise forms.ValidationError(_('Password must be at least 8 characters.'))

            mixed_case = re.search(r'[A-Z]', password) and re.search(r'[a-z]', password)
            number = re.search(r'[0-9]', password)

            if not (mixed_case and number):
                raise forms.ValidationError(
                    _('Password must have at least one uppercase letter, one '
                      'lowercase letter and one number.'))

        return password

    def clean(self):
        data = self.cleaned_data
        password = data.get('password')
        password_confirm = data.get('password_confirm')

        if password and password != password_confirm:
            raise forms.ValidationError(_('Passwords do not match.'))

        return data


class ProfileForm(forms.Form):
    title = forms.CharField(max_length=10, required=False, disabled=True)
    dob = forms.DateField(required=False, disabled=True, label=_('Date of Birth'),
                          input_formats=['%d/%m/%Y'])
    employer = forms.CharField(max_length=80, required=False)
    position = forms.CharField(max_length=30, required=False)
    show_in_roster = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    # show_phone = forms.ChoiceField(
    #     required=False,
    #     choices=(

    #     )
    #     )
    # show_email = forms.ChoiceField(
    #     required=False,
    #     choices=(

    #     )
    #     )


    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kw_initial = kwargs.get('initial', {})

        self.user = user
        profile = user.profile

        addresses = user.addresses.all()

        phone_addresses = addresses.filter(phone__isnull=False)

        cell_addresses = addresses.filter(cell_phone__isnull=False)

        email_addresses = addresses.filter(email__isnull=False)

        ### SHOW PHONE ###
        self.fields['show_phone'] = forms.ChoiceField(
            choices=[
                (None, 'Do not show my phone')
            ],
            required=False,
            label=_('Phone number to show in roster')
            )

        if phone_addresses:
            self.fields['show_phone'].choices.extend(
                [(a.id, '{} ({})'.format(
                    a.phone, a.get__type_display()
                )) for a in phone_addresses]
            )
        else:
            self.fields['show_phone'].disabled = True
        ###

        ### SHOW CELL ###
        self.fields['show_cell'] = forms.ChoiceField(
            choices=[(None, 'Do not show my cell')],
            required=False,
            label=_('Cell number to show in roster'))

        if cell_addresses:
            self.fields['show_cell'].choices.extend(
                [(a.id, '{} ({})'.format(
                    a.cell_phone, a.get__type_display()
                ))
                 for a in cell_addresses])
        else:
            self.fields['show_cell'].disabled = True
        ###

        ### SHOW EMAIL ###
        self.fields['show_email'] = forms.ChoiceField(
            choices=[(None, 'Do not show my email')],
            required=False,
            label=_('Email to show in roster'))

        if email_addresses:
            self.fields['show_email'].choices.extend(
                [(a.id, '{} ({})'.format(
                    a.email, a.get__type_display()
                )) for a in email_addresses]
            )
        else:
            self.fields['show_email'].disabled = True
        ###

        kwargs['initial'] = {
            'show_email':
            profile.show_email.id if profile.show_email else None,
            'show_phone':
            profile.show_phone.id if profile.show_phone else None,
            'show_cell':
            profile.show_cell.id if profile.show_cell else None,
            'title':
            profile.title,
            'dob':
            profile.dob.strftime('%-d/%-m/%Y') if profile.dob else '',
            'employer':
            profile.employer,
            'position':
            profile.position,
            'show_in_roster':
            profile.show_in_roster if profile.show_in_roster else False,
        }

        kwargs['initial'].update(kw_initial)
        self.initial = kwargs['initial']


class AddressForm(forms.Form):
    COUNTRIES = (
        ('', ''),
        ('CAN', 'Canada'),
        ('USA', 'USA'),
    )

    REQUIRED_FIELDS = (
        'address1',
        'city',
        'country',
        'phone',
        'state',
        'postal_code',
    )

    address1 = forms.CharField(max_length=30, required=False, label=_('Address 1'))
    address2 = forms.CharField(max_length=30, required=False, label=_('Address 2'))
    city = forms.CharField(max_length=30, required=False)
    country = forms.ChoiceField(choices=COUNTRIES, required=False)
    cell_phone = forms.CharField(max_length=30, required=False)
    phone = forms.CharField(max_length=30, required=False)
    state = forms.CharField(max_length=3, required=False, label=_('Province/State'))
    postal_code = forms.CharField(max_length=10, required=False)

    def __init__(self, user, address_type, *args, **kwargs):
        kw_initial = kwargs.get('initial', {})

        try:
            address = user.addresses.get(type=address_type)
        except Address.DoesNotExist:
            pass
        else:
            kwargs['initial'] = {
                'address1': address.address1,
                'address2': address.address2,
                'city': address.city,
                'country': address.country,
                'cell_phone': address.cell_phone,
                'phone': address.phone,
                'state': address.state,
                'postal_code': address.postal_code
            }

            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        self.has_data = False
        for key in self.data:
            if key.startswith('{}-'.format(self.prefix)):
                data = self.data.get(key)
                self.has_data = self.has_data or bool(data)

        if self.has_data:
            for f in self.REQUIRED_FIELDS:
                self.fields[f].required = True


class SubscriptionsForm(forms.Form):
    email_dues_notice = forms.BooleanField(
        required=False, label=_('Receive annual dues notice via email'),
        widget=forms.CheckboxInput())
    email_statement = forms.BooleanField(
        required=False, label=_('Receive statement via email'), widget=forms.CheckboxInput())
    subscribe_score = forms.BooleanField(
        required=False, label=_('Score Golf Magazine'), widget=forms.CheckboxInput())
    subscribe_clublink_info = forms.BooleanField(
        required=False, label=_('ClubLink Life Weekly'), widget=forms.CheckboxInput())
    subscribe_club_info = forms.BooleanField(
        required=False, label=_('Club News'), widget=forms.CheckboxInput())

    def __init__(self, user, *args, **kwargs):
        kw_initial = kwargs.get('initial', {})

        profile = user.profile

        kwargs['initial'] = {
            'email_dues_notice': profile.email_dues_notice,
            'email_statement': profile.email_statement,
            'subscribe_score': profile.subscribe_score,
            'subscribe_clublink_info': profile.subscribe_clublink_info,
            'subscribe_club_info': profile.subscribe_club_info
        }

        kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)


class PreferenceForm(forms.Form):
    mailing_address = forms.ChoiceField(
        required=True, label=_('Mailing Address'), choices=())
    billing_address = forms.ChoiceField(
        required=True, label=_('Billing Address'), choices=())

    def __init__(self, user, *args, **kwargs):
        self.user = user

        kw_initial = kwargs.get('initial', {})

        mailing_address = user.profile.mailing_address
        billing_address = user.profile.billing_address

        kwargs['initial'] = {
            'mailing_address': mailing_address.type if mailing_address else '',
            'billing_address': billing_address.type if billing_address else '',
        }

        kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        addresses = [('', '')] + [(a.type, a.type) for a in user.addresses.all()]
        self.fields['mailing_address'].choices = addresses
        self.fields['billing_address'].choices = addresses

    def clean_mailing_address(self):
        address_type = self.cleaned_data.get('mailing_address')
        try:
            return Address.objects.get(user=self.user, type=address_type)
        except Address.DoesNotExist:
            raise forms.ValidationError(_('Invalid address.'))

    def clean_billing_address(self):
        address_type = self.cleaned_data.get('billing_address')
        try:
            return Address.objects.get(user=self.user, type=address_type)
        except Address.DoesNotExist:
            raise forms.ValidationError(_('Invalid address.'))


class CustomMCField(forms.MultipleChoiceField):

    def clean(self, value):
        try:
            '''
            Check that these are all there.
            '''
            invalid = []
            for id in value:
                if not User.objects.filter(id=int(id)).exists():
                    print('APPENDING {}'.format(
                        id
                    ))
                    invalid.append(id)

            if not invalid:
                return User.objects.filter(pk__in=value)
            else:
                raise Exception('{} - these users do not exist'.format(
                    invalid
                ))

        except:
            raise Exception('Hard exception in custom field')


class RSVPForm(forms.Form):
    # number_of_children = forms.IntegerField(label=_('Number of Children'), initial=0,
    #                                         widget=forms.Select())

    # members = forms.MultipleChoiceField(
    #     initial=[]
    #     )

    def __init__(self, event, request=None, *args, **kwargs):
        self.event = event

        super().__init__(*args, **kwargs)

        choices = [(i, i) for i in range(1, event.max_guests_per_rsvp + 1)]

        self.fields['number_of_adults'] = forms.IntegerField(
            label=_('Number of Participants'),
            widget=forms.Select(),
            initial = len(choices)
            )

        self.fields['number_of_adults'].widget.choices = choices
        self.fields['number_of_adults'].widget.attrs = {
            'data-maxrsvp': event.max_guests_per_rsvp,
            'class': 'not-selectize'
        }

        ### HOST START ###

        # Always pre-populate with the host
        self.fields['host_type'] = forms.CharField(
            required=False,
            label=_('Host Type'),
            initial=_('Host'),
            widget=forms.TextInput(
                attrs={
                    'disabled': False if request.user.is_staff else True,
                    'class': 'hosttype'
                }
            )
        )

        self.fields['host_name'] = forms.CharField(
            required=False,
            label=_('Host Name'),
            widget=forms.TextInput(
                attrs={
                    'disabled':
                    True,
                    'class':
                    'hostinput member-select'
                }))

        ### HOST END ###


        ### GUEST START ###

        for x in range(2, event.max_guests_per_rsvp + 1):

            # This the guest type dropdown
            self.fields['guest_{}_type'.format(x)] = forms.ChoiceField(
                label=_('Guest Type'),
                widget=forms.Select(
                    attrs={
                        'class': 'not-selectize guest-type-dropdown',
                        'data-guestnumber': x
                    }
                ),
                choices = (
                    ('Member', 'Member'),
                    ('Guest', 'Guest')
                ),
                initial='Member'
            )

            self.fields['guest_{}_dropdown'.format(x)] = CustomMCField(
                required=False,
                label=_('Guest #{} Name'.format(x)),
                choices = [],
                # choices=[(u.id, '{} {} ({})'.format(u.first_name, u.last_name, u.option_club.name))
                #          for u in User.objects.filter(
                #              profile__show_in_roster=True, option_club=event.club)
                #          .order_by('last_name').exclude(id__in=registered)],
                widget=forms.SelectMultiple(attrs={
                    'data-guestnumber': x,
                    'data-maxItems': 1,
                    'class': 'not-selectize guestdropdown member-select guestdropdown-{}'.format(
                        x
                    )
                })
                )

            self.fields['guest_{}_input'.format(x)] = forms.CharField(
                required=False,
                label=_('Guest #{} Name'.format(x)),
                widget=forms.TextInput(attrs={
                    'data-guestnumber': x,
                    # 'class': 'not-selectize member-select',
                    'placeholder': 'Guest Name',
                    'class':  'guestinput guestinput-{}'.format(
                        x
                    )
                })
                )

        ### GUEST END ###

        if event.custom_question_1:
            self.fields['custom_answer_1'] = forms.CharField(label=event.custom_question_1)

        if event.custom_question_2:
            self.fields['custom_answer_2'] = forms.CharField(label=event.custom_question_2)

        if event.custom_question_3:
            self.fields['custom_answer_3'] = forms.CharField(label=event.custom_question_3)

        if event.custom_question_4:
            self.fields['custom_answer_4'] = forms.CharField(label=event.custom_question_4)

        if event.custom_question_5:
            self.fields['custom_answer_5'] = forms.CharField(label=event.custom_question_5)

        self.fields['notes'] = forms.CharField(
            label=_('Notes'),
            help_text='Optional - Special notes or instructions.',
            required=False)
