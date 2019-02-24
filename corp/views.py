from itertools import groupby

from django import views
from django.contrib import messages
from django.contrib.auth import (
    logout as auth_logout,
)
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django import forms

from clublink.base.clients.ibs import WebMemberClient

from clublink.base.forms import (
    GolfTournamentForm,
    MeetingsForm,
    MembershipForm,
    WeddingsForm,
    GolfForLifeForm,
)

from clublink.cms.modules.corp_site.forms import (InventoryLookupForm)

from clublink.base.messages import FORM_SUBMITTED_MESSAGE
from clublink.clubs.models import Club, Region
from clublink.corp.models import News
from clublink.cms.models import CorpEventsGallery, CorpPage, Campaigner

from pprint import pprint

def logout(request):
    auth_logout(request)
    return redirect(reverse('home'))


def redirect_home(request):
    return redirect(reverse('home'), permanent=True)


class GenericPageView(views.View):
    template = 'corp/generic/default.jinja'
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

            for page in parent.children.filter(site=get_current_site(request)):

                menu.append((
                    page.url,
                    page.name,
                    page.target,
                ))

        self.menu = menu

    def process_request(self, request, *args, **kwargs):

        self.full_path = kwargs.get('full_path', request.path.strip('/'))
        # import pdb; pdb.set_trace();
        self.page = get_object_or_404(
            CorpPage,
            full_path=self.full_path,
            site=get_current_site(request)
            )

        if self.page.should_redirect:
            if self.page.internal_redirect:
                return redirect(self.page.internal_redirect.url)
            elif self.page.external_redirect:
                return redirect(self.page.external_redirect)

    def get_extra_context(self, request, *args, **kwargs):
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
        return render(request, self.template, context)

    def dispatch(self, request, *args, **kwargs):
        response = self.process_request(request, *args, **kwargs)
        if response:
            return response

        return super().dispatch(request, *args, **kwargs)


class HomeView(GenericPageView):
    template = 'corp/home.jinja'


webclient = WebMemberClient()

class PublicInventoryLookupView(GenericPageView):
    '''
    As you're reading this, you might be wondering... why am I using this non-sense, 
    custom CMS' base view class?  Well... it's because the template structure is so 
    intimately tied to the variables in the "get_extra_context", that there is essentially 
    no other way to do this without rewriting a new set of views and base templates.

    You'll need to make sure to create the object in the DB, or the weird-ass middleware
    will 400 on not finding this in the DB.

    Oh yeah... you'll have to create it on both the sites because... reasons... too.
    '''

    template = 'corp/inventory-lookup.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': InventoryLookupForm()})
        return context

    def get(self, request, *args, **kwargs):
        # print(request.GET)

        query = request.GET.get('query', None)

        if query:
            print(query)
            query = query.strip()
            context = self.get_extra_context(request, *args, **kwargs)
            context['query'] = query

            form = context['form']
            form.initial = {'query': query}
            context['form'] = form

            # print(webclient.user)
            # print(webclient.password)

            data = webclient.get_inventory(query, 'CONTAINS')

            # print(data)

            error = data.get('a_sMessage')
            if error and "is not online" in error:
                messages.add_message(request, messages.ERROR,
                                     _('IBS client is not online'))

            #message = data.get('a_sMessage', None)
            result = data.get('SearchOnHandRetailInventoryResult', None)

            # Uncomment after deploy
            # if result:

            # Delete after deploy
            if result:

                # if settings.DEBUG:

                #     '''
                #     Example payload because the IBS server is turned off at night:

                #         from decimal import Decimal
                #         payload = [
                #             {
                #                 'ItemNumber': '086056',
                #                 'ItemName': 'Winn Dri Tac',
                #                 'DepartmentNumber': 'DB',
                #                 'DepartmentName': 'DiamondBack Golf Club',
                #                 'OnHandQuantity': 7,
                #                 'ItemPrice': Decimal('12.40')
                #             },
                #             {
                #                 'ItemNumber': '086056',
                #                 'ItemName': 'Winn Gripps',
                #                 'DepartmentNumber': 'KV',
                #                 'DepartmentName': 'King Valley Golf Club',
                #                 'OnHandQuantity': 45,
                #                 'ItemPrice': Decimal('14.15')
                #             }
                #         ]
                #     '''

                #     from decimal import Decimal
                #     payload = [
                #         {
                #             'ItemNumber': '086056',
                #             'ItemName': 'Winn Dri Tac',
                #             'DepartmentNumber': 'DB',
                #             'DepartmentName': 'DiamondBack Golf Club',
                #             'OnHandQuantity': 7,
                #             'ItemPrice': Decimal('12.40')
                #         },
                #         {
                #             'ItemNumber': '086056',
                #             'ItemName': 'Winn Gripps',
                #             'DepartmentNumber': 'KV',
                #             'DepartmentName': 'King Valley Golf Club',
                #             'OnHandQuantity': 45,
                #             'ItemPrice': Decimal('14.15')
                #         }
                #     ]
                # else:
                payload = result.get('InvItemSearchData', None)

                if len(payload) >= 200:
                    messages.add_message(
                        request, messages.INFO,
                        _('Query contains 200 or more results.  A maximum of 200 results are shown.  Try refining your search.'
                          ))

                # See: https://docs.python.org/3/library/itertools.html#itertools.groupby if needed
                grouped_payload = groupby(
                    payload, key=lambda x: x['DepartmentName'])

                final_groups = []

                for k, v in grouped_payload:
                    output = list(v)
                    if output:
                        final_groups.append((k, output))

                context['groups'] = final_groups

            else:
                context['groups'] = None
                messages.add_message(
                    request, messages.INFO,
                    _('No results were found for "{}"'.format(query)))

            return render(request, self.template, context)

        else:
            # Go through regular flow but add in the context
            return super(PublicInventoryLookupView, self).get(
                request, *args, **kwargs)


