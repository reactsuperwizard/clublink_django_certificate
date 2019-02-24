import csv
import io
import logging
import pendulum
from datetime import datetime
from io import BytesIO
from PIL import Image

from django.core.files import File
from django.contrib import messages
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.views.generic import FormView
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import redirect, reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.mail import EmailMessage

from clublink.clubs.models import Club, ClubEvent, TeamMember, ClubEventRSVP, EventSeries
from clublink.users.models import User
from clublink.cms.models import (
    ClubGallery,
    ClubGalleryImage,
    ClubImage,
    ClubPage,
)
from clublink.cms.modules.club_sites.forms import (
    CalendarForm,
    CalendarEditForm,
    CalendarBulkDeleteForm,
    GalleryForm,
    ImageUploadForm,
    PageForm,
    PageImagesForm,
    SnippetsForm,
    TeamMemberForm,
    CalendarMessageForm
)

from clublink.cms.modules.corp_site.forms import (
    NewsForm,
)
from clublink.cms.views import CMSView
from clublink.cms.constants import DAILY, WEEKLY, MONTHLY, ANNUALLY, THIS_EVENT, THIS_EVENT_AND_FOLLOWING, ALL_EVENTS, \
    DEFAULT_START_TIME, DEFAULT_END_TIME, DEFAULT_REGISTRATION_OPEN_TIME, DEFAULT_REGISTRATION_CLOSE_TIME, NOTICE, \
    MEMBER_EVENT, OUTSIDE_EVENT

from clublink.clubs.forms import (RSVPForm)

from clublink.corp.models import News

from clublink.clubs.utils import (send_cancel_rsvp_email_to_admin, send_cancel_rsvp_email_to_member, send_rsvp_email_to_admin, send_rsvp_email_to_member)

