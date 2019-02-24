import re
import datetime
from django import forms
from django.contrib.sites.models import Site
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import FilteredSelectMultiple

from django.utils import timezone
from clublink.clubs.models import ClubEvent, EventSeries
from clublink.cms import fields
from clublink.cms.models import ClubGallery, ClubPage
from clublink.cms.modules.club_sites.config import PAGE_TEMPLATES
from clublink.cms.widgets import SelectTimeWidget
from clublink.corp.models import News
from clublink.users.models import User
from clublink.cms.choices import RECURRENCE_PATTERN, RECURRENCE_REPETITION_TYPES, EVENTS_EDIT_DELETE_CHOICES
from clublink.cms.constants import REPETITION_UNTIL, NB_REPETITIONS, THIS_EVENT, THIS_EVENT_AND_FOLLOWING, ALL_EVENTS, \
    DEFAULT_START_TIME, DEFAULT_END_TIME, DEFAULT_REGISTRATION_OPEN_TIME, DEFAULT_REGISTRATION_CLOSE_TIME


class GalleryForm(forms.Form):
    name = fields.CharField()
    slug = fields.CharField()

    def __init__(self, club, *args, **kwargs):
        self.club = club
        self.gallery = None

        if 'gallery' in kwargs:
            self.gallery = kwargs.pop('gallery')

        if self.gallery:
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'name': self.gallery.name,
                'slug': self.gallery.slug,
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

    def clean_slug(self):
        data = self.cleaned_data['slug']

        galleries = ClubGallery.objects.all()
        if self.gallery:
            galleries = galleries.exclude(pk=self.gallery.pk)

        try:
            galleries.get(slug=data, club=self.club)
        except ClubGallery.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(_('This slug is already in use.'))

        return data


class TeamMemberForm(forms.Form):
    name = fields.CharField()
    job_title_en = fields.CharField(label=_('Job Title'))
    job_title_fr = fields.CharField(label=_('Job Title (French)'), required=False)
    photo = forms.ImageField(required=False)
    phone = fields.CharField(label=_('Phone Number'), required=False)
    email = fields.EmailField(required=False)

    def __init__(self, club, *args, **kwargs):
        self.club = club
        self.team_member = None

        if 'team_member' in kwargs:
            self.team_member = kwargs.pop('team_member')

        if self.team_member:
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'name': self.team_member.name,
                'job_title_en': self.team_member.job_title_en,
                'job_title_fr': self.team_member.job_title_fr,
                'phone': self.team_member.phone,
                'email': self.team_member.email,
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)


class NewsForm(forms.Form):
    publish_date = fields.DateField(input_formats=['%d/%m/%Y'],
                                    widget=forms.DateInput(attrs={'data-pikaday': True}))
    headline_en = fields.CharField(label=_('Headline'))
    headline_fr = fields.CharField(label=_('Headline (French)'), required=False)
    slug = fields.CharField()
    summary_en = fields.CharField(label=_('Summary'))
    summary_fr = fields.CharField(label=_('Summary (French)'), required=False)
    content_en = forms.CharField(label=_('Content'),
                                 widget=forms.Textarea(attrs={'data-tinymce': True}))
    content_fr = forms.CharField(label=_('Content (French)'), required=False,
                                 widget=forms.Textarea(attrs={'data-tinymce': True}))
    photo = forms.ImageField()

    def __init__(self, club, *args, **kwargs):
        self.club = club
        self.news = None

        if 'news' in kwargs:
            self.news = kwargs.pop('news')

        if self.news:
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'publish_date':
                    self.news.publish_date.strftime('%d/%m/%Y') if self.news.publish_date else '',
                'headline_en': self.news.headline_en,
                'headline_fr': self.news.headline_fr,
                'summary_en': self.news.summary_en,
                'summary_fr': self.news.summary_fr,
                'content_en': self.news.content_en,
                'content_fr': self.news.content_fr,
                'slug': self.news.slug,
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        if self.news:
            self.fields['photo'].required = False

    def clean(self):
        slug = self.cleaned_data.get('slug')
        headline = self.cleaned_data.get('headline')

        if not slug and headline:
            slug = headline

        self.cleaned_data['slug'] = slugify(slug)

        news = News.objects.filter(slug=self.cleaned_data.get('slug'))
        if self.news:
            news = news.exclude(pk=self.news.pk)
        if news.exists():
            self.add_error('slug', forms.ValidationError(_('Slug is already in use.')))

        return self.cleaned_data


