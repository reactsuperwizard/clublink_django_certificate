import calendar
import logging
import json

logger = logging.getLogger(__name__)

import string
from datetime import date
from smtplib import SMTPRecipientsRefused
from urllib.parse import quote_plus, parse_qs, urlparse

from django.conf import settings

import user_agents
from clublink.base.clients.dynamics import DynamicsClient
from clublink.base.forms import (GolfTournamentForm, MeetingsForm,
                                 MembershipForm, WeddingsForm)
from clublink.base.messages import FORM_SUBMITTED_MESSAGE
from clublink.clubs.forms import (AddressForm, PreferenceForm, ProfileForm,
                                  RSVPForm, SubscriptionsForm, UserForm)
from clublink.clubs.models import Club, ClubEvent, ClubEventRSVP
from clublink.clubs.utils import (send_cancel_rsvp_email_to_admin,
                                  send_cancel_rsvp_email_to_member,
                                  send_rsvp_email_to_admin,
                                  send_rsvp_email_to_member)
from clublink.cms.models import ClubGallery, ClubPage
from clublink.corp.models import News
from clublink.users.models import Address, Profile, User
from dateutil.relativedelta import relativedelta
from django import views
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.urls import resolve
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, select_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.defaults import page_not_found, permission_denied
from pymssql import OperationalError


def handler500(request):
    return render(request, 'clubs/errors/500.jinja', status=500,context = {'request': request}
    )


def handler404(request, exception=None):
    return page_not_found(request, exception, template_name='clubs/errors/404.jinja')


def handler403(request, exception=None):
    return permission_denied(request, exception, template_name='clubs/errors/403.jinja')


def logout(request):
    auth_logout(request)
    return redirect(reverse('home'))


def redirect_home(request):
    return redirect(reverse('home'), permanent=True)


class GenericPageView(views.View):
    template = 'clubs/generic/default.jinja'
    extra_context = {}
    full_path = None
    page = None
    menu = ()

    def generate_menu(self, request, *args, **kwargs):
        menu = []

        parent = self.page if self.page.list_in_child_page_nav else self.page.parent

        if parent:

            if parent.list_in_child_page_nav:
                menu.append((
                    parent.url,
                    parent.name_in_child_page_nav or parent.name,
                    parent.target,
                ))

            for page in parent.children.distinct().order_by('sort'):
                if page.is_visible(request):
                    menu.append((
                        page.url,
                        page.name,
                        page.target,
                    ))

        self.menu = menu

    def process_request(self, request, *args, **kwargs):

        full_path = kwargs.get('full_path', request.path.strip('/'))
        self.full_path = full_path

        full_path = full_path.split('~~~')[0]

        # To handle for the CalendarREgister

        # print(self.full_path)
        # print(request.club)

        clubpages = ClubPage.objects.filter(club=request.club)
        # print(clubpages.count())

        filtered = clubpages.filter(full_path=self.full_path)
        # print(filtered.count())

        page = ClubPage.objects.get(full_path=full_path, club=request.club)
        # print(page.id)

        self.page = get_object_or_404(ClubPage, club=request.club, full_path=full_path)

        visibility = self.page.visibility
        if visibility == ClubPage.NOBODY_VISIBILITY:
            raise Http404
        elif visibility == ClubPage.NON_MEMBERS_ONLY_VISIBILITY and request.member_portal:
            raise Http404
        elif visibility == ClubPage.MEMBERS_ONLY_VISIBILITY and not request.member_portal and not request.user.is_superuser:
            if request.user.is_authenticated:
                raise PermissionDenied
            else:
                messages.add_message(request, messages.WARNING,
                                     _('You must be signed in to view this page.'))
                login_url = '{}?next={}'.format(reverse('login'), quote_plus(request.path))
                return redirect(login_url)

        if self.page.should_redirect:
            if self.page.internal_redirect:
                return redirect(self.page.internal_redirect.url)
            elif self.page.external_redirect:
                return redirect(self.page.external_redirect)
        try:
            alias_club = Club.objects.get(pk=request.GET.get('filter_club'), site=request.site)
        except Club.DoesNotExist:
            logger.debug('No club exists')
        else:
            try:
                alias_page = alias_club.pages.get(full_path=self.full_path, site=request.site)
            except ClubPage.DoesNotExist:
                pass
            else:
                self.page.alias = alias_page

    def before_render(self, request, *args, **kwargs):
        pass

    def get_extra_context(self, request, *args, **kwargs):
        # import pdb; pdb.set_trace();
        extra_context = self.extra_context
        extra_context.update({
            'page': self.page,
            'menu': self.menu,
            'full_path': '/{}/'.format(self.full_path) if self.full_path else '/'
        })
        return extra_context

    def get(self, request, *args, **kwargs):
        self.generate_menu(request, *args, **kwargs)
        context = self.get_extra_context(request, *args, **kwargs)
        self.before_render(request, *args, **kwargs)
        return render(request, self.template, context)

    def dispatch(self, request, *args, **kwargs):
        response = self.process_request(request, *args, **kwargs)
        if response:
            return response

        return super().dispatch(request, *args, **kwargs)