class ClubSiteView(CMSView):
    template = 'cms/club_site/home.jinja'
    clubs = Club.objects.none()
    club = None
    should_redirect = True

    def get_breadcrumbs(self, request, *args, **kwargs):

        home_url = reverse('club-site.home', kwargs={'club_pk': self.club.pk})

        return [
            (home_url, _('Club Site')),
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update(
            {'cms_module': 'club_site',
            'page': None,
            'clubs': self.clubs,
            'club': self.club,
            'sites': Site.objects.prefetch_related(),
            'current_site': get_current_site(request)
            })
        return context

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        club_pk = kwargs.get('club_pk')

        if request.user.is_superuser:
            self.clubs = Club.objects.all()
        else:
            self.clubs = request.user.clubs.all()

        self.clubs = self.clubs.exclude(slug=None)

        if self.clubs.count() < 0:
            raise PermissionDenied()

        if club_pk is None:
            if 'cms_club' in request.session:
                try:
                    self.club = self.clubs.get(pk=request.session.get('cms_club'))
                except Club.DoesNotExist:
                    pass

            if not self.club:
                self.club = self.clubs.first()
        else:
            try:
                self.club = self.clubs.get(pk=club_pk)
            except Club.DoesNotExist:
                raise PermissionDenied()

        if club_pk is None and self.should_redirect:
            return redirect(reverse('club-site.home', kwargs={'club_pk': self.club.pk}))

        return response


    def _get_pendulum_inst(self, start, end):
        return pendulum.instance(datetime.combine(start, end))

    def _get_time_date_differences(self, event, data):
        """Here we define the date and time differences"""
        differences = {}
        event_start = self._get_pendulum_inst(event.start_date, event.start_time)
        data_start = self._get_pendulum_inst(data['start_date'], data['start_time'])
        differences['start'] = event_start.diff(data_start, False)

        event_end = self._get_pendulum_inst(event.end_date, event.end_time)
        data_end = self._get_pendulum_inst(data['end_date'], data['end_time'])
        differences['end'] = event_end.diff(data_end, False)

        if data['registration_open_date'] and data['registration_open_time']:
            data_registration_open = self._get_pendulum_inst(data['registration_open_date'],
                                                             data['registration_open_time'])

            differences['registration_open'] = data_registration_open.diff(data_start, False)

        if data['registration_close_date'] and data['registration_close_time']:
            data_registration_close = self._get_pendulum_inst(data['registration_close_date'],
                                                              data['registration_close_time'])

            differences['registration_close'] = data_registration_close.diff(data_start, False)

        return differences



    def _update_recursive_events(self, edited_event, recurrence_data, data, img_bytes = None):
        edited_event = edited_event.first()
        event_recc_data = data.copy()

        try:
            self.event_series = EventSeries.objects.get(events=edited_event)
        except EventSeries.DoesNotExist:
            pass

        if recurrence_data['recurrence_set']:
            self.events_to_update = self.event_series.events.filter(start_date__gt=edited_event.start_date)
            self.events_to_update.delete()
            self._generate_recursive_events (recurrence_data, data, img_bytes, self.event_series)

        else:
            if recurrence_data['edit_options'] == THIS_EVENT_AND_FOLLOWING:
                self.events_to_update = self.event_series.events.filter (start_date__gt=edited_event.start_date)

            if recurrence_data['edit_options'] == ALL_EVENTS:
                self.events_to_update = self.event_series.events.filter (start_date__gt=timezone.now())

            differences = self._get_time_date_differences(edited_event, data)

            for event in self.events_to_update:
                event_start = self._get_pendulum_inst(event.start_date, event.start_time)
                event_end = self._get_pendulum_inst(event.end_date, event.end_time)

                event_new_start = event_start.add(seconds=(differences['start'].in_seconds()))
                event_recc_data['start_date'] = event_new_start.date()
                event_recc_data['end_date'] = event_end.add(seconds=(differences['end'].in_seconds())).date()

                if data['registration_open_date'] and data['registration_open_time']:
                    event_recc_data['registration_open_date'] = event_new_start.\
                        subtract(seconds=(differences['registration_open'].in_seconds())).date()

                if data['registration_close_date'] and data['registration_close_time']:
                    event_recc_data['registration_close_date'] = event_new_start. \
                        subtract(seconds=(differences['registration_close'].in_seconds())).date()

                event.__dict__.update(event_recc_data)

                if img_bytes:
                    photo = BytesIO(img_bytes)
                    photo.seek(0)
                    event.photo.save("image_%s" % event.pk, File(photo))

                event.save()

        return data

    def _generate_recursive_events(self, recurrence_data, data, img_bytes = None, event_series = None):
        event_data = data.copy()
        repetitions = 0

        #EventSeries
        event_data['event_series'] = event_series if event_series else EventSeries.objects.create()

        duration = None
        if recurrence_data['recurrence_repetitions'] is None and recurrence_data['recurrence_until'] is not None:
            recurrence_start = self._get_pendulum_inst(event_data['start_date'], event_data['start_time'])
            recurrence_end = self._get_pendulum_inst(recurrence_data['recurrence_until'], event_data['end_time'])
            duration = recurrence_end - recurrence_start

        if duration:
            if recurrence_data['recurrence_pattern'] == DAILY:
                repetitions = duration.in_days() / recurrence_data['recurrence_every']
            if recurrence_data['recurrence_pattern'] == WEEKLY:
                repetitions = duration.in_weeks () / recurrence_data['recurrence_every']
            if recurrence_data['recurrence_pattern'] == MONTHLY:
                repetitions = duration.in_months () / recurrence_data['recurrence_every']
            if recurrence_data['recurrence_pattern'] == ANNUALLY:
                repetitions = duration.in_years () / recurrence_data['recurrence_every']
        else:
            repetitions = recurrence_data['recurrence_repetitions']

        for i in range(0, round(repetitions)):
            reg_open = reg_close = False
            event_start = self._get_pendulum_inst(event_data['start_date'], event_data['start_time'])
            event_end = self._get_pendulum_inst(event_data['end_date'], event_data['end_time'])

            if event_data['registration_open_date'] and event_data['registration_open_time']:
                event_registration_open = self._get_pendulum_inst(event_data['registration_open_date'],
                                                                  event_data['registration_open_time'])
                reg_open = True
            if event_data['registration_close_date'] and event_data['registration_close_time']:
                event_registration_end = self._get_pendulum_inst(event_data['registration_close_date'],
                                                                 event_data['registration_close_time'])
                reg_close = True

            if recurrence_data['recurrence_pattern'] == DAILY:
                event_data['start_date'] = event_start.add (days=recurrence_data['recurrence_every']).date ()
                event_data['end_date'] = event_end.add (days=recurrence_data['recurrence_every']).date ()
                if reg_open:
                    event_data['registration_open_date'] = event_registration_open.\
                        add(days=recurrence_data['recurrence_every']).date()
                if reg_close:
                    event_data['registration_close_date'] = event_registration_end. \
                        add (days=recurrence_data['recurrence_every']).date ()

            if recurrence_data['recurrence_pattern'] == WEEKLY:
                event_data['start_date'] = event_start.add(weeks=recurrence_data['recurrence_every']).date()
                event_data['end_date'] = event_end.add (weeks=recurrence_data['recurrence_every']).date ()
                if reg_open:
                    event_data['registration_open_date'] = event_registration_open. \
                        add (weeks=recurrence_data['recurrence_every']).date ()
                if reg_close:
                    event_data['registration_close_date'] = event_registration_end. \
                        add (weeks=recurrence_data['recurrence_every']).date ()

            if recurrence_data['recurrence_pattern'] == MONTHLY:
                event_data['start_date'] = event_start.add (months=recurrence_data['recurrence_every']).date ()
                event_data['end_date'] = event_end.add (months=recurrence_data['recurrence_every']).date ()
                if reg_open:
                    event_data['registration_open_date'] = event_registration_open. \
                        add (months=recurrence_data['recurrence_every']).date ()
                if reg_close:
                    event_data['registration_close_date'] = event_registration_end. \
                        add (months=recurrence_data['recurrence_every']).date ()

            if recurrence_data['recurrence_pattern'] == ANNUALLY:
                event_data['start_date'] = event_start.add (years=recurrence_data['recurrence_every']).date ()
                event_data['end_date'] = event_end.add (years=recurrence_data['recurrence_every']).date ()
                if reg_open:
                    event_data['registration_open_date'] = event_registration_open. \
                        add (years=recurrence_data['recurrence_every']).date ()
                if reg_close:
                    event_data['registration_close_date'] = event_registration_end. \
                        add (years=recurrence_data['recurrence_every']).date ()

            event = ClubEvent.objects.create(club=self.club, **event_data)

            if img_bytes:
                photo = BytesIO(img_bytes)
                photo.seek(0)
                event.photo.save("image_%s" % event.pk, File(photo))
                event.save()

        return event_data

class SwitchClub(ClubSiteView):
    template = 'cms/club_site/switch.jinja'
    should_redirect = False

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.switch-club'), _('Switch Club'))
        ]

    def post(self, request, *args, **kwargs):
        pk = request.POST.get('pk')

        try:
            Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            pass
        else:
            request.session['cms_club'] = pk
            return redirect(reverse('club-site.home', kwargs={'club_pk': pk}))

        return self.get(request, *args, **kwargs)

class PagesView(ClubSiteView):
    template = 'cms/club_site/pages.jinja'

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.pages', kwargs={'club_pk': self.club.pk}), _('Pages')),
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({
            'pages': self.club.pages.filter(parent=None).distinct().order_by('sort')
        })
        return context