class CalendarForm(forms.Form):
    # extra_fields
    recurrence_set = forms.BooleanField( label=_('Set recurrence parameters'), required=False,
                                         initial=False, widget=forms.CheckboxInput)
    recurrence_pattern = forms.ChoiceField(label=_('Pattern'), choices=RECURRENCE_PATTERN, required=False)
    recurrence_every = forms.IntegerField(label=_('Event happens every'), required=False)
    recurrence_repetition_types = forms.ChoiceField(label=_('Recurrence type'), required=False,
                                                    choices=RECURRENCE_REPETITION_TYPES)
    recurrence_until = forms.DateField(label=_('Until'), required=False, initial=None, widget=forms.SelectDateWidget())
    recurrence_repetitions = forms.IntegerField(label=_('Repetitions'), required=False)

    type = fields.ChoiceField(choices=ClubEvent.TYPE_CHOICES)
    name = fields.CharField()
    email = fields.EmailField(required=False)
    description = fields.TextareaField(widget=forms.Textarea(attrs={'data-tinymce': True}))
    start_date = forms.DateField(widget=forms.SelectDateWidget())
    start_time = forms.TimeField(initial=DEFAULT_START_TIME, widget=SelectTimeWidget(required=False, twelve_hr=True))
    end_date = forms.DateField(required=False, initial=None, widget=forms.SelectDateWidget())
    end_time = forms.TimeField(required=False, initial=DEFAULT_END_TIME,
                               widget=SelectTimeWidget(required=False, twelve_hr=True))
    max_attendees = fields.IntegerField(initial=0)
    max_guests_per_rsvp = fields.IntegerField(initial=1, min_value=1)
    photo = forms.ImageField(required=False)
    custom_question_1 = fields.CharField(required=False)
    custom_question_2 = fields.CharField(required=False)
    custom_question_3 = fields.CharField(required=False)
    custom_question_4 = fields.CharField(required=False)
    custom_question_5 = fields.CharField(required=False)
    online_registration = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=True,
        required=False)
    registration_open_date = forms.DateField(
        required=False, initial=None, widget=forms.SelectDateWidget())
    registration_open_time = forms.TimeField(
        required=False, initial=DEFAULT_REGISTRATION_OPEN_TIME, widget=SelectTimeWidget(required=False, twelve_hr=True))
    registration_close_date = forms.DateField(
        required=False, initial=None, widget=forms.SelectDateWidget())
    registration_close_time = forms.TimeField(
        required=False, initial=DEFAULT_REGISTRATION_CLOSE_TIME, widget=SelectTimeWidget(required=False, twelve_hr=True))

    def __init__(self, *args, **kwargs):
        self.event = None

        if 'event' in kwargs:
            self.event = kwargs.pop('event')

        if self.event:
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'start_date': self.event.start_date,
                'start_time': self.event.start_time,
                'end_date': self.event.end_date,
                'end_time': self.event.end_time,
                'name': self.event.name,
                'email': self.event.email,
                'description': self.event.description,
                'type': self.event.type,
                'max_attendees': self.event.max_attendees,
                'max_guests_per_rsvp': self.event.max_guests_per_rsvp,
                'custom_question_1': self.event.custom_question_1,
                'custom_question_2': self.event.custom_question_2,
                'custom_question_3': self.event.custom_question_3,
                'custom_question_4': self.event.custom_question_4,
                'custom_question_5': self.event.custom_question_5,
                'online_registration': self.event.online_registration,
                'registration_open_date': self.event.registration_open_date,
                'registration_open_time': self.event.registration_open_time,
                'registration_close_date': self.event.registration_close_date,
                'registration_close_time': self.event.registration_close_time
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data

        start_date = self.cleaned_data['start_date']
        start_time = self.cleaned_data['start_time']

        if self.cleaned_data.get('recurrence_set'):
            if not self.cleaned_data.get('recurrence_pattern'):
                self.add_error( 'recurrence_pattern', forms.ValidationError(_('This is a required field.')))

            if not self.cleaned_data.get('recurrence_every'):
                self.add_error( 'recurrence_every', forms.ValidationError(_('This is a required field.')))

            if self.cleaned_data.get('recurrence_repetition_types') == REPETITION_UNTIL \
                    and not self.cleaned_data.get('recurrence_until'):
                self.add_error( 'recurrence_until', forms.ValidationError(_('This is a required field.')))

            if self.cleaned_data.get('recurrence_repetition_types') == NB_REPETITIONS \
                    and not self.cleaned_data.get('recurrence_repetitions'):
                self.add_error('recurrence_repetitions', forms.ValidationError(_('This is a required field.')))

        if not self.cleaned_data.get('end_date'):
            self.cleaned_data['end_date'] = start_date

        if not self.cleaned_data.get('end_time'):
            self.cleaned_data['end_time'] = start_time

        end_date = self.cleaned_data['end_date']
        end_time = self.cleaned_data['end_time']
        email = self.cleaned_data['email']

        if end_date < start_date:
            self.add_error(
                'end_date',
                forms.ValidationError(_('End date must not be earlier than start date.')))

        if start_date == end_date and end_time < start_time:
            self.add_error(
                'end_time',
                forms.ValidationError(_('End time must not be earlier than start time.')))

        open_date = self.cleaned_data.get('registration_open_date')
        open_time = self.cleaned_data.get('registration_open_time')
        close_date = self.cleaned_data.get('registration_close_date')
        close_time = self.cleaned_data.get('registration_close_time')

        online_registration = self.cleaned_data.get('online_registration')

        if online_registration:
            if not open_date:
                self.add_error('registration_open_date',
                               forms.ValidationError(_('This field is required.')))
            if not open_time:
                self.add_error('registration_open_time',
                               forms.ValidationError(_('This field is required.')))
            if not close_date:
                self.add_error('registration_close_date',
                               forms.ValidationError(_('This field is required.')))
            if not close_time:
                self.add_error('registration_close_time',
                               forms.ValidationError(_('This field is required.')))

            if open_date and open_time and close_date and close_time:
                if open_date > end_date:
                    self.add_error(
                        'registration_open_date',
                        forms.ValidationError(_('Open date must not be later than end date.')))

                if close_date > end_date:
                    self.add_error(
                        'registration_close_date',
                        forms.ValidationError(_('Close date must not be later than end date.')))

                if close_date < open_date:
                    self.add_error(
                        'registration_close_date',
                        forms.ValidationError(_('Close date must not be earlier than open date.')))

                if open_date == close_date and close_time < open_time:
                    self.add_error(
                        'registration_close_time',
                        forms.ValidationError(_('Close time must not be earlier than open time.')))

        photo = self.cleaned_data.get ('photo', False)
        if photo and photo._size > 4 * 1024 * 1024:
            self.add_error('photo',forms.ValidationError(_('Image too large( > 4MB )')))

        return cleaned_data


