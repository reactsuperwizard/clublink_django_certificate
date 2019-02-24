from datetime import datetime, time, timedelta
from urllib.error import HTTPError

from dirtyfields import DirtyFieldsMixin
from django_mysql.models import JSONField
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.translation import get_language, ugettext_lazy as _

from clublink.base.clients.google import GoogleMapsClient
from clublink.base.utils import list_intersect, optimize_jpeg, RandomizedUploadPath
from clublink.clubs.builtins import PROVINCES, STATES
from clublink.clubs.managers import ClubManager, DepartmentManager

class Region(models.Model):
    slug = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    sort = models.IntegerField(default=0)
    site = models.ForeignKey(
        Site,
        blank=True,
        null=True,
        default=1,
        related_name='regions',
        on_delete=models.PROTECT
        )
    tee_time_url = models.URLField(
                    blank=True, null=True,
                    help_text='Used for US tee times that are region-specific'
                    )

    class Meta:
        ordering = ('sort', 'name',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Region: {}>'.format(self.name)

class Club(DirtyFieldsMixin, models.Model):
    SILVER = 'SI'
    GOLD = 'GO'
    PLATINUM = 'PL'
    PRESTIGE = 'PR'

    TIER_CHOICES = ((SILVER, _('Silver')), (GOLD, _('Gold')), (PLATINUM,
                                                               _('Platinum')),
                    (PRESTIGE, _('Prestige')))

    tier = models.CharField(
        max_length=2, choices=TIER_CHOICES, blank=True, null=True)

    slug = models.CharField(max_length=64, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=2, choices=PROVINCES + STATES, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    fax = models.CharField(max_length=30, null=True, blank=True)
    svg_logo = models.FileField(null=True, upload_to=RandomizedUploadPath('club_logos_svg'),
                                blank=True)
    logo = models.ImageField(null=True, upload_to=RandomizedUploadPath('club_logos'), blank=True)
    dark_logo = models.FileField(null=True, upload_to=RandomizedUploadPath('dark_logos'),
                                 blank=True)
    academy_logo = models.FileField(null=True, upload_to=RandomizedUploadPath('academy_logos'),
                                    blank=True)
    listing_image = models.ImageField(null=True, upload_to=RandomizedUploadPath('listing_image'),
                                      blank=True)
    code = models.CharField(max_length=4, unique=False)
    youtube_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    admins = models.ManyToManyField('users.User', related_name='clubs', blank=True)
    region = models.ForeignKey(
        Region,
        related_name='clubs',
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )
    daily_fee_location = models.BooleanField(default=False, help_text='NOTE: As per Brendan, also accounts for several other things in page scaffolding, and is therefore "needed" for building out pages for now.')
    hide_daily_fees = models.BooleanField(default=False, help_text='If you want to hide this club from http://clublink.ca/daily-fee-golf/')
    no_weddings = models.BooleanField(default=False, help_text='Avoid default showing in weddings')
    no_meetings = models.BooleanField(default=False, help_text='Avoid default showing in meetings')
    is_resort = models.BooleanField(default=False)
    bilingual = models.BooleanField(default=False)
    latitude = models.CharField(max_length=32, blank=True)
    longitude = models.CharField(max_length=32, blank=True)
    resort_url = models.URLField(null=True, blank=True)
    resort_weddings_url = models.URLField(null=True, blank=True)
    event_form_email = models.EmailField(null=True, blank=True)
    calendar_rsvp_email = models.EmailField(null=True, blank=True)

    # English uploads
    bistro_menu = models.FileField(null=True, upload_to=RandomizedUploadPath('bistro_menus'),
                                   blank=True)
    wedding_menu = models.FileField(null=True, upload_to=RandomizedUploadPath('wedding_menus'),
                                    blank=True)
    banquet_menu = models.FileField(null=True, upload_to=RandomizedUploadPath('banquet_menus'),
                                    blank=True)
    membership_brochure = models.FileField(null=True, upload_to=RandomizedUploadPath('membership_brochures'),
                                    blank=True)
    golf_tournament_menu = models.FileField(null=True, upload_to=RandomizedUploadPath('golf_tournament_menus'),
                                   blank=True)

    # French uploads
    bistro_menu_fr = models.FileField(null=True, upload_to=RandomizedUploadPath('bistro_menus'),
                                   blank=True)
    wedding_menu_fr = models.FileField(null=True, upload_to=RandomizedUploadPath('wedding_menus'),
                                    blank=True)
    banquet_menu_fr = models.FileField(null=True, upload_to=RandomizedUploadPath('banquet_menus'),
                                    blank=True)
    membership_brochure_fr = models.FileField(null=True, upload_to=RandomizedUploadPath('membership_brochures'),
                                    blank=True)
    golf_tournament_menu_fr = models.FileField(
        null=True,
        upload_to=RandomizedUploadPath('golf_tournament_menus'),
        blank=True)

    teeitup = models.URLField(blank=True, null=True, help_text='What is the TeeItUp url for iframing?')
    site = models.ForeignKey(
        Site,
        blank=True,
        null=True,
        related_name='clubs',
        on_delete=models.PROTECT
        )

    bcg_style = models.BooleanField(default=False, help_text='Use CMS style page like bcg?')

    use_corp_styles = models.BooleanField(
        default=False,
        help_text='This is meant to use the same background as your corp-page equivalent based on the path'
        )

    sales_email = models.EmailField(blank=True, null=True, help_text='Override email for membership inquiries.  Otherwise, it uses the generic one on the server.')

    class Meta:
        ordering = ('name',)

    objects = ClubManager()

    def get_club_tier(self):
        return getattr(Club, self.tier, None)

    @property
    def thumbor_svg_logo(self):
        path = self.svg_logo.url.split('amazonaws.com')[-1]
        return (settings.S3_BASE + '/trim/filters:quality(80):format(png)' + path)

    @property
    def logo_url(self):
        from django.conf import settings
        import os
        config = os.environ.get('DJANGO_CONFIGURATION', None)
        if self.logo:
            if 'development' in config.lower():
                url = 'https://stage-club.s3.amazonaws.com/media/' + self.logo.url.split('/static/')[-1]
            else:
                url = self.logo.url
        else:
            url = ''
        return url

    @property
    def is_us_club(self):
        return self.state in [s[0] for s in STATES]

    @property
    def country(self):
        if self.is_us_club:
            return _('USA')
        elif self.state in [p[0] for p in PROVINCES]:
            return _('Canada')
        return None

    @property
    def has_address(self):
        return bool(self.address or self.city or self.state or self.postal_code)

    def get_full_address(self):
        return '{}, {}, {} {}'.format(self.address, self.city, self.state, self.postal_code)

    def geocode(self):
        gmaps = GoogleMapsClient()
        try:
            lat, lng = gmaps.get_lat_lng('{}, {}'.format(self.name, self.get_full_address()))
        except HTTPError:
            pass
        else:
            self.latitude = lat if lat is not None else ''
            self.longitude = lng if lng is not None else ''

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Club: {}>'.format(self.name)

    def save(self, *args, **kwargs):
        dirty_fields = self.get_dirty_fields()

        geodata_changed = list_intersect(dirty_fields.keys(),
                                         ['name', 'address', 'city', 'state', 'postal_code'])

        if geodata_changed:
            self.geocode()

        super().save(*args, **kwargs)

        if 'listing_image' in dirty_fields and self.listing_image:
            optimize_jpeg(self.listing_image)


class TeamMember(DirtyFieldsMixin, models.Model):
    club = models.ForeignKey(
        Club,
        related_name='team_members',
        on_delete=models.PROTECT
        )
    name = models.CharField(max_length=255)
    job_title_en = models.CharField(max_length=255)
    job_title_fr = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255)
    email = models.EmailField()
    photo = models.ImageField(
        null=True, upload_to=RandomizedUploadPath('team_member'), blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ('sort',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<TeamMember: {}>'.format(self.name)

    @property
    def job_title(self):
        return getattr(self, 'job_title_{}'.format(get_language()), self.job_title_en)

    def save(self, *args, **kwargs):
        dirty_fields = self.get_dirty_fields()

        super().save(*args, **kwargs)

        if 'photo' in dirty_fields and self.photo:
            optimize_jpeg(self.photo)


class Department(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=2)
    clubs = models.ManyToManyField(Club, related_name='departments', blank=True)
    hidden = models.BooleanField(default=False)
    admins = models.ManyToManyField('users.User', related_name='departments', blank=True)
    director_email = models.EmailField(blank=True)

    class Meta:
        ordering = ('name',)

    objects = DepartmentManager()

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Department: {}>'.format(self.name)


class EventSeries(models.Model):
    created = models.DateTimeField(default=timezone.now)

class ClubEvent(models.Model):
    MEMBER_EVENT = 0
    NOTICE = 1
    OUTSIDE_EVENT = 2

    TYPE_CHOICES = (
        (MEMBER_EVENT, _('Member Event')),
        (NOTICE, _('Notice')),
        (OUTSIDE_EVENT, _('Outside Event')),
    )

    club = models.ForeignKey(
        Club,
        related_name='events',
        on_delete=models.PROTECT
        )
    event_series = models.ForeignKey(
        EventSeries,
        related_name='events',
        on_delete=models.PROTECT,
        null = True
        )
    name = models.CharField(max_length=255)
    email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        help_text='Override for event contact')
    description = models.TextField()
    start_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_date = models.DateField()
    end_time = models.TimeField(null=True, blank=True)
    max_attendees = models.IntegerField(default=0)
    max_guests_per_rsvp = models.IntegerField(default=1)
    photo = models.ImageField(upload_to=RandomizedUploadPath('club_events'), null=True, blank=True)
    type = models.IntegerField(choices=TYPE_CHOICES)
    online_registration = models.BooleanField(default=False)
    registration_open_date = models.DateField(null=True, blank=True)
    registration_open_time = models.TimeField(null=True, blank=True)
    registration_close_date = models.DateField(null=True, blank=True)
    registration_close_time = models.TimeField(null=True, blank=True)
    custom_question_1 = models.CharField(max_length=255, null=True, blank=True)
    custom_question_2 = models.CharField(max_length=255, null=True, blank=True)
    custom_question_3 = models.CharField(max_length=255, null=True, blank=True)
    custom_question_4 = models.CharField(max_length=255, null=True, blank=True)
    custom_question_5 = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ('start_date', 'start_time')

    class InvalidGuestCount(Exception):
        pass

    class LimitExceeded(Exception):
        pass

    class AlreadyAttending(Exception):
        pass

    def __str__(self):
        return self.name

    @property
    def start_datetime(self):
        dt = datetime.combine(self.start_date, self.start_time)
        return timezone.make_aware(dt)

    @property
    def end_datetime(self):
        dt = datetime.combine(self.end_date, self.end_time)
        return timezone.make_aware(dt)

    @property
    def date(self):
        if self.all_day:
            return self.start_datetime.strftime('%B %-d')

        d = self.start_datetime.strftime('%B %-d, %-I:%M%p')
        if not self.instant:
            d += ' - {}'.format(self.end_datetime.strftime('%B %-d, %-I:%M%p'))

        return d

    @property
    def all_day(self):
        start = datetime.combine(self.start_date, self.start_time)
        end = datetime.combine(self.end_date, self.end_time)
        twenty_four = start + timedelta(hours=24) == end
        return twenty_four and self.start_time == time(hour=0, minute=0, second=0)

    @property
    def instant(self):
        start = datetime.combine(self.start_date, self.start_time)
        end = datetime.combine(self.end_date, self.end_time)
        return start == end

    @property
    def total_guests(self):
        num_guests = models.F('number_of_adults') + models.F('number_of_children')
        query = self.rsvps.filter(parent__isnull=True).aggregate(number_of_guests=models.Sum(num_guests))
        return query.get('number_of_guests') or 0

    @property
    def is_full(self):
        if not self.max_attendees:
            return False
        return self.total_guests >= self.max_attendees

    @property
    def registration_open_datetime(self):
        if self.registration_open_date and self.registration_open_time:
            dt = datetime.combine(self.registration_open_date, self.registration_open_time)
            return timezone.make_aware(dt)
        return None

    @property
    def registration_close_datetime(self):
        if self.registration_close_date and self.registration_close_time:
            dt = datetime.combine(self.registration_close_date, self.registration_close_time)
            return timezone.make_aware(dt)
        return None

    @property
    def all_possible_registrants(self, user=None):
        from clublink.users.models import User
        return User.objects.all()[6000:6100]

    @property
    def all_registrants(self):
        userids = self.rsvps.values('user')
        from clublink.users.models import User
        return User.objects.filter(id__in=userids)

    @property
    def visible_registrants(self):
        all_users = self.all_registrants
        return all_users.filter(profile__show_in_roster=True).order_by('last_name')

    @property
    def hidden_registrants_count(self):
        return self.rsvps.filter(user__profile__show_in_roster=False).count()

    @property
    def total_registrants_count(self):
        return self.rsvps.filter(parent__isnull=True).count()

    @property
    def is_registration_open(self):
        if not self.online_registration:
            return False

        if self.registration_open_datetime and timezone.now() < self.registration_open_datetime:
            return False

        if self.registration_close_datetime and timezone.now() > self.registration_close_datetime:
            return False

        return True

    def is_rsvped(self, user):
        return self.rsvps.filter(user=user).exists()

    def rsvp(self, user, number_of_adults=1, number_of_children=0, custom_answer_1='',
             custom_answer_2='', custom_answer_3='', custom_answer_4='', custom_answer_5='', parent=None, **kwargs):
        number_of_guests = number_of_adults + number_of_children
        if number_of_guests < 1 or number_of_guests > self.max_guests_per_rsvp:
            raise self.InvalidGuestCount('The max number of guests for this event is {}'.format(self.max_guests_per_rsvp))

        if self.max_attendees and number_of_guests + self.total_guests > self.max_attendees:
            raise self.LimitExceeded('This event is already at full capacity.')

        if self.is_rsvped(user):
            raise self.AlreadyAttending('{} {} is already registered for this event.'.format(user.first_name, user.last_name))

        return ClubEventRSVP.objects.create(
            user=user, event=self, number_of_adults=number_of_adults,
            number_of_children=number_of_children, custom_answer_1=custom_answer_1,
            custom_answer_2=custom_answer_2, custom_answer_3=custom_answer_3,
            custom_answer_4=custom_answer_4, custom_answer_5=custom_answer_5,
            parent=parent
            )


class ClubEventRSVP(models.Model):
    created = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(
        'users.User',
        related_name='club_event_rsvps',
        on_delete=models.PROTECT
        )
    event = models.ForeignKey(
        ClubEvent,
        related_name='rsvps',
        on_delete=models.PROTECT
        )
    number_of_adults = models.IntegerField(default=1)
    number_of_children = models.IntegerField(default=0)

    guest_data = JSONField(
        default=dict,
        help_text='''
        Django does not have a native in-built JSONField for MySQL.
        Instead of hardcoding the number of guests allowable (like the below fields),
        we are adding a JSONField to store guest data. This will also help with futureproofing 
        the model for email and contact info storage at a later point.
        '''
        )

    custom_answer_1 = models.CharField(max_length=255, blank=True)
    custom_answer_2 = models.CharField(max_length=255, blank=True)
    custom_answer_3 = models.CharField(max_length=255, blank=True)
    custom_answer_4 = models.CharField(max_length=255, blank=True)
    custom_answer_5 = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        'clubs.ClubEventRSVP',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=('Who did the original RSVP?'),
        related_name='children'
        )

    class Meta:
        ordering = ('created',)

    @property
    def number_of_guests(self):
        return self.number_of_adults + self.number_of_children

    @property
    def confirmation_number(self):
        return '{}-{}'.format(self.event.pk, self.pk)

    def get_data_attrs(self):
        '''
        This is used to create a set of attrs that can be passed to the form field, which in turn is used by selectize to create initial values.

        All this because they didn't write this properly with ModelForm's in the first place.
        This can't be undone very easily now because of how ingrained the data is with all parts of the system.
        '''
        attrs = {}

        x = 2
        for rsvp in self.children.all():
            attrs['guest_{}_dropdown'.format(x)] = {
                'data-value': rsvp.user.id, 'data-displayname': '{} {} ({})'.format(
                    rsvp.user.first_name,
                    rsvp.user.last_name,
                    rsvp.user.option_club.name
                )
                }
            x += 1
        return attrs

    def get_initial_form_data(self, editmode=False, behalf=None):
        '''
        This helps populate the ClubEventRSVP form, which is not a ModelForm,
        so that we can hydrate it and allow for some edits.
        '''

        # Populate the host information first
        initial = {
            'number_of_adults': self.number_of_guests,
            'host_type': _('Host'),
        }

        if behalf or not editmode:
            # initial['host_name'] = '{} {} ({})'.format(self.user.first_name,
            #                     self.user.last_name,
            #                     self.user.option_club_name)

            # Then, the other clublink member guests
            x = 2
            for rsvp in self.children.all():
                initial['guest_{}_type'.format(x)] = 'Member'
                initial['guest_{}_dropdown'.format(x)] = rsvp.user.id
                print('RSVP: ', rsvp.user.id)
                x += 1

            # Finally, the non-member guests
            guests = self.guest_data
            if guests:
                for g in guests:
                    initial['guest_{}_type'.format(x)] = 'Guest'
                    initial['guest_{}_input'.format(x)] = g['name']
                    x+=1

            initial['notes'] = self.notes

        return initial




sync_order = [Region, Club, TeamMember, Department, ClubEvent, ClubEventRSVP]
