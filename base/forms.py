from datetime import date
from dateutil.relativedelta import relativedelta

from captcha.fields import ReCaptchaField
from django import forms
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from clublink.clubs.models import Club, Region

from clublink.users.models import User
from clublink.cms.models import Campaigner

from pprint import pprint

class SimpleContactForm(forms.Form):
    email_subject = None
    to_email = None
    email_template_text = None
    email_template_html = None

    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()
    phone = forms.CharField()
    additional_info = forms.CharField(required=False, label=_('Comments/Questions'),
                                      widget=forms.Textarea())
    captcha = ReCaptchaField()

    def send_email(self, club=None):
        context = {
            'club': club,
            'data': self.cleaned_data,
        }

        message = render_to_string(self.email_template_text, context=context)
        message_html = render_to_string(self.email_template_html, context=context)

        from_email = '{} {} <{}>'.format(self.cleaned_data['first_name'],
                                         self.cleaned_data['last_name'],
                                         getattr(settings, 'DEFAULT_FROM_EMAIL_ADDRESS'))

        if not isinstance(self.to_email, list):
            self.to_email = [self.to_email]


        # set it
        self.to_email = list(set(self.to_email))

        if self.__class__.__base__ == EventsForm and club and club.event_form_email and self.cleaned_data['location']:
            
            self.to_email.append(
                self.cleaned_data['location'].event_form_email
                )

        email = EmailMultiAlternatives(
            subject=self.email_subject, body=message, to=self.to_email,
            from_email=from_email, reply_to=[self.cleaned_data['email']])

        email.attach_alternative(message_html, 'text/html')

        email.send()


class GolfTournamentForm(SimpleContactForm):
    email_subject = 'Golf Tournament Inquiry Form'
    to_email = getattr(settings, 'CORPORATE_EVENTS_EMAIL_ADDRESS')
    email_template_text = 'email/forms/golf-tournament-inquiry.txt'
    email_template_html = 'email/forms/golf-tournament-inquiry.jinja'

    subscribe = forms.BooleanField(
        required=False, label=_('Sign up for our newsletter and current promotions.'),
        widget=forms.CheckboxInput())