class CalendarEditForm(CalendarForm):
    recurrence_set = forms.BooleanField( label=_('Update recurrence parameters'), required=False,
                                         initial=False, widget=forms.CheckboxInput)
    edit_options = forms.ChoiceField(label=_('Do you want to edit:'),required=False,
                                       choices=EVENTS_EDIT_DELETE_CHOICES,widget=forms.RadioSelect())

    def __init__(self, *args, **kwargs):
        super(CalendarEditForm, self).__init__(*args, **kwargs)

        if self.event.event_series:
            self.fields['edit_options'].required = True

    def clean(self):
        super(CalendarEditForm, self).clean()

        cleaned_data = self.cleaned_data
        registered_members = False
        recurrence_set = cleaned_data.get('recurrence_set', None)
        edit_options = cleaned_data.get ('edit_options')

        if recurrence_set and edit_options:
            try:
                self.event_series = EventSeries.objects.get (events=self.event)
                if edit_options == THIS_EVENT_AND_FOLLOWING:
                    events = self.event_series.events.filter(start_date__gte=self.event.start_date)
                if edit_options == ALL_EVENTS:
                    events = self.event_series.events.filter(start_date__gte=timezone.now())
                for event in events:
                    if event.total_guests > 0: registered_members = True
            except EventSeries.DoesNotExist:
                self.add_error ('edit_options', forms.ValidationError (_ ('This Event is not part of Series.')))

        if registered_members:
            self.add_error ('recurrence_set',
                            forms.ValidationError (_ ('Some events already have registered members. '
                                                      'Please unregister them before updating the recurrence pattern.')))

        return cleaned_data

