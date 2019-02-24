from django.conf import settings
from django.conf.urls import url, include
from django.contrib.staticfiles.views import serve
from django.conf.urls.static import static
from django.urls import path, include


from clublink.clubs import views

from django.contrib.sitemaps.views import sitemap
from ..sitemaps import ClubPageSitemap

urlpatterns = []

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)   

urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),

    # Corporate sitemap to include
    path('sitemap.xml', sitemap,
         {'sitemaps': 
            {
                'pages': ClubPageSitemap
            },
        },
         name='django.contrib.sitemaps.views.sitemap'),    
    
    url(r'^robots\.txt', include('robots.urls')),

    # Auth pages
    url(r'^logout/$', views.logout, name='logout'),

    # About pages
    url(r'^about/$', views.AboutView.as_view(), name='about'),
    url(r'^about/gallery/$', views.GalleryView.as_view(),
        name='about.gallery'),
    url(r'^about/gallery/(?P<slug>[^\/]+)/$', views.GalleryView.as_view(),
        name='about.gallery', kwargs={'full_path': 'about/gallery'}),
    url(r'^about/team/$', views.TeamView.as_view(), name='about.team'),
    url(r'^about/golf-shop/$', views.GolfShopView.as_view(), name='about.golf-shop'),
    url(r'^about/policies/$', views.PoliciesView.as_view(), name='about.policies'),

    # My Club pages
    url(r'^my-club/$', views.GenericPageView.as_view(), name='my-club'),
    url(r'^my-club/calendar/$', views.CalendarView.as_view(), name='my-club.calendar'),
    url(r'^my-club/calendar/(?P<pk>[0-9]+)/$', views.CalendarItemView.as_view(),
        name='my-club.calendar-item', kwargs={'full_path': 'my-club/calendar'}),
    url(r'^my-club/gallery/$', views.GalleryView.as_view(),
        name='my-club.gallery'),
    url(r'^my-club/gallery/(?P<slug>[^\/]+)/$', views.GalleryView.as_view(),
        name='my-club.gallery', kwargs={'full_path': 'my-club/gallery'}),
    url(r'^my-club/roster/$', views.RosterView.as_view(), name='my-club.roster'),
    url(r'^my-club/bistro-menus/$', views.GenericPageView.as_view(), name='my-club.bistro-menus'),
    url(r'^my-club/golf-shop/$', views.GolfShopView.as_view(), name='my-club.golf-shop'),
    url(r'^my-club/team/$', views.TeamView.as_view(), name='my-club.team'),

    # My Account pages
    url(r'^my-account/$', views.MyAccountView.as_view(), name='my-account'),
    url(r'^my-account/statement/$', views.StatementView.as_view(), name='my-account.statement'),
    url(r'^my-account/annual-dues/$', views.AnnualDuesView.as_view(),
        name='my-account.annual-dues'),
    url(r'^my-account/update-profile/$', views.UpdateProfileView.as_view(),
        name='my-account.update-profile'),
    url(r'^my-account/update-profile/addresses/$', views.UpdateAddressView.as_view(),
        name='my-account.update-address', kwargs={'full_path': 'my-account/update-profile'}),
    url(r'^my-account/update-profile/subscriptions/$', views.UpdateSubscriptionsView.as_view(),
        name='my-account.update-subscriptions', kwargs={'full_path': 'my-account/update-profile'}),
    url(r'^my-account/member-services/$', views.GenericPageView.as_view(),
        name='my-account.member-services'),
    url(r'^my-account/payment-terms/$', views.PaymentTermsView.as_view(),
        name='my-account.payment-terms'),

    # LinkLine pages
    url(r'^linkline/$', views.GenericPageView.as_view(), name='linkline'),
    url(r'^linkline/book-a-tee-time/$', views.LinkLineBookTeeTimeView.as_view(),
        name='linkline.book-a-tee-time'),
    url(r'^linkline/guest-fees/$', views.GuestFeesView.as_view(), name='linkline.guest-fees'),
    url(r'^linkline/golf-policies/$', views.GolfPoliciesView.as_view(),
        name='linkline.golf-policies'),
    url(r'^linkline/terms-of-use/$', views.LinkLineTermsOfUseView.as_view(),
        name='linkline.terms-of-use'),


    # News pages
    url(r'^news/$', views.NewsView.as_view(), name='news'),
    url(r'^news/(?P<slug>[^\/]+)/$', views.NewsItemView.as_view(), name='news-item',
        kwargs={'full_path': 'news'}),

    # Membership pages
    url(r'^membership/$', views.MembershipView.as_view(), name='membership'),
    url(r'^membership/inquiry/$', views.MembershipInquiryView.as_view(),
        name='membership.inquiry'),
    url(r'^membership/guest-fees/$', views.GuestFeesView.as_view(),
        name='membership.guest-fees'),

    # Daily Fee Golf pages
    url(r'^daily-fee-golf/book/$', views.BookTeeTimeView.as_view(), name='daily-fee-golf.book'),
    url(r'^daily-fee-golf/rates/$', views.DailyFeeRatesView.as_view(),
        name='daily-fee-golf.rates'),

    # Events pages
    url(r'^events/$', views.EventsView.as_view(), name='events'),
    url(r'^events/golf-tournaments/$', views.GolfTournamentsView.as_view(),
        name='events.golf-tournaments'),
    url(r'^events/golf-tournaments/inquiry/$', views.GolfTournamentsInquiryView.as_view(),
        name='events.golf-tournaments.inquiry'),
    url(r'^events/weddings/$', views.WeddingsView.as_view(), name='events.weddings'),
    url(r'^events/weddings/inquiry/$', views.WeddingsInquiryView.as_view(),
        name='events.weddings.inquiry'),
    url(r'^events/meetings/$', views.MeetingsView.as_view(), name='events.meetings'),
    url(r'^events/meetings/inquiry/$', views.MeetingsInquiryView.as_view(),
        name='events.meetings.inquiry'),

    # Game Improvement page
    url(r'^game-improvement/$', views.GameImprovementView.as_view(), name='game-improvement'),

    # Contact page
    url(r'^contact-us/$', views.ContactView.as_view(), name='contact-us'),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^favicon.ico$', serve, kwargs={'path': 'favicon.ico'}),
        url(r'^__403__/$', views.handler403),
        url(r'^__404__/$', views.handler404),
        url(r'^__500__/$', views.handler500),
    ]

# This is a catch all that must go after all other routes
# This is also a pretty terrible idea.
urlpatterns += [
    url(r'(?P<full_path>.*)/$', views.GenericPageView.as_view(), name='generic'),
]