class PagesAddView(PagesView):
    template = 'cms/club_site/pages-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = PageForm(self.club)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.pages-add', kwargs={'club_pk': self.club.pk}), _('Add New'))
        ]

    def post(self, request, *args, **kwargs):
        self.form = PageForm(self.club, request.POST)

        if self.form.is_valid():
            try:
                page = ClubPage.objects.create(club=self.club, **self.form.cleaned_data)
            except IntegrityError:
                messages.add_message(request, messages.ERROR, _('An error occured.'))
            else:
                edit_url = reverse('club-site.pages-edit', kwargs={
                    'club_pk': self.club.pk, 'page_pk': page.pk})
                messages.add_message(request, messages.SUCCESS, _('Page was created.'))
                return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class PagesReorderView(PagesView):
    template = 'cms/club_site/pages-reorder.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(self, request, *args, **kwargs)
        parent_id = request.GET.get('parent_id', None)
        context.update({
            'parent': self.club.pages.get(pk=parent_id) if parent_id else None,
            'pages': self.club.pages.filter(parent_id=parent_id).order_by('sort'),
        })
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        reorder_url = reverse('club-site.pages-reorder', kwargs={'club_pk': self.club.pk})
        return crumbs + [
            (reorder_url, _('Re-order'))
        ]

    def post(self, request, *args, **kwargs):
        for i, pk in enumerate(request.POST.getlist('pk', [])):
            try:
                page = self.club.pages.get(pk=pk)
            except ClubGallery.DoesNotExist:
                pass
            else:
                page.sort = i
                page.save()
        messages.add_message(request, messages.SUCCESS, _('Pages re-ordered.'))
        return redirect(request.get_full_path())


class PagesDetailsView(PagesView):
    page = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.page = self.club.pages.get(pk=kwargs.get('page_pk'))
        except ClubPage.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Page does not exist.'))
            return redirect(reverse('club-site.pages', kwargs={'club_pk': self.club.pk}))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'page': self.page})
        return context


class PagesEditView(PagesDetailsView):
    template = 'cms/club_site/pages-edit.jinja'
    page_form = None
    snippets_form_en = None
    snippets_form_fr = None
    images_form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        if self.page:
            self.page_form = PageForm(self.club, page=self.page)
            self.snippets_form_en = SnippetsForm(self.page, locale='en')
            self.snippets_form_fr = SnippetsForm(self.page, locale='fr')
            self.images_form = PageImagesForm(self.page, locale='en')

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({
            'page_form': self.page_form,
            'snippets_form_en': self.snippets_form_en,
            'snippets_form_fr': self.snippets_form_fr,
            'images_form': self.images_form,
        })
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('club-site.pages-edit', kwargs={
            'club_pk': self.club.pk, 'page_pk': self.page.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):

        edit_url = reverse('club-site.pages-edit', kwargs={
            'club_pk': self.club.pk, 'page_pk': self.page.pk})

        if 'settings' in request.POST:
            self.page_form = PageForm(self.club, request.POST, page=self.page)

            if self.page_form.is_valid():
                for field in self.page_form.cleaned_data:
                    setattr(self.page, field, self.page_form.cleaned_data[field])
                try:
                    self.page.save()
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, _('An error occured.'))
                else:
                    messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
                    return redirect(edit_url)

        elif 'snippets_en' in request.POST or 'snippets_fr' in request.POST:
            self.snippets_form_en = SnippetsForm(self.page, 'en', request.POST)
            self.snippets_form_fr = SnippetsForm(self.page, 'fr', request.POST)

            locale = 'en'
            snippet_form = self.snippets_form_en

            if 'snippets_fr' in request.POST:
                locale = 'fr'
                snippet_form = self.snippets_form_fr

            if snippet_form.is_valid():
                for field in snippet_form.fields:
                    value = snippet_form.cleaned_data.get(field, None)
                    if value:
                        self.page.set_snippet(field, locale, value)
                    else:
                        self.page.snippets.filter(slug=field, locale=locale).delete()

            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect('{}?edit-snippets&locale={}'.format(edit_url, locale))

        elif 'images' in request.POST:
            self.images_form = PageImagesForm(self.page, 'en', request.POST, request.FILES)

            if self.images_form.is_valid():
                for field in self.images_form.fields:
                    value = self.images_form.cleaned_data.get(field, None)
                    if value:
                        ClubImage.objects.update_or_create(
                            page=self.page, slug=field, locale='en', defaults={'image': value})

            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect('{}?edit-images'.format(edit_url))

        return self.get(request, *args, **kwargs)


class PagesDeleteView(PagesDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        if self.page and self.page.is_locked and not request.user.is_superuser:
            messages.add_message(request, messages.WARNING, _('You cannot delete system pages.'))
            return redirect(reverse('club-site.pages', kwargs={'club_pk': self.club.pk}))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the page: <strong>{}</strong>?')
        message = message.format(self.page.name or '{}/'.format(self.page.full_path))
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('club-site.pages-delete', kwargs={
            'club_pk': self.club.pk, 'page_pk': self.page.pk})
        return crumbs + [
            (delete_url, _('Delete')),
        ]

    def post(self, request, *args, **kwargs):
        self.page.delete()
        messages.add_message(request, messages.SUCCESS, _('Page deleted.'))
        edit_url = reverse('club-site.pages', kwargs={'club_pk': self.club.pk})
        return redirect(edit_url)


class GalleryView(ClubSiteView):
    template = 'cms/club_site/gallery.jinja'
    galleries = ClubGallery.objects.none()

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.galleries = self.club.galleries
        return response

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.gallery', kwargs={'club_pk': self.club.pk}), _('Gallery'))
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'galleries': self.galleries.order_by('name', 'slug')})
        return context