class CalendarBulkDeleteForm(forms.Form):
    delete_options = forms.ChoiceField(label=_('Do you want to delete:'),required=True,
                                       choices=EVENTS_EDIT_DELETE_CHOICES,widget=forms.RadioSelect())

    def __init__(self, *args, **kwargs):
        self.event = None

        if 'event' in kwargs:
            self.event = kwargs.pop('event')

        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        registered_members = False
        delete_options = cleaned_data.get('delete_options', None)

        if delete_options and delete_options in (THIS_EVENT_AND_FOLLOWING, ALL_EVENTS):
            try:
                self.event_series = EventSeries.objects.get(events=self.event)
                if delete_options == THIS_EVENT_AND_FOLLOWING:
                    events = self.event_series.events.filter(start_date__gte=self.event.start_date)
                if delete_options == ALL_EVENTS:
                    events = self.event_series.events.all()
                for event in events:
                    if event.total_guests > 0: registered_members = True
            except EventSeries.DoesNotExist:
                self.add_error('delete_options', forms.ValidationError(_('This Event is not part of Series.')))

        elif self.event.total_guests > 0: registered_members = True

        if registered_members:
            self.add_error('delete_options',
                           forms.ValidationError (_('Some events already have registered members. '
                                                    'Please unregister and notify them of the change first.')))

        return cleaned_data


class ImageUploadForm(forms.Form):
    file = forms.ImageField(widget=forms.FileInput({'multiple': True}))


