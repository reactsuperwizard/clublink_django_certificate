from django.conf.urls import include, url


urlpatterns = [
    url(r'^club-sites/', include('clublink.cms.modules.club_sites.urls')),
    url(r'^corp-site/', include('clublink.cms.modules.corp_site.urls')),
    url(r'^assets/', include('clublink.cms.modules.assets.urls')),
    url(r'^users/', include('clublink.cms.modules.users.urls')),
    url(r'', include('clublink.cms.modules.dashboard.urls')),
]
