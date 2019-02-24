from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

from clublink.certificates import views


handler403 = views.handler403
handler404 = views.handler404
handler500 = views.handler500


urlpatterns = [
    url(r'', include('clublink.certificates.urls.gc')),
    url(r'', include('clublink.certificates.urls.api')),
]

if settings.ADMIN_ENABLED:
    urlpatterns += [
        url(r'^admin/', admin.site.urls),
        url(r'^admin/rosetta/', include('rosetta.urls')),
    ]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]




if settings.DEBUG:
    urlpatterns += [
        url(r'^__403__/$', handler403),
        url(r'^__404__/$', handler404),
        url(r'^__500__/$', handler500),
    ]

import shared_session

urlpatterns += [
    url(r'^shared-session/', shared_session.urls),  # feel free to change the base url
]