class PageForm(forms.Form):
    name_en = fields.CharField(label=_('Name'), required=False)
    name_fr = fields.CharField(label=_('Name (French)'), required=False)
    slug = fields.CharField(max_length=64)
    visibility = fields.ChoiceField(choices=ClubPage.VISIBILITY_CHOICES)
    show_address_bar = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=True,
        required=False)
    show_in_main_menu = forms.BooleanField(
        label=_('Show in Hamburger Menu'), required=False, initial=True,
        widget=forms.CheckboxInput)
    list_in_main_menu_subnav = forms.BooleanField(
        label=_('Duplicate in Hamburger Menu Subnav'), required=False, initial=False,
        widget=forms.CheckboxInput)
    name_in_main_menu_subnav_en = fields.CharField(
        label=_('Name in Hamburger Menu Subnav'), required=False)
    name_in_main_menu_subnav_fr = fields.CharField(
        label=_('Name in Hamburger Menu Subnav (French)'), required=False)
    show_page_nav = forms.BooleanField(
        label=_('Show Page Navigation'), required=False, initial=True,
        widget=forms.CheckboxInput)
    list_in_child_page_nav = forms.BooleanField(
        label=_('Show in Child Page Navigation'), required=False, initial=False,
        widget=forms.CheckboxInput)
    name_in_child_page_nav_en = fields.CharField(
        label=_('Name in Child Page Navigation'), required=False)
    name_in_child_page_nav_fr = fields.CharField(
        label=_('Name in Child Page Navigation (French)'), required=False)
    should_redirect = forms.BooleanField(
        required=False, initial=False, widget=forms.CheckboxInput)
    external_redirect = fields.CharField(required=False)
    opens_in_new_window = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=False,
        required=False)
    hidden_bucket = forms.BooleanField(required=False, initial=False)
    facebook_pixel_id = fields.CharField(required=False)


    def __init__(self, club, *args, **kwargs):
        self.club = club
        self.page = None

        if 'page' in kwargs:
            self.page = kwargs.pop('page')

        if self.page:
            kw_initial = kwargs.get('initial', {})
            p = self.page
            kwargs['initial'] = {
                'name_en': p.name_en,
                'name_fr': p.name_fr,
                'slug': p.slug,
                'visibility': p.visibility,
                'show_address_bar': p.show_address_bar,
                'parent': p.parent.pk if p.parent else None,
                'show_in_main_menu': p.show_in_main_menu,
                'list_in_main_menu_subnav': p.list_in_main_menu_subnav,
                'name_in_main_menu_subnav_en': p.name_in_main_menu_subnav_en,
                'name_in_main_menu_subnav_fr': p.name_in_main_menu_subnav_fr,
                'show_page_nav': p.show_page_nav,
                'list_in_child_page_nav': p.list_in_child_page_nav,
                'name_in_child_page_nav_en': p.name_in_child_page_nav_en,
                'name_in_child_page_nav_fr': p.name_in_child_page_nav_fr,
                'alias': p.alias.pk if p.alias else None,
                'should_redirect': p.should_redirect,
                'external_redirect': p.external_redirect,
                'internal_redirect': p.internal_redirect.pk if p.internal_redirect else None,
                'opens_in_new_window': p.opens_in_new_window,
                'hidden_bucket': p.hidden_bucket,
                'facebook_pixel_id': p.facebook_pixel_id
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        excludes = Q(parent=None, slug='')
        if self.page:
            excludes |= Q(pk=self.page.pk)
        linkable_pages = self.club.pages.exclude(excludes).order_by('full_path')

        if self.page and self.page.is_locked:
            self.fields.pop('slug')
        else:
            self.fields['parent'] = fields.ChoiceField(
                choices=[(None, 'No parent')] + [(p.pk, p.full_path) for p in linkable_pages],
                required=False)

        self.fields['alias'] = fields.ChoiceField(
            choices=[(None, 'No alias')] + [(p.pk, p.full_path) for p in linkable_pages],
            required=False)

        self.fields['internal_redirect'] = fields.ChoiceField(
            choices=[(None, 'No redirect')] + [(p.pk, p.full_path) for p in linkable_pages],
            required=False)

    def clean_parent(self):
        pk = self.cleaned_data['parent']
        parent = None

        if pk:
            try:
                parent = ClubPage.objects.get(pk=pk)
            except ClubPage.DoesNotExist:
                raise forms.ValidationError('Invalid parent.')

        return parent

    def clean_alias(self):
        pk = self.cleaned_data['alias']
        parent = None

        if pk:
            try:
                parent = ClubPage.objects.get(pk=pk)
            except ClubPage.DoesNotExist:
                raise forms.ValidationError('Invalid alias.')

        return parent

    def clean_internal_redirect(self):
        pk = self.cleaned_data['internal_redirect']
        parent = None

        if pk:
            try:
                parent = ClubPage.objects.get(pk=pk)
            except ClubPage.DoesNotExist:
                raise forms.ValidationError('Invalid redirect.')

        return parent

    def clean(self):
        cleaned_data = super().clean()

        slug = cleaned_data.get('slug', '')
        parent = cleaned_data.get('parent', None)

        if slug:
            if re.match(r'[^a-zA-Z0-9_-]', slug):
                self.add_error(
                    'slug', forms.ValidationError(_('Slug may only contain alphanumeric '
                                                    'characters, underscore and hyphens.')))
            else:
                pages = ClubPage.objects.filter(club=self.club, parent=parent, slug=slug)

                if self.page:
                    pages = pages.exclude(pk=self.page.pk)

                if pages.exists():
                    self.add_error(
                        'slug', forms.ValidationError(_('This slug is already in use.')))

        return cleaned_data


class SnippetsForm(forms.Form):
    title = fields.CharField(required=False)
    keywords = fields.CharField(required=False)
    description = fields.TextareaField(required=False)
    headline = fields.CharField(required=False)

    def __init__(self, page, locale, *args, **kwargs):
        self.page = page

        if 'prefix' not in kwargs:
            kwargs['prefix'] = locale

        template = PAGE_TEMPLATES.get(self.page.full_path, PAGE_TEMPLATES['*'])
        template_snippets = template.get('snippets', PAGE_TEMPLATES['*']['snippets'])

        kw_initial = kwargs.get('initial', {})
        kwargs['initial'] = {
            'title': self.page.get_snippet('title', fallback=False, locale=locale),
            'keywords': self.page.get_snippet('keywords', fallback=False, locale=locale),
            'description': self.page.get_snippet('description', fallback=False, locale=locale),
            'headline': self.page.get_snippet('headline', fallback=False, locale=locale),
        }

        for slug in template_snippets:
            kwargs['initial'][slug] = self.page.get_snippet(slug, fallback=False, locale=locale)

        kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        for slug in template_snippets:
            field_type = template_snippets[slug]

            if field_type == 'text':
                self.fields[slug] = fields.TextareaField(required=False)
            elif field_type == 'html':
                self.fields[slug] = forms.CharField(
                    required=False, widget=forms.Textarea(attrs={'data-tinymce': True}))
            else:
                self.fields[slug] = fields.CharField(required=False)


class PageImagesForm(forms.Form):
    def __init__(self, page, locale, *args, **kwargs):
        self.page = page

        if 'prefix' not in kwargs:
            kwargs['prefix'] = locale

        template = PAGE_TEMPLATES.get(self.page.full_path, PAGE_TEMPLATES['*'])
        template_images = template.get('images', PAGE_TEMPLATES['*']['images'])

        super().__init__(*args, **kwargs)

        for slug in template_images:
            label = template_images[slug]['label']
            self.fields[slug] = forms.ImageField(label=label, required=False)

class CalendarMessageForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    from_name = fields.CharField(
        required=True,
        initial='ClubLink'
        )
    reply_to = fields.EmailField(
        required=True, initial='no-reply@clublink.ca'
        )
    subject = fields.CharField(
        required=True
        )
    message = fields.TextareaField(
        required=True
        )