class AboutView(GenericPageView):
    template = 'corp/about.jinja'


class NewsView(GenericPageView):
    template = 'corp/news/news.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        news = News.objects.filter(show_on_corp_site=True)
        if request.LANGUAGE_CODE == 'fr':
            news = [n for n in news if n.fully_french]
        extra_context.update({
            'news': news,
        })
        return extra_context


class NewsItemView(NewsView):
    template = 'corp/news/news-item.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        try:
            extra_context.update({
                'news_item': News.objects.get(slug=kwargs.get('slug'))
            })
        except News.DoesNotExist:
            raise Http404
        return extra_context


class EmploymentView(GenericPageView):
    template = 'corp/employment/employment.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        return extra_context


class OpportunitiesView(GenericPageView):
    template = 'corp/employment/opportunities.jinja'


class LifeAtClublinkView(GenericPageView):
    template = 'corp/employment/life-at-clublink.jinja'


class DailyFeeGolfView(GenericPageView):
    MENU = (
        ('daily-fee-golf', _('Daily Fee Club Listing')),
        ('daily-fee-golf.book', _('Book a Tee Time')),
    )

    template = 'corp/daily-fee-golf/daily-fee-golf.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)

        clubs = Club.objects.filter(daily_fee_location=True, hide_daily_fees=False, site=request.site)
        extra_context.update({
            'clubs': clubs,
        })

        return extra_context


class BookTeeTimeView(GenericPageView):
    template = 'corp/daily-fee-golf/book.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super(BookTeeTimeView, self).get_extra_context(request, *args, **kwargs)

        if self.kwargs.get('booking_region', None):
            # import pdb; pdb.set_trace();
            extra_context['booking_region'] = Region.objects.get(slug=self.kwargs.get('booking_region'))

        return extra_context

class EventsView(GenericPageView):
    def get(self, request, *args, **kwargs):
        return redirect(reverse('events.weddings'))


class GolfTournamentsView(GenericPageView):
    template = 'corp/events/golf-tournaments.jinja'


class GolfTournamentsInquiryView(GenericPageView):
    form = GolfTournamentForm()
    template = 'corp/events/golf-tournaments-inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = GolfTournamentForm(request.POST)

        if self.form.is_valid():
            self.form.send_email()
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)
            return redirect(reverse('events.golf-tournaments.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form
        })

        return extra_context


class MeetingsInquiryView(GenericPageView):
    form = None
    template = 'corp/events/meetings-inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = MeetingsForm(data=request.POST)

        if self.form.is_valid():
            self.form.send_email()
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)
            return redirect(reverse('events.meetings.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        if self.form is None:
            self.form = MeetingsForm(site=request.site)

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
        })

        return extra_context


class WeddingsView(GenericPageView):
    template = 'corp/events/weddings.jinja'


class WeddingsInquiryView(GenericPageView):
    form = None
    template = 'corp/events/weddings-inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = WeddingsForm(data=request.POST)

        if self.form.is_valid():
            self.form.send_email()
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)
            return redirect(reverse('events.weddings.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        if self.form is None:
            self.form = WeddingsForm(site=request.site)
            # club_choices = [('', '')] + [(c.pk, c.name) for c in Club.objects.filter(site=request.site).exclude(slug=None)]
            # self.form = WeddingsForm().fields['location'] = forms.ChoiceField(choices=club_choices, widget=forms.Select)


        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
        })

        return extra_context