class GalleryAddView(GalleryView):
    template = 'cms/club_site/gallery-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = GalleryForm(self.club)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.gallery-add', kwargs={'club_pk': self.club.pk}), _('Add New'))
        ]

    def post(self, request, *args, **kwargs):
        self.form = GalleryForm(self.club, request.POST)

        if self.form.is_valid():
            try:
                gallery = ClubGallery.objects.create(club=self.club, **self.form.cleaned_data)
            except IntegrityError:
                messages.add_message(request, messages.ERROR, _('An error occured.'))
            else:
                edit_url = reverse('club-site.gallery-edit', kwargs={
                    'club_pk': self.club.pk, 'gallery_pk': gallery.pk})
                messages.add_message(request, messages.SUCCESS, _('Gallery was created.'))
                return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class GalleryReorderView(GalleryView):
    template = 'cms/club_site/gallery-reorder.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(self, request, *args, **kwargs)
        context.update({'galleries': self.galleries.order_by('sort')})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        reorder_url = reverse('club-site.gallery-reorder', kwargs={'club_pk': self.club.pk})
        return crumbs + [
            (reorder_url, _('Re-order'))
        ]

    def post(self, request, *args, **kwargs):
        for i, pk in enumerate(request.POST.getlist('pk', [])):
            try:
                gallery = self.galleries.get(pk=pk)
            except ClubGallery.DoesNotExist:
                pass
            else:
                gallery.sort = i
                gallery.save()
        messages.add_message(request, messages.SUCCESS, _('Galleries re-ordered.'))
        return redirect(reverse('club-site.gallery', kwargs={'club_pk': self.club.pk}))


class GalleryDetailsView(GalleryView):
    gallery = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.gallery = self.club.galleries.get(pk=kwargs.get('gallery_pk'))
        except ClubGallery.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Gallery does not exist.'))
            return redirect(reverse('club-site.gallery', kwargs={'club_pk': self.club.pk}))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'gallery': self.gallery})
        return context


class GalleryEditView(GalleryDetailsView):
    template = 'cms/club_site/gallery-edit.jinja'
    edit_form = None
    upload_form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.edit_form = GalleryForm(self.club, gallery=self.gallery)
        self.upload_form = ImageUploadForm()
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'edit_form': self.edit_form, 'upload_form': self.upload_form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('club-site.gallery-edit', kwargs={
            'club_pk': self.club.pk, 'gallery_pk': self.gallery.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('club-site.gallery-edit', kwargs={
            'club_pk': self.club.pk, 'gallery_pk': self.gallery.pk})

        if 'edit' in request.POST:
            self.edit_form = GalleryForm(self.club, request.POST, gallery=self.gallery)

            if self.edit_form.is_valid():
                gallery = ClubGallery.objects.filter(pk=self.gallery.pk)
                try:
                    gallery.update(**self.edit_form.cleaned_data)
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, _('An error occured.'))
                else:
                    messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
                    return redirect(edit_url)
        elif 'upload' in request.POST:
            self.upload_form = ImageUploadForm(request.POST, request.FILES)

            if self.upload_form.is_valid():
                files = request.FILES.getlist('file')
                for image_file in files:
                    ClubGalleryImage.objects.create(gallery=self.gallery, image=image_file)
                messages.add_message(request, messages.SUCCESS, _('Images uploaded.'))
                return redirect('{}?edit-images'.format(edit_url))
        elif 'reorder' in request.POST:
            for i, pk in enumerate(request.POST.getlist('pk', [])):
                try:
                    image = self.gallery.images.get(pk=pk)
                except ClubGalleryImage.DoesNotExist:
                    pass
                else:
                    image.sort = i
                    image.save()
            messages.add_message(request, messages.SUCCESS, _('Images re-ordered.'))
            return redirect('{}?edit-images'.format(edit_url))

        return self.get(request, *args, **kwargs)


class GalleryDeleteView(GalleryDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the gallery: <strong>{name}</strong>?')
        context.update({'confirm_message': message.format(name=self.gallery.name)})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('club-site.gallery-delete',
                             kwargs={'club_pk': self.club.pk, 'gallery_pk': self.gallery.pk})
        return crumbs + [
            (delete_url, _('Delete'))
        ]

    def post(self, request, *args, **kwargs):
        self.gallery.delete()
        messages.add_message(request, messages.SUCCESS, _('Gallery deleted.'))
        return redirect(reverse('club-site.gallery', kwargs={'club_pk': self.club.pk}))


class GalleryImageDetailsView(GalleryDetailsView):
    image = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.image = self.gallery.images.get(pk=kwargs.get('image_pk'))
        except ClubGalleryImage.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Image does not exist.'))
            edit_url = reverse('club-site.gallery-edit',
                               kwargs={'club_pk': self.club.pk, 'gallery_pk': self.gallery.pk})
            return redirect('{}?edit-images'.format(edit_url))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'image': self.image})
        return context


class GalleryImageDeleteView(GalleryImageDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the image?')
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('club-site.gallery-image-delete', kwargs={
            'club_pk': self.club.pk, 'gallery_pk': self.gallery.pk, 'image_pk': self.image.pk})
        edit_url = reverse('club-site.gallery-edit', kwargs={
            'club_pk': self.club.pk, 'gallery_pk': self.gallery.pk})
        return crumbs + [
            ('{}?edit-images'.format(edit_url), _('Edit')),
            (delete_url, _('Delete Image')),
        ]

    def post(self, request, *args, **kwargs):
        self.image.delete()
        messages.add_message(request, messages.SUCCESS, _('Image deleted.'))
        edit_url = reverse('club-site.gallery-edit',
                           kwargs={'club_pk': self.club.pk, 'gallery_pk': self.gallery.pk})
        return redirect('{}?edit-images'.format(edit_url))


class TeamMemberView(ClubSiteView):
    template = 'cms/club_site/team-members.jinja'
    team_members = TeamMember.objects.none()

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.team_members = self.club.team_members
        return response

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.team-members', kwargs={'club_pk': self.club.pk}),
             _('Team Members'))
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'team_members': self.team_members.order_by('sort')})
        return context


