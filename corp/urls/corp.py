from django.conf.urls import url
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include


from clublink.corp import views

from ..sitemaps import CorpNewsSitemap, CorpPageSitemap


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^robots\.txt', include('robots.urls')),
    url(r'^accessibility/$',
        views.GenericPageView.as_view(),
        name='accessibility'),
    url(r'^privacy-policy/$',
        views.GenericPageView.as_view(),
        name='privacy-policy'),
        
    url(r'^inventory-lookup/$',
        views.PublicInventoryLookupView.as_view(),
        name='public.inventory-lookup'),

    # Corporate sitemap to include
    path(
        'sitemap.xml',
        sitemap, {
            'sitemaps': {
                'news': CorpNewsSitemap,
                'pages': CorpPageSitemap
            },
        },
        name='django.contrib.sitemaps.views.sitemap'),


    # Auth pages
    url(r'^logout/$', views.logout, name='logout'),

    # About pages
    url(r'^about/$', views.AboutView.as_view(), name='about'),
    url(r'^about/our-story/$',
        views.GenericPageView.as_view(),
        name='about.our-story'),
    url(r'^about/our-clubs/$',
        views.GenericPageView.as_view(),
        name='about.our-clubs'),
    url(r'^about/news/$', views.NewsView.as_view(), name='news'),
    url(r'^about/news/(?P<slug>[^\/]+)/$',
        views.NewsItemView.as_view(),
        name='news-item',
        kwargs={'full_path': 'about/news'}),

    # Employment pages
    url(r'^about/employment/$',
        views.EmploymentView.as_view(),
        name='employment'),
    url(r'^about/employment/who-we-are/$',
        views.GenericPageView.as_view(),
        name='employment.who-we-are'),
    url(r'^about/employment/faq/$',
        views.GenericPageView.as_view(),
        name='employment.faq'),
    url(r'^about/employment/life-at-clublink/$',
        views.LifeAtClublinkView.as_view(),
        name='employment.life-at-clublink'),
    url(r'^about/employment/opportunities/$',
        views.OpportunitiesView.as_view(),
        name='employment.opportunities'),
    url(r'^about/employment/job-fairs/$',
        views.GenericPageView.as_view(),
        name='employment.job-fairs'),

    # Membership pages
    url(r'^membership/$', views.MembershipView.as_view(), name='membership'),
    url(r'^membership/clubs/$',
        views.OurClubsView.as_view(),
        name='membership.clubs'),
    url(r'^membership/clubs/(?P<slug>[^\/]+)/$',
        views.OurClubsView.as_view(),
        name='membership.clubs',
        kwargs={'full_path': 'membership/clubs'}),
    url(r'^membership/inquiry/$',
        views.MembershipInquiryView.as_view(),
        name='membership.inquiry'),
    url(r'^membership/clublink-life/$',
        views.ClubLinkLifeView.as_view(),
        name='clublink-life'),
    url(r'^membership/categories/$',
        views.GenericPageView.as_view(),
        name='membership.categories'),
    url(r'^membership/faq/$',
        views.GenericPageView.as_view(),
        name='membership.faq'),
    url(r'^membership/rules/$',
        views.GenericPageView.as_view(),
        name='membership.rules'),

    # Daily Fee Golf pages
    url(r'^daily-fee-golf/$',
        views.DailyFeeGolfView.as_view(),
        name='daily-fee-golf'),
    url(r'^daily-fee-golf/book/$',
        views.BookTeeTimeView.as_view(),
        name='daily-fee-golf.book'),

    # Game Improvement pages
    url(r'^improvement/$',
        views.GameImprovementView.as_view(),
        name='improvement'),
    url(r'^improvement/our-academies/$',
        views.AcademiesView.as_view(),
        name='improvement.academies'),
    url(r'^improvement/our-academies/(?P<slug>[^\/]+)/$',
        views.AcademiesView.as_view(),
        name='improvement.academies',
        kwargs={'full_path': 'improvement/our-academies'}),

    # Events pages
    url(r'^events/$', views.EventsView.as_view(), name='events'),
    url(r'^events/golf-tournaments/$',
        views.GolfTournamentsView.as_view(),
        name='events.golf-tournaments'),
    url(r'^events/golf-tournaments/inquiry/$',
        views.GolfTournamentsInquiryView.as_view(),
        name='events.golf-tournaments.inquiry'),
    url(r'^events/meetings/$',
        views.GenericPageView.as_view(),
        name='events.meetings'),
    url(r'^events/meetings/inquiry/$',
        views.MeetingsInquiryView.as_view(),
        name='events.meetings.inquiry'),
    url(r'^events/weddings/$',
        views.WeddingsView.as_view(),
        name='events.weddings'),
    url(r'^events/weddings/inquiry/$',
        views.WeddingsInquiryView.as_view(),
        name='events.weddings.inquiry'),
    url(r'^events/weddings/venues/$',
        views.WeddingsVenuesView.as_view(),
        name='events.weddings.venues'),
    url(r'^events/weddings/venues/(?P<slug>[^\/]+)/$',
        views.WeddingsVenuesView.as_view(),
        name='events.weddings.venues',
        kwargs={'full_path': 'events/weddings/venues'}),
    url(r'^events/weddings/resorts/$',
        views.WeddingsResortsView.as_view(),
        name='events.weddings.resorts'),
    url(r'^events/weddings/cultural/$',
        views.GenericPageView.as_view(),
        name='events.weddings.cultural'),
    url(r'^events/weddings/testimonials/$',
        views.WeddingsTestimonialsView.as_view(),
        name='events.weddings.testimonials'),
    url(r'^events/weddings/gallery/$',
        views.WeddingsGalleryView.as_view(),
        name='events.weddings.gallery'),
    url(r'^events/weddings/gallery/(?P<slug>[^\/]+)/$',
        views.WeddingsGalleryView.as_view(),
        name='events.weddings.gallery',
        kwargs={'full_path': 'events/weddings/gallery'}),

    # Contact pages
    url(r'^contact/$', views.ContactView.as_view(), name='contact'),

    # Resorts pages
    url(r'^resorts/$', views.ResortsView.as_view(), name='resorts'),

    # Shop pages
    url(r'^shop/$', views.ShopView.as_view(), name='shop'),
    # Shop pages
    url(r'^golfforlife/$', views.GolfForLifeView.as_view(), name='golfforlife'),

    # This is a catch all that must go after all other routes
    url(r'(?P<full_path>.*)/', views.GenericPageView.as_view(),
        name='generic'),
]


import shared_session

urlpatterns += [
    url(r'^shared-session/', shared_session.urls),  # feel free to change the base url
]