class WeddingsVenuesView(GenericPageView):
    template = 'corp/events/venues.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        regions = Region.objects.filter(site=request.site).annotate(club_count=Count('clubs')).filter(club_count__gt=0)

        try:
            region = Region.objects.get(slug=kwargs.get('slug'))
        except Region.DoesNotExist:
            if not kwargs.get('slug'):
                region = regions.first()
            else:
                raise Http404

        extra_context.update({
            'regions': regions,
            'region': region
        })

        return extra_context


class WeddingsResortsView(GenericPageView):
    template = 'corp/events/resorts.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context['clubs'] = Club.objects.filter(
            is_resort=True,
            resort_weddings_url__isnull=False,
            no_weddings=False
            )
        return context


class WeddingsTestimonialsView(GenericPageView):
    template = 'corp/events/testimonials.jinja'


class WeddingsGalleryView(GenericPageView):
    template = 'corp/events/gallery.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        galleries = CorpEventsGallery.objects.filter(site=request.site)

        try:
            gallery = CorpEventsGallery.objects.get(slug=kwargs.get('slug'))
        except CorpEventsGallery.DoesNotExist:
            if not kwargs.get('slug'):
                gallery = galleries.first()
            else:
                raise Http404

        extra_context.update({
            'galleries': galleries,
            'gallery': gallery
        })

        return extra_context


class MembershipView(GenericPageView):
    template = 'corp/membership/overview.jinja'


class OurClubsView(GenericPageView):
    template = 'corp/membership/clubs.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)

        regions = Region.objects.filter(site=request.site).annotate(club_count=Count('clubs')).filter(club_count__gt=0)

        try:
            region = Region.objects.get(slug=kwargs.get('slug'))
        except Region.DoesNotExist:
            region = regions.first()

        extra_context.update({
            'regions': regions,
            'region': region
        })

        return extra_context


class MembershipInquiryView(GenericPageView):
    form = None
    template = 'corp/membership/inquiry.jinja'

    def post(self, request, *args, **kwargs):
        self.form = MembershipForm(data=request.POST)

        if self.form.is_valid():
            self.form.send_email()
            messages.add_message(request, messages.SUCCESS, FORM_SUBMITTED_MESSAGE)
            return redirect(reverse('membership.inquiry'))

        return self.get(request, *args, **kwargs)

    def get_extra_context(self, request, *args, **kwargs):
        if not self.form:
            self.form = MembershipForm(request=request)

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form
        })

        return extra_context


class ClubLinkLifeView(GenericPageView):
    template = 'corp/membership/clublink-life.jinja'


class GameImprovementView(GenericPageView):
    template = 'corp/improvement/overview.jinja'


class AcademiesView(GenericPageView):
    template = 'corp/improvement/academies.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)

        regions = request.site.regions.annotate(club_count=Count('clubs')).filter(club_count__gt=0)

        try:
            region = Region.objects.get(slug=kwargs.get('slug'))
        except Region.DoesNotExist:
            region = regions.first()

        extra_context.update({
            'regions': regions,
            'region': region
        })

        return extra_context


class ContactView(GenericPageView):
    template = 'corp/contact.jinja'


class ResortsView(GenericPageView):
    template = 'corp/resorts.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context['clubs'] = Club.objects.filter(is_resort=True, site=request.site)
        return context


class ShopView(GenericPageView):
    template = 'corp/shop.jinja'




class GolfForLifeView(GenericPageView):
    form = None
    template = 'corp/golfforlife/enternow.jinja'
    
    def post(self, request, *args, **kwargs):
        self.form = GolfForLifeForm(data=request.POST)
      
        if self.form.is_valid():
            
            email_res = self.form.isEmailValid()            
            if email_res[0] == False :
                messages.add_message(request, messages.ERROR, _('Email is not valid. Please confirm your email.'))
                return redirect(reverse('golfforlife'))
            
            print('pin verification')
            pin_res = self.form.isPinCodeValid(email_res[1], email_res[2])
            if pin_res[0] == False:
                messages.add_message(request, messages.ERROR, pin_res[1])
                return redirect(reverse('golfforlife'))

            self.form.send_email()
            messages.add_message(request, messages.SUCCESS, 
                _('THANK YOU FOR COMPLETING THE INQUIRY FORM. A MEMBER OF OUR TEAM WILL BE IN TOUCH WITH YOU SOON.'))
            return redirect(reverse('golfforlife'))
        return self.get(request, *args, **kwargs)


    def get_extra_context(self, request, *args, **kwargs):
        if not self.form:
            self.form = GolfForLifeForm(request=request)

        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form
        })

        return extra_context