class TeamMemberAddView(TeamMemberView):
    template = 'cms/club_site/team-members-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = TeamMemberForm(self.club)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.team-members-add', kwargs={'club_pk': self.club.pk}), _('Add New'))
        ]

    def post(self, request, *args, **kwargs):
        self.form = TeamMemberForm(self.club, request.POST, request.FILES)

        if self.form.is_valid():
            data = self.form.cleaned_data
            team_member = TeamMember.objects.create(club=self.club, **data)
            edit_url = reverse('club-site.team-members-edit', kwargs={
                'club_pk': self.club.pk, 'team_member_pk': team_member.pk})
            messages.add_message(request, messages.SUCCESS, _('Team member was created.'))
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class TeamMemberDetailsView(TeamMemberView):
    team_member = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.team_member = self.club.team_members.get(pk=kwargs.get('team_member_pk'))
        except TeamMember.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Team member does not exist.'))
            return redirect(reverse('club-site.team-members', kwargs={'club_pk': self.club.pk}))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'team_member': self.team_member})
        return context


class TeamMemberEditView(TeamMemberDetailsView):
    template = 'cms/club_site/team-members-edit.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = TeamMemberForm(self.club, team_member=self.team_member)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('club-site.team-members-edit', kwargs={
            'club_pk': self.club.pk, 'team_member_pk': self.team_member.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('club-site.team-members-edit', kwargs={
            'club_pk': self.club.pk, 'team_member_pk': self.team_member.pk})

        self.form = TeamMemberForm(self.club, request.POST, request.FILES,
                                   team_member=self.team_member)

        if self.form.is_valid():
            team_member = TeamMember.objects.filter(pk=self.team_member.pk)
            data = self.form.cleaned_data
            photo = data.pop('photo')
            team_member.update(**data)
            if photo:
                team_member = team_member.first()
                team_member.photo = photo
                team_member.save()
            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class TeamMemberDeleteView(TeamMemberDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the team member: <strong>{}</strong>?')
        message = message.format(self.team_member.name)
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('club-site.team-members-delete', kwargs={
            'club_pk': self.club.pk, 'team_member_pk': self.team_member.pk})
        return crumbs + [
            (delete_url, _('Delete')),
        ]

    def post(self, request, *args, **kwargs):
        self.team_member.delete()
        messages.add_message(request, messages.SUCCESS, _('Team member deleted.'))
        edit_url = reverse('club-site.team-members', kwargs={'club_pk': self.club.pk})
        return redirect(edit_url)


class TeamMemberReorderView(TeamMemberView):
    template = 'cms/club_site/team-members-reorder.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(self, request, *args, **kwargs)
        context.update({'team_members': self.team_members.order_by('sort')})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        reorder_url = reverse('club-site.team-members-reorder', kwargs={'club_pk': self.club.pk})
        return crumbs + [
            (reorder_url, _('Re-order'))
        ]

    def post(self, request, *args, **kwargs):
        for i, pk in enumerate(request.POST.getlist('pk', [])):
            try:
                team_member = self.team_members.get(pk=pk)
            except TeamMember.DoesNotExist:
                pass
            else:
                team_member.sort = i
                team_member.save()
        messages.add_message(request, messages.SUCCESS, _('Team members re-ordered.'))
        return redirect(reverse('club-site.team-members', kwargs={'club_pk': self.club.pk}))


class NewsView(ClubSiteView):
    template = 'cms/club_site/news.jinja'
    news = News.objects.none()

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        news = News.objects.annotate(club_count=Count('clubs'))
        self.news = news.filter(show_on_club_site=True, show_on_corp_site=False,
                                clubs=self.club.pk, club_count=1)
        return response

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.news', kwargs={'club_pk': self.club.pk}),
             _('News'))
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'news': self.news})
        return context


class NewsAddView(NewsView):
    template = 'cms/club_site/news-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = NewsForm()
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.news-add', kwargs={'club_pk': self.club.pk}), _('Add New'))
        ]

    def post(self, request, *args, **kwargs):
        self.form = NewsForm(request.POST, request.FILES)

        if self.form.is_valid():
            data = self.form.cleaned_data
            data.update({
                'show_on_club_site': True,
                'show_on_corp_site': False,
            })
            news_item = News.objects.create(**data)
            news_item.clubs.add(self.club)
            edit_url = reverse('club-site.news-edit', kwargs={
                'club_pk': self.club.pk, 'news_item_pk': news_item.pk})
            messages.add_message(request, messages.SUCCESS, _('News item was created.'))
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class NewsDetailsView(NewsView):
    news_item = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.news_item = self.news.get(pk=kwargs.get('news_item_pk'))
        except News.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('News item does not exist.'))
            return redirect(reverse('club-site.news', kwargs={'club_pk': self.club.pk}))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'news_item': self.news_item})
        return context


class NewsEditView(NewsDetailsView):
    template = 'cms/club_site/news-edit.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = NewsForm(news=self.news_item)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('club-site.news-edit', kwargs={
            'club_pk': self.club.pk, 'news_item_pk': self.news_item.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('club-site.news-edit', kwargs={
            'club_pk': self.club.pk, 'news_item_pk': self.news_item.pk})

        self.form = NewsForm(request.POST, request.FILES,
                             news=self.news_item)

        if self.form.is_valid():
            news_item = News.objects.filter(pk=self.news_item.pk)
            data = self.form.cleaned_data
            data.pop('show_on_club_site')
            data.pop('show_on_corp_site')
            photo = data.pop('photo')
            news_item.update(**data)
            if photo:
                news_item = news_item.first()
                news_item.photo = photo
                news_item.save()
            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class NewsDeleteView(NewsDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the news item: <strong>{}</strong>?')
        message = message.format(self.news_item.headline)
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('club-site.news-delete', kwargs={
            'club_pk': self.club.pk, 'news_item_pk': self.news_item.pk})
        return crumbs + [
            (delete_url, _('Delete')),
        ]

    def post(self, request, *args, **kwargs):
        self.news_item.delete()
        messages.add_message(request, messages.SUCCESS, _('News item deleted.'))
        edit_url = reverse('club-site.news', kwargs={'club_pk': self.club.pk})
        return redirect(edit_url)


class CalendarView(ClubSiteView):
    template = 'cms/club_site/calendar.jinja'
    events = ClubEvent.objects.none()

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        clubevents = self.club.events
        qs = self.request.GET.get('qs', None)
        if qs:
            clubevents = clubevents.filter(name__icontains=qs)
        self.events = clubevents
        return response

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.calendar', kwargs={'club_pk': self.club.pk}), _('Events'))
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'events': self.events, 'now': timezone.now().date()})
        return context