class HomeView(GenericPageView):
    template = 'clubs/home.jinja'

    def get_extra_context(self, request, *args, **kwargs):

        extra_context = super().get_extra_context(request, *args, **kwargs)

        '''
        This handles for the extra logic that is needed to do give different buckets somewhat dynamically.  Brendan knows that the eventual task will be to provide access to a dynamic bucket list.
        '''

        spoofed_user_id = request.GET.get('spoof', request.session.get('spoofed_user_id'))

        if spoofed_user_id:
            user = User.objects.get(id=spoofed_user_id)
        elif request.user.is_authenticated:
            user = request.user
        else:
            user = None

        subdomain = request.META['HTTP_HOST'].split('.')[0]

        if user and user.home_club and (user.home_club == request.club):

            # Similar to get_template_name in the real TemplateView, we return the first one that is found https://docs.djangoproject.com/en/1.11/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin.get_template_names

            bucket_template_name = select_template(
                    [
                        'clubs/members/{}/home-buckets.jinja'.format(request.club.slug),
                        'clubs/members/base-home-buckets.jinja',
                        'clubs/includes/{}/home-buckets.jinja'.format(request.club.slug),
                        'clubs/includes/home-buckets.jinja'
                    ]
                ).name

        else:
            bucket_template_name = select_template(
                    [
                        'clubs/includes/{}/home-buckets.jinja'.format(request.club.slug),
                        'clubs/includes/home-buckets.jinja'
                    ]
                ).name

        extra_context['bucket_template_name'] = bucket_template_name
        extra_context['subdomain'] = subdomain
        return extra_context

class AboutView(GenericPageView):
    template = 'clubs/about/about.jinja'


class GalleryView(GenericPageView):
    template = 'clubs/about/gallery.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        slug = kwargs.get('slug')

        if slug:
            try:
                gallery = request.club.galleries.get(slug=slug)
            except ClubGallery.DoesNotExist:
                raise Http404()
        else:
            gallery = request.club.galleries.first()

        extra_context.update({
            'slug': slug,
            'gallery': gallery,
            'view_name': resolve(request.path).url_name,
        })

        return extra_context


class TeamView(GenericPageView):
    template = 'clubs/about/team.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'team_members': request.club.team_members.all(),
        })
        return extra_context


class GolfShopView(GenericPageView):
    template = 'clubs/about/base.jinja'


class PoliciesView(GenericPageView):
    template = 'clubs/about/base.jinja'


class CalendarView(GenericPageView):
    template = 'clubs/my-club/calendar.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        cal = calendar.Calendar(firstweekday=6)
        today = timezone.localtime(timezone.now())

        try:
            club = Club.objects.get(pk=request.GET.get('filter_club'))
        except Club.DoesNotExist:
            club = request.club

        try:
            selected_date = date(*[int(i) for i in request.GET.get('date').split('-')])
        except (ValueError, TypeError, AttributeError):
            selected_date = today

        end_date = selected_date + relativedelta(days=7)

        try:
            year = int(request.GET.get('calendar_year'))
        except (ValueError, TypeError):
            year = int(selected_date.strftime('%Y'))

        try:
            month = int(request.GET.get('calendar_month'))
        except (ValueError, TypeError):
            month = int(selected_date.strftime('%-m'))

        first_date = date(year, month, 1)

        member_events = ClubEvent.objects.filter(
            club=club, start_date__gte=first_date,
            start_date__lt=first_date + relativedelta(months=1))

        dates = {}
        for event in member_events:
            key = event.start_date.strftime('%Y%m%d')

            if key not in dates:
                dates[key] = {
                    'member_events': False,
                    'notices': False,
                    'outside_events': False,
                }

            if event.type == ClubEvent.MEMBER_EVENT:
                dates[key]['member_events'] = True
            elif event.type == ClubEvent.NOTICE:
                dates[key]['notices'] = True
            elif event.type == ClubEvent.OUTSIDE_EVENT:
                dates[key]['outside_events'] = True

        event_calendar = []
        for week in cal.monthdatescalendar(year, month):
            event_week = []
            for day in week:
                if day < first_date or day >= first_date + relativedelta(months=1):
                    event_week.append(None)
                else:
                    markers = dates.get(day.strftime('%Y%m%d'), {})
                    event_week.append({
                        'day': day.strftime('%-d'),
                        'month': day.strftime('%-m'),
                        'year': day.strftime('%Y'),
                        **markers,
                    })
            event_calendar.append(event_week)

        week_events = ClubEvent.objects.filter(
            club=club, start_date__gte=selected_date, start_date__lte=end_date)

        events = []
        day_events = []
        for event in week_events:
            if day_events and day_events[0].start_date != event.start_date:
                events.append(day_events)
                day_events = []
            day_events.append(event)
        if day_events:
            events.append(day_events)

        extra_context.update({
            'current_club': club,
            'calendar_month': first_date,
            'next_calendar_month': first_date + relativedelta(months=1),
            'previous_calendar_month': first_date - relativedelta(months=1),
            'calendar': event_calendar,
            'selected_date': selected_date,
            'end_date': end_date,
            'previous_week_date': selected_date - relativedelta(days=7),
            'next_week_date': end_date + relativedelta(days=1),
            'events': events,
        })

        return extra_context


