from django.conf.urls import url
from django.conf import settings
from clublink.cms.modules.corp_site import views
from django.conf.urls.static import static

urlpatterns = []

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    # Corp Site CMS
    url(r'^$', views.CorpSiteView.as_view(), name='corp-site.home'),
    url(r'^pages/$', views.PagesView.as_view(), name='corp-site.pages'),
    url(r'^pages/new/$',
        views.PagesAddView.as_view(),
        name='corp-site.pages-add'),
    url(r'^pages/(?P<page_pk>[0-9]+)/$',
        views.PagesEditView.as_view(),
        name='corp-site.pages-edit'),
    url(r'^pages/(?P<page_pk>[0-9]+)/delete/$',
        views.PagesDeleteView.as_view(),
        name='corp-site.pages-delete'),
    url(r'^news/$', views.NewsView.as_view(), name='corp-site.news'),
    url(r'^news/new/$', views.NewsAddView.as_view(),
        name='corp-site.news-add'),
    url(r'^news/(?P<news_item_pk>[0-9]+)/$',
        views.NewsEditView.as_view(),
        name='corp-site.news-edit'),
    url(r'^news/(?P<news_item_pk>[0-9]+)/delete/$',
        views.NewsDeleteView.as_view(),
        name='corp-site.news-delete'),
    url(r'^inventory-lookup/$',
        views.InventoryLookupView.as_view(),
        name='inventory-lookup'),
    url(r'^events-gallery/$',
        views.EventsGalleryView.as_view(),
        name='corp-site.events-gallery'),
    url(r'^events-gallery/new/(?P<site_pk>[0-9])?$',
        views.EventsGalleryAddView.as_view(),
        name='corp-site.events-gallery-add'),
    url(r'^events-gallery/reorder/$',
        views.EventsGalleryReorderView.as_view(),
        name='corp-site.events-gallery-reorder'),
    url(r'^events-gallery/(?P<gallery_pk>[0-9]+)/$',
        views.EventsGalleryEditView.as_view(),
        name='corp-site.events-gallery-edit'),
    url(r'^events-gallery/(?P<gallery_pk>[0-9]+)/delete/$',
        views.EventsGalleryDeleteView.as_view(),
        name='corp-site.events-gallery-delete'),
    url(r'^events-gallery/(?P<gallery_pk>[0-9]+)/image/(?P<image_pk>[0-9]+)/delete/$',
        views.EventsGalleryImageDeleteView.as_view(),
        name='corp-site.events-gallery-image-delete'),
    url(r'^golfforlife/$', views.GiftCardExchangerView.as_view(), name='corp-site.golfforlife'),
]