class CalendarAddView(CalendarView):
    template = 'cms/club_site/calendar-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = CalendarForm()
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('club-site.calendar-add', kwargs={'club_pk': self.club.pk}), _('Add New'))
        ]


    def post(self, request, *args, **kwargs):

        self.form = CalendarForm(request.POST, request.FILES)

        if self.form.is_valid():
            data = self.form.cleaned_data
            img_bytes = None

            if data['photo']:img_bytes = data.pop('photo').read()

            # pop recurrence fields to its own dict
            recurrence_data = {'recurrence_set': data.pop('recurrence_set'),
                               'recurrence_repetition_types': data.pop('recurrence_repetition_types'),
                               'recurrence_pattern': data.pop('recurrence_pattern'),
                               'recurrence_every': data.pop('recurrence_every'),
                               'recurrence_until': data.pop('recurrence_until'),
                               'recurrence_repetitions': data.pop('recurrence_repetitions')}

            if recurrence_data['recurrence_set']:
                data['event_series'] = self._generate_recursive_events(recurrence_data, data, img_bytes)['event_series']

            event = ClubEvent.objects.create(club=self.club, **data)

            if img_bytes:
                photo = BytesIO(img_bytes)
                photo.seek(0)
                event.photo.save("image_%s" % event.pk, File(photo))
                event.save()

            edit_url = reverse('club-site.calendar-edit', kwargs={'club_pk': self.club.pk, 'event_pk': event.pk})
            messages.add_message(request, messages.SUCCESS, _('Calendar event was created.'))
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class CalendarDetailsView(CalendarView):
    event = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        try:
            self.event = self.club.events.get(pk=kwargs.get('event_pk'))
        except ClubEvent.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Calendar event does not exist.'))
            return redirect(reverse('club-site.calendar', kwargs={'club_pk': self.club.pk}))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'event': self.event})
        return context

class CalendarEditView(CalendarDetailsView):
    template = 'cms/club_site/calendar-edit.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        if self.event: self.form = CalendarEditForm(event=self.event)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('club-site.calendar-edit', kwargs={
            'club_pk': self.club.pk, 'event_pk': self.event.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('club-site.calendar-edit', kwargs={
            'club_pk': self.club.pk, 'event_pk': self.event.pk})

        self.form = CalendarEditForm(request.POST, request.FILES, event=self.event)

        if self.form.is_valid():
            data = self.form.cleaned_data
            img_bytes = None

            if data['photo']: img_bytes = data.pop('photo').read()

            # pop recurrence fields to its own dict
            recurrence_data = {'recurrence_set': data.pop('recurrence_set'),
                               'recurrence_repetition_types': data.pop('recurrence_repetition_types'),
                               'recurrence_pattern': data.pop('recurrence_pattern'),
                               'recurrence_every': data.pop('recurrence_every'),
                               'recurrence_until': data.pop('recurrence_until'),
                               'recurrence_repetitions': data.pop('recurrence_repetitions'),
                               'edit_options': data.pop('edit_options')}

            if not data['online_registration']:
                data['registration_open_date'] = data['registration_close_date'] = data['custom_question_1'] = \
                    data['custom_question_2'] = data['custom_question_3'] = data['custom_question_4'] = \
                    data['custom_question_5'] = None
                data['registration_open_time'] = DEFAULT_REGISTRATION_OPEN_TIME
                data['registration_close_time'] = DEFAULT_REGISTRATION_CLOSE_TIME
                data['max_guests_per_rsvp'] = 1
                data['max_attendees'] = 0

            event = ClubEvent.objects.filter(pk=self.event.pk)

            if recurrence_data['edit_options'] in (THIS_EVENT_AND_FOLLOWING, ALL_EVENTS):
                if not img_bytes and event.first().photo:
                    img_bytes = event.first().photo.read()
                self._update_recursive_events(event, recurrence_data, data, img_bytes)

            if not img_bytes: data.pop('photo')

            event.update(**data)

            if img_bytes:
                photo = BytesIO(img_bytes)
                photo.seek(0)
                event = event.first()
                event.photo.save("image_%s" % event.pk, File(photo))
                event.save()

            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect(edit_url)
        else:
            for k, v in self.form.errors.items():
                messages.add_message(
                    request, messages.ERROR,
                    _('{}: {}'.format(
                        k, v
                    ))
                )

        return self.get(request, *args, **kwargs)