class MembershipForm(SimpleContactForm):
    email_subject = 'Membership Inquiry Form'

    # Pass the request into the form, and then we can call the club sales email instead
    to_email = getattr(settings, 'MEMBERSHIP_SALES_EMAIL_ADDRESS')


    email_template_text = 'email/forms/membership-inquiry.txt'
    email_template_html = 'email/forms/membership-inquiry.jinja'

    date_of_birth = forms.DateField(required=False, input_formats=['%d/%m/%Y'],
                                    widget=forms.DateInput(attrs={'data-pikaday': True}))
    region = forms.ChoiceField()
    company = forms.CharField(required=False)

    subscribe = forms.BooleanField(
        required=False, label=_('Sign up for our newsletter and current promotions.'),
        widget=forms.CheckboxInput())

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.to_email = getattr(settings, 'MEMBERSHIP_SALES_EMAIL_ADDRESS')

        if settings.DEBUG:
            self.fields.pop('captcha')

        if request:
            region_superset = Region.objects.filter(site=request.site)

            if request.club and request.club.sales_email:
                self.to_email = request.club.sales_email
            elif request.site and request.site.id != 1:
                # TODO: Set this in config variables instead
                self.to_email = 'membershipsalesflorida@clublink.ca'

        else:
            region_superset = Region.objects.all()

        self.fields['region'].choices = [
            (r.id, r.name) for r in region_superset if r.clubs.count() > 0
        ]

    def clean_region(self):
        pk = self.cleaned_data.get('region')
        try:
            return Region.objects.get(pk=pk).name
        except Region.DoesNotExist:
            raise forms.ValidationError(_('Invalid region.'))

    def clean(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = timezone.localtime(timezone.now())
            jan_first = date(year=today.year, month=1, day=1)
            self.cleaned_data.update({
                'age_on_january1': relativedelta(jan_first, dob).years
            })
        return self.cleaned_data


class EventsForm(SimpleContactForm):
    TYPE_OF_EVENT_CHOICES = (
        ('', ''),
    )

    preferred_date = forms.CharField()
    number_of_guests = forms.CharField()

    def __init__(self, site=None, *args, **kwargs):
        kw_initial = kwargs.get('initial', {})

        self.club = kwargs.pop('club', None)

        if self.club:
            kw_initial.update({
                'location': self.club.pk,
            })

        kwargs['initial'] = kw_initial

        super().__init__(*args, **kwargs)

        self.fields['type_of_event'] = forms.ChoiceField(
            choices=self.TYPE_OF_EVENT_CHOICES, widget=forms.Select)

        if site:
            club_superset = Club.objects.filter(site=site)
        else:
            club_superset = Club.objects.all()

        club_choices = [('', '')] + [(c.pk, c.name) for c in club_superset.exclude(slug=None)]
        self.fields['location'] = forms.ChoiceField(choices=club_choices, widget=forms.Select)

    def clean_location(self):
        pk = self.cleaned_data['location']

        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            raise forms.ValidationError(_('Invalid location.'))

        return club


class WeddingsForm(EventsForm):
    email_subject = 'Weddings Inquiry Form'
    to_email = []
    email_template_text = 'email/forms/weddings-inquiry.txt'
    email_template_html = 'email/forms/weddings-inquiry.jinja'

    TYPE_OF_EVENT_CHOICES = (
        ('', ''),
        ('Ceremony & Reception', _('Ceremony & Reception')),
        ('Reception', _('Reception')),
        ('Ceremony', _('Ceremony')),
        ('Bridal Shower', _('Bridal Shower')),
        ('Rehearsal Party', _('Rehearsal Party')),
        ('Other', _('Other')),
    )

    def __init__(self, site=None, *args, **kwargs):
        self.to_email = getattr(settings, 'EVENTS_EMAIL_ADDRESSES')
        super().__init__(site, *args, **kwargs)

        if site:
            club_superset = Club.objects.filter(site=site)
        else:
            club_superset = Club.objects.all()

        club_choices = [('', '')] + [(c.pk, c.name) for c in club_superset.exclude(slug=None).exclude( no_weddings=True)]
        self.fields['location'] = forms.ChoiceField(choices=club_choices, widget=forms.Select)

    # def send_email(self, club=None):
    #     if club and club.event_form_email:
    #         self.to_email.append(club.event_form_email)
    #     super().send_email(club=club)
    #     if club and club.event_form_email:
    #         self.to_email = getattr(settings, 'EVENTS_EMAIL_ADDRESSES')


class MeetingsForm(EventsForm):
    email_subject = 'Meetings & Banquets Inquiry Form'
    to_email = []
    email_template_text = 'email/forms/meetings-inquiry.txt'
    email_template_html = 'email/forms/meetings-inquiry.jinja'

    TYPE_OF_EVENT_CHOICES = (
        ('', ''),
        ('Meeting', _('Meeting')),
        ('Banquet', _('Banquet')),
        ('Other', _('Other')),
    )

    def __init__(self, site=None, *args, **kwargs):
        self.to_email = getattr(settings, 'EVENTS_EMAIL_ADDRESSES')
        super().__init__(site, *args, **kwargs)
        if site:
            club_superset = Club.objects.filter(site=site)
        else:
            club_superset = Club.objects.all()

        club_choices = [('', '')] + [(c.pk, c.name) for c in club_superset.exclude(slug=None).exclude( no_meetings=True)]
        self.fields['location'] = forms.ChoiceField(choices=club_choices, widget=forms.Select)

    # def send_email(self, club=None):
    #     if club and club.event_form_email:
    #         self.to_email.append(club.event_form_email)
    #     super().send_email(club=club)
    #     if club and club.event_form_email:
    #         self.to_email = getattr(settings, 'EVENTS_EMAIL_ADDRESSES')

class GolfForLifeForm(forms.Form):    

    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()
    pincode = forms.CharField()    
    subscribe = forms.BooleanField(
        required=False, label=_('I agree.'),
        widget=forms.CheckboxInput())

    
    # Pass the request into the form, and then we can call the club sales email instead
    to_email = getattr(settings, 'MEMBERSHIP_SALES_EMAIL_ADDRESS')
    email_template_text = 'email/forms/membership-inquiry.txt'
    email_template_html = 'email/forms/membership-inquiry.jinja'
    email_subject = 'Golf for life Contest'


    def send_email(self, club=None):
        context = {
            'club': club,
            'data': self.cleaned_data,
        }

        # message = render_to_string(self.email_template_text, context=context)
        # message_html = render_to_string(self.email_template_html, context=context)

        # from_email = '{} {} <{}>'.format(self.cleaned_data['first_name'],
        #                                  self.cleaned_data['last_name'],
        #                                  getattr(settings, 'DEFAULT_FROM_EMAIL_ADDRESS'))

        # if not isinstance(self.to_email, list):
        #     self.to_email = [self.to_email]

        # # set it
        # self.to_email = list(set(self.to_email))

        # if self.__class__.__base__ == EventsForm and club and club.event_form_email and self.cleaned_data['location']:
            
        #     self.to_email.append(
        #         self.cleaned_data['location'].event_form_email
        #         )

        # email = EmailMultiAlternatives(
        #     subject=self.email_subject, body=message, to=self.to_email,
        #     from_email=from_email, reply_to=[self.cleaned_data['email']])

        # email.attach_alternative(message_html, 'text/html')

        # email.send()


    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.to_email = getattr(settings, 'MEMBERSHIP_SALES_EMAIL_ADDRESS')

        if request:
            region_superset = Region.objects.filter(site=request.site)

            if request.club and request.club.sales_email:
                self.to_email = request.club.sales_email
            elif request.site and request.site.id != 1:
                # TODO: Set this in config variables instead
                self.to_email = 'membershipsalesflorida@clublink.ca'
        else:
            region_superset = Region.objects.all()
        
    def isEmailValid(self):
        email = self.cleaned_data.get('email')
        userObjs = User.objects.filter(email__exact = email).order_by('id')
        length = len(userObjs)
        if length == 0:
            return [False]        
        return [True, email, userObjs[0].id]
    
    def isPinCodeValid(self, email,user_id):
        pincode = self.cleaned_data.get('pincode')
        fltCamp = Campaigner.objects.filter(pin_code__exact = pincode)
        
        if len(fltCamp) == 0:
            return [False,'Pin Code Error! Pin Code does not exist.']
        
        if len(fltCamp) > 1:
            return [False,'Pin Code Error! Pin Code is duplicated.']

        if hasattr(fltCamp[0],'user') and fltCamp[0].user.email == email:
            return [False, 'Pin Code Error! Pin Code is already used by the other user.']        
        
        fltCamp[0].user_id = user_id
        fltCamp[0].first_name = self.cleaned_data.get('first_name')
        fltCamp[0].second_name = self.cleaned_data.get('last_name')        
        fltCamp[0].opt_flag = 1 if self.cleaned_data.get('subscribe') else 0
        fltCamp[0].send_giftcard = 0
        fltCamp[0].msg_step = 0
        fltCamp[0].save()
        print(fltCamp.values())
        return [True , fltCamp[0].id]



    # def clean_region(self):
    #     pk = self.cleaned_data.get('region')
    #     try:
    #         return Region.objects.get(pk=pk).name
    #     except Region.DoesNotExist:
    #         raise forms.ValidationError(_('Invalid region.'))

    def clean(self):
        # dob = self.cleaned_data.get('date_of_birth')
        # if dob:
        #     today = timezone.localtime(timezone.now())
        #     jan_first = date(year=today.year, month=1, day=1)
        #     self.cleaned_data.update({
        #         'age_on_january1': relativedelta(jan_first, dob).years
        #     })
        return self.cleaned_data