class CalendarItemView(GenericPageView):
    template = 'clubs/my-club/calendar-item.jinja'
    event = None
    rsvp_form = None

    def process_request(self, request, *args, **kwargs):
        response = super().process_request(request, *args, **kwargs)
        self.event = get_object_or_404(ClubEvent, pk=kwargs.get('pk'))
        return response

    def get_extra_context(self, request, *args, **kwargs):
        if not self.rsvp_form:
            self.rsvp_form = RSVPForm(self.event, request)

        mode = request.GET.get('mode', None)
        editmode = True if mode == 'edit' and request.user.is_staff else False

        user = None
        behalf = None

        if editmode:
            behalf = request.GET.get('behalf', None)
            if behalf:
                user_qs = User.objects.filter(id=int(behalf))
                if user_qs.exists():
                    user = user_qs.first()
                print('BEHALF MODE')
                print(user.id)

        registered = self.event.rsvps.filter(user=user if user else request.member)
        if registered.exists():
            assert(registered.count() == 1)
            registered = registered.first()
            initial = registered.get_initial_form_data(editmode, behalf)
            self.rsvp_form.initial = initial

            if behalf or not editmode:
                # Inject the already-selected user id and display name
                attrs = registered.get_data_attrs()
                for k, v in attrs.items():
                    self.rsvp_form.fields[k].widget.attrs.update(v)
        if editmode and request.user.is_staff and not behalf:
            self.rsvp_form.fields['host_name'].widget.attrs.update({
                'disabled':
                False
            })
        else:
            # We put it here so that the JS has a consistent way of bootstrapping the selectize dropdowns from data attributes, like the other ones.

            pre_populated = user if user else request.member

            self.rsvp_form.fields['host_name'].widget.attrs.update({
                    'data-value': pre_populated.id,
                    'data-displayname':
                    '{} {} ({})'.format(pre_populated.first_name,
                                        pre_populated.last_name,
                                        pre_populated.option_club_name
                    )
            })

        return_url = '{}?date={}'.format(reverse('my-club.calendar'),
                                         self.event.start_date.strftime('%Y-%-m-%-d'))

        if self.event.club != request.club:
            return_url += '&filter_club={}'.format(self.event.club.pk)

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'event': self.event,
            'return_url': return_url,
            'rsvp_form': self.rsvp_form,
            'editmode': editmode,
            'behalf': behalf
        })
        return extra_context

    def post(self, request, *args, **kwargs):

        # TODO - this really needs to be refactored now that we have some semblance of a CRUD app

        if 'rsvp' in request.POST:
            self.rsvp_form = RSVPForm(self.event, request=request, data=request.POST)

            if self.rsvp_form.is_valid():

                # Refactor this...
                urlstring = request.META['HTTP_REFERER']
                qs = urlparse(urlstring).query
                behalf = parse_qs(qs).get('behalf', None)
                if behalf:
                    behalf = behalf[0]

                try:
                    '''
                    We first check if the user is an admin, and if so, they are allowed to register for someone else.
                    '''
                    host_user = request.member

                    if request.user.is_staff:
                        host_name = self.rsvp_form.cleaned_data['host_name']

                        if host_name:
                            host_id = int(host_name)
                            host_user = User.objects.get(id=host_id)

                        else:
                            '''
                            On a personal fill of the form, hostname does not get populated, 
                            so we have to just get the user from the request
                            '''
                            host_user = request.member or request.user

                    else:
                        host_user = request.member

                    # Register for yourself first
                    rsvp = self.event.rsvp(user=host_user, **self.rsvp_form.cleaned_data)

                except ClubEvent.AlreadyAttending:

                    host_user = request.member
                    if behalf:
                        host_user = User.objects.get(id=int(behalf))
                    registered = self.event.rsvps.filter(user=host_user)

                    if registered.exists():
                        registered = registered.first()
                        rsvp = registered
                    else:
                        raise Exception('Unepxected exception: 408')

                    cd = self.rsvp_form.cleaned_data
                    adults = self.rsvp_form.cleaned_data['number_of_adults']

                    net_data = {}
                    for x in range(2, adults+1):
                        keys = [
                            'guest_{}_type'.format(x)
                        ]

                        for k in keys:
                            net_data[k] = cd[k]

                        if net_data['guest_{}_type'.format(x)] == 'Member':
                            key = 'guest_{}_dropdown'.format(x)
                            net_data[key] = cd[key].first().id
                        else:
                            key = 'guest_{}_input'.format(x)
                            net_data[key] = cd[key]

                    notes = cd.get('notes', '')
                    net_data['notes'] = notes
                    net_data['number_of_adults'] = adults

                    # Check the diff
                    existing = registered.get_initial_form_data()

                    diff = {}


                    for k, v in net_data.items():
                        if k in existing and existing[k] != v:
                            diff[k] = v
                        elif k not in existing:
                            diff[k] = v

                    members = []
                    guests = []
                    cancel_members = []

                    if not diff:
                        messages.add_message(request, messages.ERROR,
                                         _('No differences detected with existing RSVP.'))

                    else:
                        print('\n')
                        print(diff)
                        print('\n')
                        '''
                        If there is any difference at all, we have to update that particular value and resend the info to user and admin.
                        '''

                        for x in range(2, adults+1):
                            guestType = cd.get('guest_{}_type'.format(x), None)

                            if guestType == 'Member':

                                guestMember = list(cd.get('guest_{}_dropdown'.format(x), []))
                                members.extend(
                                    guestMember
                                )

                            elif guestType == 'Guest':

                                guestName = cd.get('guest_{}_input'.format(x), '')
                                guests.append(
                                    {'name': guestName}
                                )

                                '''
                                Since this type was changed to Guest (from Member) 
                                we need to cancel the existing member
                                '''
                                this_type = existing.get('guest_{}_type'.format(x), None)
                                if this_type == 'Member':
                                    cancel_members.append(
                                        existing['guest_{}_dropdown'.format(x)]
                                        )

                            else:
                                logger.exception(
                                    'Unknown guest type on RSVPForm. No guest type.',
                                    extra={
                                        'guestType': guestType
                                    }
                                )

                        rsvp.guest_data = guests
                        rsvp.number_of_adults = adults
                        rsvp.notes = notes
                        rsvp.save()

                        # Print this success message to the screen
                        messages.add_message(
                            request,
                            messages.SUCCESS,
                            _('RSVP has been edited. A revised confirmation email has been sent to you and your guests.')
                        )

                    if members:

                        # Then, try the others...
                        for member in members:
                            if settings.DEBUG:
                                import time
                                time.sleep(1)

                            try:
                                member_rsvp = self.event.rsvp(
                                    user=member, parent=rsvp)

                            except ClubEvent.AlreadyAttending:
                                messages.add_message(
                                    request, messages.ERROR,
                                    _('{} {} is already attending this event. An email will not be resent.'.
                                      format(member.first_name,
                                             member.last_name)))

                            except Exception as e:
                                messages.add_message(request, messages.ERROR,
                                                     e.message)

                            else:
                                messages.add_message(
                                    request, messages.SUCCESS,
                                    _('{} {} has been registered.'.format(
                                        member.first_name, member.last_name)))

                                try:
                                    send_rsvp_email_to_member(
                                        member_rsvp, host_user)
                                    send_rsvp_email_to_admin(
                                        member_rsvp, host_user)

                                except SMTPRecipientsRefused as e:
                                    logging.error(e)

                        # Here, we need to cancel all members who are no longer registered
                        old_member_guests = list(rsvp.children.values_list('user', flat=True))
                        member_ids = [m.id for m in members]
                        cancel_members = [
                            m for m in old_member_guests if m not in member_ids
                        ]

                    if cancel_members:

                        cancel_rsvps = ClubEventRSVP.objects.filter(event=self.event, user__id__in=cancel_members)

                        for c in cancel_rsvps:

                            # Cancel email to members
                            try:
                                send_cancel_rsvp_email_to_member(
                                    c,
                                    host_user
                                )

                                messages.add_message(request, messages.SUCCESS, _('Registration for {} {} has been cancelled.'.format(
                                    c.user.first_name,
                                    c.user.last_name
                                )))

                            except SMTPRecipientsRefused as e:
                                logging.error(e)


                            if settings.DEBUG:
                                import time
                                time.sleep(1)
                                print('admin', c)

                            # Cancel email to admins
                            try:
                                send_cancel_rsvp_email_to_admin(
                                    c,
                                    host_user
                                )

                            except SMTPRecipientsRefused as e:
                                logging.error(e)

                        # Now delete
                        for c in cancel_rsvps:
                            c.delete()


                    ## Send the host user's last becuase the lookups are required
                    try:
                        if settings.DEBUG:
                            import time
                            time.sleep(1)
                        send_rsvp_email_to_member(rsvp)
                        if settings.DEBUG:
                            import time
                            time.sleep(1)
                        send_rsvp_email_to_admin(rsvp)
                    except SMTPRecipientsRefused as e:
                        logger.exception(e)

                    return redirect(request.META['HTTP_REFERER'])

                    # return redirect('{}#rsvp'.format(request.path))

                except ClubEvent.InvalidGuestCount:
                    messages.add_message(request, messages.ERROR,
                                         _('Invalid guest count.'))
                except ClubEvent.LimitExceeded:
                    messages.add_message(request, messages.ERROR,
                                         _('There are not enough open spaces.'))

                else:

                    messages.add_message(request, messages.SUCCESS, _('{} {} has been registered.'.format(
                        host_user.first_name, host_user.last_name
                    )))

                    '''
                    We know the number of adults that were selected on the form.
                    We will use that to loop through and capture the guest data, 
                    and parse according to whether the guest is a member or a non-member.
                    '''

                    adults = self.rsvp_form.cleaned_data['number_of_adults']
                    members = []
                    guests = []

                    cd = self.rsvp_form.cleaned_data

                    notes = cd.get('notes', '')

                    for x in range(2, adults+1):

                        guestType = cd.get('guest_{}_type'.format(x), None)

                        if guestType == 'Member':

                            guestMember = list(cd.get('guest_{}_dropdown'.format(x), []))
                            members.extend(
                                guestMember
                            )

                        elif guestType == 'Guest':

                            guestName = cd.get('guest_{}_input'.format(x), '')
                            guests.append(
                                {'name': guestName}
                            )

                            # Print this success message to the screen
                            messages.add_message(
                                request,
                                messages.SUCCESS,
                                _('{} has been registered.'.format(
                                    guestName
                                ))
                            )

                        else:
                            logger.exception(
                                'Unknown guest type on RSVPForm',
                                extra={
                                    'guestType': guestType
                                }
                            )

                    rsvp.guest_data = guests
                    rsvp.number_of_adults = 1 + len(members) + len(guests)
                    rsvp.notes = notes
                    rsvp.save()

                    # Then, try the others...
                    for member in members:
                        if settings.DEBUG:
                            import time
                            time.sleep(1)

                        try:
                            member_rsvp = self.event.rsvp(user=member, parent=rsvp)

                        except ClubEvent.AlreadyAttending:
                            messages.add_message(
                                request,
                                messages.ERROR,
                                _('{} {} is already attending this event'.format(member.first_name, member.last_name))
                                )

                        except Exception as e:
                            messages.add_message(
                                request,
                                messages.ERROR,
                                e.message
                            )

                        else:
                            messages.add_message(request, messages.SUCCESS, _('{} {} has been registered.'.format(
                                member.first_name,
                                member.last_name
                            )))

                            try:
                                if settings.DEBUG:
                                    import time
                                    time.sleep(1)
                                send_rsvp_email_to_member(member_rsvp, host_user)

                                if settings.DEBUG:
                                    import time
                                    time.sleep(1)
                                send_rsvp_email_to_admin(member_rsvp, host_user)

                            except SMTPRecipientsRefused as e:
                                logging.error(e)


                    ## Send the host user's last becuase the lookups are required
                    try:
                        if settings.DEBUG:
                            import time
                            time.sleep(1)
                        send_rsvp_email_to_member(rsvp)
                        if settings.DEBUG:
                            import time
                            time.sleep(1)
                        send_rsvp_email_to_admin(rsvp)
                    except SMTPRecipientsRefused as e:
                        logger.exception(e)

                    if request.user.is_staff:
                        return redirect(request.path+'?mode=edit')
                    else:
                        return redirect('{}#rsvp'.format(request.path))


            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    self.rsvp_form.errors
                )

        elif 'cancel' in request.POST:

            behalf = None

            if request.user.is_staff:

                # Refactor this...
                urlstring = request.META['HTTP_REFERER']
                qs = urlparse(urlstring).query
                behalf = parse_qs(qs).get('behalf', None)
                if behalf:
                    behalf = behalf[0]

            if behalf:
                try:
                    behalf_user = User.objects.get(id=int(behalf))
                except:
                    behalf_user = None

            host_user = behalf_user if behalf else request.member

            rsvp = self.event.rsvps.get(user=host_user)

            children = rsvp.children.all()

            # MEMBER CANCEL FOR CHILDREN
            for c in children:

                if settings.DEBUG:
                    import time
                    time.sleep(1)
                    print('user', c)

                try:
                    send_cancel_rsvp_email_to_member(
                        c,
                        host_user
                    )

                    messages.add_message(request, messages.SUCCESS, _('Registration for {} {} has been cancelled.'.format(
                        c.user.first_name,
                        c.user.last_name
                    )))

                except SMTPRecipientsRefused as e:
                    logging.error(e)

            # ADMIN CANCEL FOR CHILDREN
            for c in children:

                if settings.DEBUG:
                    import time
                    time.sleep(1)
                    print('admin', c)

                try:
                    send_cancel_rsvp_email_to_admin(
                        c,
                        host_user
                    )

                except SMTPRecipientsRefused as e:
                    logging.error(e)

            # Now delete
            for c in children:
                c.delete()
            rsvp.delete()

            messages.add_message(request, messages.SUCCESS,
                                 _('Your registration has been cancelled.'))

            try:
                if settings.DEBUG:
                    import time
                    time.sleep(1)
                send_cancel_rsvp_email_to_member(rsvp, host_user)
            except SMTPRecipientsRefused as e:
                logging.error(e)

            try:
                if settings.DEBUG:
                    import time
                    time.sleep(1)
                send_cancel_rsvp_email_to_admin(rsvp, host_user)
            except SMTPRecipientsRefused as e:
                logging.error(e)


            return redirect(request.path + '?mode=edit')

        return self.get(request, *args, **kwargs)