class CalendarMessageView(CalendarDetailsView):
    template = 'cms/club_site/calendar-message.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = CalendarMessageForm()
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({
            'form': self.form
            })
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        message_url = reverse('club-site.calendar-message', kwargs={
            'club_pk': self.club.pk, 'event_pk': self.event.pk})
        return crumbs + [
            (message_url, _('Messaging'))
        ]

    def post(self, request, *args, **kwargs):


        form = CalendarMessageForm(request.POST)
        if form.is_valid():

            message_url = reverse('club-site.calendar-message', kwargs={
            'club_pk': kwargs['club_pk'], 'event_pk': kwargs['event_pk']})
            event = ClubEvent.objects.get(pk=kwargs['event_pk'])
            data = form.cleaned_data

            '''
            Format is:

            {'from_name': 'ClubLink',
            'message': 'asdfsadf',
            'reply_to': 'no-reply@clublink.ca',
            'subject': 'asdfsadf'}

            '''

            count = event.rsvps.count()

            if count:

                email = EmailMessage(
                    subject=data['subject'],
                    body=data['message'],
                    from_email='{} <{}>'.format(
                        data['from_name'],
                        data['reply_to']
                    ),
                    # SES somehow requires a to
                    to=['no-reply@clublink.ca'],
                    reply_to=[data['reply_to']],
                    bcc=list(event.rsvps.values_list('user__email', flat=True))
                )
                email.send()

                messages.add_message(
                    request, messages.SUCCESS, _('Message successfully sent to {} members.'.format(
                        count
                )))

                if settings.DEBUG:
                    messages.add_message(
                        request, messages.INFO, _('Since this is a testing environment, you should check Mailtrap'))

                    # Easter eggs
                    # if request.user.last_name == 'Bones' or request.user.last_name == 'Burnnett':]
                    #     messages.add_message(
                    #         request, request.INFO, ('Hi Mister {} - from Kevin'.format(
                    #             request.user.last_name
                    #         ))
                    #     )

            else:
                messages.add_message(
                    request, messages.INFO, _('This event has no RSVPs')
                )
            return redirect(message_url)

        return self.get(request, *args, **kwargs)

        # edit_url = reverse(
        #     'club-site.calendar-edit',
        #     kwargs={
        #         'club_pk': self.club.pk,
        #         'event_pk': self.event.pk
        #     })

        # self.form = CalendarForm(request.POST, request.FILES, event=self.event)

        # if self.form.is_valid():
        #     event = ClubEvent.objects.filter(pk=self.event.pk)
        #     data = self.form.cleaned_data
        #     photo = data.pop('photo')
        #     event.update(**data)
        #     if photo:
        #         event = event.first()
        #         event.photo = photo
        #         event.save()
        #     messages.add_message(request, messages.SUCCESS,
        #                          _('Changes saved.'))
        #     return redirect(edit_url)

        # return self.get(request, *args, **kwargs)


class CalendarEventRSVPDeleteView(FormView):

    def post(self, request, *args, **kwargs):

        try:
            obj = ClubEventRSVP.objects.get(pk=kwargs['rsvp_pk'])
            messages.add_message(request, messages.SUCCESS, _('{} {} - RSVP successfully deleted.'.format(
                obj.user.first_name, obj.user.last_name
            )))
            obj.delete()
            send_cancel_rsvp_email_to_member(rsvp)
            send_cancel_rsvp_email_to_admin(rsvp)
        except Exception as e:
            messages.add_message(request, messages.ERROR, str(e))
        return redirect('club-site.calendar-register', event_pk=kwargs['event_pk'], club_pk=kwargs['club_pk'])



class CalendarRegisterView(CalendarDetailsView):
    template = 'cms/club_site/calendar-register.jinja'

    def pre_dispatch(self, request, *args, **kwargs):
        event = ClubEvent.objects.get(pk=kwargs['event_pk'])

        if not event.type == 0:
            messages.add_message(request, messages.ERROR, _('Online registration is only available for member events - not notices or outside events.'))
            return redirect('club-site.calendar', club_pk=kwargs['club_pk'])
        else:
            response = super().pre_dispatch(request, *args, **kwargs)
            return response

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        register_url = reverse('club-site.calendar-register', kwargs={
            'club_pk': self.club.pk, 'event_pk': self.event.pk})
        return crumbs + [
            (register_url, _('Register')),
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        q = request.GET.get('q', None)
        context['query'] = []
        if q:
            query = User.objects.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(membership_number__icontains=q) |
                Q(option_club__name__icontains=q)
            )
            context['query'] = query
        context['q'] = q
        context['registrants'] = User.objects.filter(id__in=context['event'].rsvps.values('user'))
        context['rsvp_form'] = RSVPForm(self.event, request)
        context['parent_rsvps'] = context['event'].rsvps.exclude(parent__isnull=False).select_related('user').prefetch_related('children')
        return context

    def post(self, request, *args, **kwargs):
        event = ClubEvent.objects.get(pk=kwargs['event_pk'])

        if not event.online_registration:
            messages.add_message(request, messages.ERROR, _('Online registration is disabled for this event.'))
            return redirect('club-site.calendar', club_pk=kwargs['club_pk'])

        registrant = request.POST.get('registrant', None)
        if registrant:
            try:
                user = User.objects.get(id=registrant)
                adults=request.POST.get('adults', 0)
                children=request.POST.get('children', 0)
                custom_answer_1=request.POST.get('custom_question_1', '')
                custom_answer_2=request.POST.get('custom_question_2', '')
                custom_answer_3=request.POST.get('custom_question_3', '')
                custom_answer_4=request.POST.get('custom_question_4', '')
                custom_answer_5=request.POST.get('custom_question_5', '')

                rsvp = event.rsvp(
                    user=user,
                    number_of_adults=int(adults),
                    number_of_children=int(children),
                    custom_answer_1=custom_answer_1,
                    custom_answer_2=custom_answer_2,
                    custom_answer_3=custom_answer_3,
                    custom_answer_4=custom_answer_4,
                    custom_answer_5=custom_answer_5
                )
                messages.add_message(request, messages.SUCCESS, _('Event registration successful.'))
                send_rsvp_email_to_member(rsvp)
                send_rsvp_email_to_admin(rsvp)
                return redirect('club-site.calendar-register', event_pk=event.pk, club_pk=event.club.pk)
            except Exception as e:
                logging.exception(e)
                messages.add_message(request, messages.ERROR, str(e))
                return redirect('club-site.calendar-register', event_pk=event.pk, club_pk=event.club.pk)
        else:
            messages.add_message(request, messages.ERROR, _('No registrant info provided.'))
            return redirect('club-site.calendar-register', event_pk=event.pk, club_pk=event.club.pk)