class RosterView(GenericPageView):
    template = 'clubs/my-club/roster.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context['letters'] = list(string.ascii_uppercase)

        filter_letter = request.GET.get('letter', 'A').upper()
        if filter_letter not in extra_context['letters']:
            filter_letter = 'A'

        extra_context['filter_letter'] = filter_letter

        users = User.objects.filter(last_name__istartswith=filter_letter,
                                    profile__show_in_roster=True,
                                    status='A').filter(Q(option_club=request.club ) |
                                                       (Q( home_club=request.club) &
                                                        Q(option_club=None ))).select_related('profile')

        extra_context['members'] = users.order_by('last_name')

        return extra_context


class MembershipView(GenericPageView):
    template = 'clubs/membership/membership.jinja'


class MembershipInquiryView(GenericPageView):
    form = None
    template = 'clubs/membership/inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = MembershipForm(request=request, data=request.POST)

        if self.form.is_valid():
            self.form.send_email(request.club)
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)
            return redirect(reverse('membership.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        if not self.form:
            self.form = MembershipForm(request=request)

        extra_context = super().get_extra_context(request)
        extra_context.update({
            'form': self.form,
        })
        return extra_context


class GuestFeesView(GenericPageView):
    template = 'clubs/membership/guest-fees.jinja'


class DailyFeeGolfView(GenericPageView):
    def process_request(self, request, *args, **kwargs):
        super().process_request(request, *args, **kwargs)
        if not request.club.daily_fee_location:
            raise Http404()


class BookTeeTimeView(DailyFeeGolfView):
    template = 'clubs/daily-fee-golf/book.jinja'


class DailyFeeRatesView(DailyFeeGolfView):
    template = 'clubs/daily-fee-golf/rates.jinja'


class EventsView(GenericPageView):
    template = 'clubs/events/events.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        tiles = []

        if request.site.id == 1:
            cutoff = 4
        else:
            cutoff = 3

        for child in self.page.children.filter(hidden_bucket=False).order_by('sort')[:cutoff]:
            tiles.append((
                child.url,
                child.name,
                child.redirects_externally,
            ))

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'tiles': tiles,
        })

        return extra_context