class RegistrationEmailView(CalendarDetailsView):
    template = 'cms/club_site/registration-email.jinja'


class CalendarBulkDeleteView(CalendarDetailsView):
    template = 'cms/club_site/calendar-delete.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = CalendarBulkDeleteForm(event=self.event)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('club-site.calendar-delete', kwargs={
            'club_pk': self.club.pk, 'event_pk': self.event.pk})
        return crumbs + [
            (delete_url, _('Delete')),
        ]

    def post(self, request, *args, **kwargs):
        self.form = CalendarBulkDeleteForm(request.POST, request.FILES, event=self.event)

        if self.form.is_valid():
            data = self.form.cleaned_data

            if data['delete_options'] == THIS_EVENT:
                self.event.delete()

            if data['delete_options'] in (THIS_EVENT_AND_FOLLOWING, ALL_EVENTS):
                try:
                    self.event_series = EventSeries.objects.get(events=self.event)
                    if data['delete_options'] == THIS_EVENT_AND_FOLLOWING:
                        self.event_series.events.filter(start_date__gt=self.event.start_date).delete()
                        self.event.delete()

                    if data['delete_options'] == ALL_EVENTS:
                        self.event_series.events.all().delete()

                    messages.add_message(request, messages.SUCCESS, _('Calendar event deleted.'))

                except EventSeries.DoesNotExist:
                    messages.add_message(request, messages.WARNING, _('This Event is not part of Series.'))

            edit_url = reverse('club-site.calendar', kwargs={'club_pk': self.club.pk})
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class CalendarExportView(CalendarDetailsView):
    def get(self, request, *args, **kwargs):
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, quotechar='"')

        writer.writerow(
            ['Club', self.event.club.name]
        )

        writer.writerow(
            ['Event Name', self.event.name]
        )

        writer.writerow(
            ['Event ID', self.event.id]
        )

        writer.writerow(['Total Participants', self.event.total_guests])

        writer.writerow(['Total Allowed', self.event.max_attendees])
        writer.writerow([])

        header = [
            'Registration Date',
            'Confirmation Number',
            'Host Confirmation Number',
            'Host Name',
            'Number of Adults',
            'Is a member?',
            'Name',
            'Email',
            'Phone',
            'Notes'
        ]

        if self.event.custom_question_1:
            header.append(self.event.custom_question_1)

        if self.event.custom_question_2:
            header.append(self.event.custom_question_2)

        if self.event.custom_question_3:
            header.append(self.event.custom_question_3)

        if self.event.custom_question_4:
            header.append(self.event.custom_question_4)

        if self.event.custom_question_5:
            header.append(self.event.custom_question_5)

        writer.writerow(header)

        # Only start with the hosts... members who are invited get their own RSVP, so this confuses things...
        # We couldn't refactor this without a massive overhual, so we had to leave it.
        for r in self.event.rsvps.filter(parent__isnull=True).prefetch_related():
            row = [
                timezone.localtime(r.created).strftime('%Y-%m-%d %H:%M:%S'),
                r.confirmation_number,
                r.parent.confirmation_number if r.parent else r.confirmation_number,
                r.parent.user.get_full_name() if r.parent else r.user.get_full_name(),
                r.number_of_adults,
                'Yes',
                r.user.get_full_name(),
                r.user.email,
                r.user.profile.mailing_address.phone if r.user.profile.mailing_address else '',
            ]

            if self.event.custom_question_1:
                row.append(r.custom_answer_1)

            if self.event.custom_question_2:
                row.append(r.custom_answer_2)

            if self.event.custom_question_3:
                row.append(r.custom_answer_3)

            if self.event.custom_question_4:
                row.append(r.custom_answer_4)

            if self.event.custom_question_5:
                row.append(r.custom_answer_5)

            if r.notes:
                row.append(r.notes)

            writer.writerow(row)

            # Members who are the host's guests
            for child in r.children.all():
                row = [
                    timezone.localtime(child.created).strftime('%Y-%m-%d %H:%M:%S'),
                    child.confirmation_number,
                    child.parent.confirmation_number if child.parent else child.confirmation_number,
                    child.parent.user.get_full_name() if child.parent else child.user.get_full_name(),
                    '',
                    'Yes',
                    child.user.get_full_name(),
                    child.user.email,
                    child.user.profile.mailing_address.phone if child.user.profile.mailing_address else '',
                ]

                if self.event.custom_question_1:
                    row.append(child.custom_answer_1)

                if self.event.custom_question_2:
                    row.append(child.custom_answer_2)

                if self.event.custom_question_3:
                    row.append(child.custom_answer_3)

                if self.event.custom_question_4:
                    row.append(child.custom_answer_4)

                if self.event.custom_question_5:
                    row.append(child.custom_answer_5)

                writer.writerow(row)

            # Non-members who are the host's guests
            if r.guest_data:

                for g in r.guest_data:
         
                    row = [
                        timezone.localtime(r.created).strftime('%Y-%m-%d %H:%M:%S'),
                        '',
                        r.confirmation_number,
                        r.parent.user.get_full_name() if r.parent else r.user.get_full_name(),
                        '',
                        'No',
                        g.get('name', None),
                        '',
                        '',
                        ''
                    ]
                    writer.writerow(row)

            # Add a blank line after
            writer.writerow([])

        filename = '{}-guest-list-{}-({})-{}.csv'.format(
            slugify(self.event.club.name),
            slugify(self.event.name), self.event.id, self.event.start_date.strftime('%Y-%m-%d'))
        response = HttpResponse(content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        response.write(buffer.getvalue())
        buffer.close()

        return response