class GolfTournamentsView(GenericPageView):
    template = 'clubs/events/golf-tournaments.jinja'


class GolfTournamentsInquiryView(GenericPageView):
    form = GolfTournamentForm()
    template = 'clubs/events/golf-tournaments-inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = GolfTournamentForm(data=request.POST)

        if self.form.is_valid():
            self.form.send_email(request.club)
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)
            return redirect(reverse('events.golf-tournaments.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request)
        extra_context.update({
            'form': self.form,
        })
        return extra_context


class WeddingsView(GenericPageView):
    template = 'clubs/events/weddings.jinja'


class WeddingsInquiryView(GenericPageView):
    form = None
    template = 'clubs/events/weddings-inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = WeddingsForm(data=request.POST, club=request.club)

        if self.form.is_valid():
            self.form.send_email(request.club)
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)
            return redirect(reverse('events.weddings.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        if self.form is None:
            self.form = WeddingsForm(site=request.site, club=request.club)

        extra_context = super().get_extra_context(request)
        extra_context.update({
            'form': self.form,
        })

        return extra_context


class MeetingsView(GenericPageView):
    template = 'clubs/events/meetings.jinja'


class MeetingsInquiryView(GenericPageView):
    form = None
    template = 'clubs/events/meetings-inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = MeetingsForm(site=request.site, data=request.POST, club=request.club)

        if self.form.is_valid():
            self.form.send_email(request.club)
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)

            return redirect(reverse('events.meetings.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        if self.form is None:
            self.form = MeetingsForm(site=request.site, club=request.club)

        extra_context = super().get_extra_context(request)
        extra_context.update({
            'form': self.form,
        })

        return extra_context


class GameImprovementView(GenericPageView):
    template = 'clubs/game-improvement.jinja'


class ContactView(GenericPageView):
    template = 'clubs/contact.jinja'


class MyAccountView(GenericPageView):
    template = 'clubs/my-account/my-account.jinja'
    client = None

    def process_request(self, request, *args, **kwargs):
        self.client = DynamicsClient()
        return super().process_request(request, *args, **kwargs)

    def before_render(self, request, *args, **kwargs):
        self.client.disconnect()

    def get_extra_context(self, request, *args, **kwargs):
        summary = {}
        linked_members = []

        if request.member and request.member.membership_number:
            summary_cache_key = 'dyn:account_summary_{}'.format(request.member.membership_number)
            summary = cache.get(summary_cache_key, {})

            linked_cache_key = 'dyn:linked_members_{}'.format(request.member.membership_number)
            linked_members = cache.get(linked_cache_key, [])

            if not summary:
                summary = self.client.get_account_summary(request.member.membership_number)
                if summary:
                    cache.set(summary_cache_key, summary, 600)

            if not linked_members:
                try:
                    linked_members = self.client.get_linked_members(
                        request.member.membership_number)
                    if linked_members:
                        cache.set(linked_members, linked_members, 600)
                except OperationalError:
                    pass

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'summary': summary,
            'linked_members': linked_members,
        })
        return extra_context


class StatementView(GenericPageView):
    template = 'clubs/my-account/statement.jinja'
    statement_url = None

    def process_request(self, request, *args, **kwargs):
        super().process_request(request, *args, **kwargs)

        url_format = 'https://statements.clublinkprojects.ca/?display=last&member={}'
        member_id = request.member.encrypted_membership_number
        self.statement_url = url_format.format(quote_plus(member_id))

        if 'display' not in request.GET:
            return_url = '{}?display'.format(request.build_absolute_uri())
            self.statement_url += '&redirect={}'.format(quote_plus(return_url))
            return redirect(self.statement_url)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'statement_url': self.statement_url,
        })
        return extra_context


class AnnualDuesView(GenericPageView):
    template = 'clubs/my-account/annual-dues.jinja'


class BaseProfileView(GenericPageView):
    submenu = (
        (reverse_lazy('my-account.update-profile'), _('Profile')),
        (reverse_lazy('my-account.update-address'), _('Addresses')),
        (reverse_lazy('my-account.update-subscriptions'), _('Communications')),
    )

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'submenu': self.submenu
        })
        return extra_context


class UpdateSubscriptionsView(BaseProfileView):
    template = 'clubs/my-account/update-subscription.jinja'
    subscription_form = None

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)

        if not self.subscription_form:
            self.subscription_form = SubscriptionsForm(request.member)

        extra_context.update({
            'subscription_form': self.subscription_form,
        })
        return extra_context

    def post(self, request, *args, **kwargs):
        self.subscription_form = SubscriptionsForm(request.member, request.POST)

        success = True
        if self.subscription_form.is_valid():
            subscription_data = self.subscription_form.cleaned_data

            if request.member.membership_number:
                client = DynamicsClient()

                try:
                    client.update_member(member_id=request.member.membership_number,
                                         **subscription_data)
                except DynamicsClient.ClientError:
                    success = False
                    messages.add_message(request, messages.ERROR,
                                         _('An error occured. Please try again.'))

                client.disconnect()

            if success:
                profile = Profile.objects.filter(user=request.member)
                profile.update(**subscription_data)

                messages.add_message(request, messages.SUCCESS, _('Your profile was updated.'))
                return redirect(request.path)

        return self.get(request, *args, **kwargs)


class UpdateAddressView(BaseProfileView):
    template = 'clubs/my-account/update-address.jinja'

    HOME_ADDRESS = 'HOME'
    BUSINESS_ADDRESS = 'BUSINESS'
    COTTAGE_ADDRESS = 'COTTAGE'
    OTHER_ADDRESS = 'OTHER'

    address_types = [
        HOME_ADDRESS,
        BUSINESS_ADDRESS,
        COTTAGE_ADDRESS,
        OTHER_ADDRESS,
    ]
    address_labels = {
        HOME_ADDRESS: _('Home Address'),
        BUSINESS_ADDRESS: _('Business Address'),
        COTTAGE_ADDRESS: _('Cottage Address'),
        OTHER_ADDRESS: _('Other Address'),
    }

    def __init__(self, *args, **kwargs):
        self.forms = {}
        super().__init__(*args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)

        for address_type in self.address_types:
            if not self.forms.get(address_type):
                self.forms[address_type] = AddressForm(
                    request.member, address_type, prefix=address_type)

        extra_context.update({
            'address_labels': self.address_labels,
            'address_types': self.address_types,
            'forms': self.forms,
        })

        return extra_context

    def post(self, request, *args, **kwargs):
        client = DynamicsClient()

        is_valid = True
        for address_type in self.address_types:
            self.forms[address_type] = AddressForm(
                request.member, address_type, request.POST, prefix=address_type)

            is_valid = is_valid and self.forms[address_type].is_valid()

        errors = False
        if is_valid:
            for address_type in self.address_types:
                success = True
                if self.forms[address_type].has_data:
                    address_data = self.forms[address_type].cleaned_data

                    if request.member.membership_number:
                        try:
                            client.update_member_address(
                                member_id=request.member.membership_number, type=address_type,
                                **address_data)
                        except DynamicsClient.ClientError:
                            success = False
                            errors = True

                    if success:
                        Address.objects.update_or_create(
                            type=address_type, user=request.member, defaults=address_data)

            if errors:
                messages.add_message(
                    request, messages.ERROR, _('An error occured. Please try again.'))
            else:
                messages.add_message(request, messages.SUCCESS, _('Your profile was updated.'))
                return redirect(request.path)

        client.disconnect()
        return self.get(request, *args, **kwargs)


class UpdateProfileView(BaseProfileView):
    template = 'clubs/my-account/update-profile.jinja'
    user_form = None
    profile_form = None
    preference_form = None

    def get_extra_context(self, request, *args, **kwargs):
        if not self.user_form:
            self.user_form = UserForm(request.member)

        if not self.profile_form:
            self.profile_form = ProfileForm(request.member)

        if not self.preference_form:
            self.preference_form = PreferenceForm(request.member)

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'user_form': self.user_form,
            'profile_form': self.profile_form,
            'preference_form': self.preference_form,
        })

        return extra_context

    def post(self, request, *args, **kwargs):
        self.user_form = UserForm(request.member, request.POST)
        self.profile_form = ProfileForm(request.member, request.POST)
        self.preference_form = PreferenceForm(request.member, request.POST)

        success = True

        if (self.user_form.is_valid() and self.profile_form.is_valid()
                and self.preference_form.is_valid()):
            member = User.objects.filter(pk=request.member.pk)
            user_data = self.user_form.cleaned_data
            profile_data = self.profile_form.cleaned_data
            preference_data = self.preference_form.cleaned_data
            password = user_data.pop('password')
            user_data.pop('password_confirm')

            if request.member.membership_number:

                show_phone = profile_data.pop('show_phone')
                show_email = profile_data.pop('show_email')

                profile_data['show_phone_id'] = show_phone
                profile_data['show_email_id'] = show_email


                mailing_address = preference_data.get('mailing_address')
                billing_address = preference_data.get('billing_address')

                member_data = {
                    'member_id': request.member.membership_number,
                    'employer': profile_data.get('employer'),
                    'position': profile_data.get('position'),
                    'preferred_language': user_data.get('preferred_language'),
                    'show_in_roster': profile_data.get('show_in_roster'),
                    'email_address': user_data.get('email'),
                    'mailing_id': mailing_address.type if mailing_address else None,
                    'billing_id': billing_address.type if billing_address else None,
                }

                client = None

                # Skip this for development
                if 'dev' not in settings.CONFIGURATION.lower():
                    try:
                        client = DynamicsClient()
                        client.update_member(**member_data)
                    except DynamicsClient.ClientError as e:
                        print(member_data)
                        print(e)
                        logging.error(e)
                        success = False
                        messages.add_message(
                            request, messages.ERROR, _('An error occured. Please try again.'))
                    finally:
                        if client:
                            client.disconnect()



            if success:
                member.update(**user_data)

                if password:
                    request.member.set_password(password)
                    request.member.save()

                profile = Profile.objects.filter(user=request.member)
                profile.update(**profile_data, **preference_data)

                messages.add_message(request, messages.SUCCESS, _('Your profile was updated.'))
                return redirect(request.path)

        return self.get(request, *args, **kwargs)


class PaymentTermsView(MyAccountView):
    template = 'clubs/my-account/base.jinja'


class LinkLineBookTeeTimeView(GenericPageView):
    template = 'clubs/linkline/book.jinja'
    booking_url = None

    def process_request(self, request, *args, **kwargs):
        if getattr(request, 'webres_member_token', None):
            self.booking_url = (
                'https://ww5.goibsvision.com/WebRes/Club/{}/LoginWithToken/{}'.format(
                    request.webres_friendly_name, request.webres_member_token))

        ua = user_agents.parse(request.META['HTTP_USER_AGENT'])
        if self.booking_url and (ua.is_mobile or ua.is_tablet):
            return redirect(self.booking_url)
        elif self.booking_url:
            return redirect(self.booking_url)

        return super().process_request(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'booking_url': self.booking_url,
        })
        return extra_context


class GolfPoliciesView(GenericPageView):
    template = 'clubs/linkline/base.jinja'


class LinkLineTermsOfUseView(GenericPageView):
    template = 'clubs/linkline/base.jinja'


class NewsView(GenericPageView):
    template = 'clubs/news/news.jinja'
    news = News.objects.none()

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        self.news = News.objects.filter(publish_date__lte=timezone.now(), show_on_club_site=True)
        filter_club = request.GET.get('filter_club')
        if filter_club:
            self.news = self.news.filter(clubs__id__in=[filter_club])
        else:
            self.news = self.news.filter(Q(clubs__in=[request.club]) | Q(clubs=None))
        extra_context.update({
            'news': self.news,
        })
        return extra_context


class NewsItemView(NewsView):
    template = 'clubs/news/news-item.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        try:
            extra_context['news_item'] = self.news.get(slug=kwargs.get('slug'))
        except News.DoesNotExist:
            raise Http404
        return extra_context
