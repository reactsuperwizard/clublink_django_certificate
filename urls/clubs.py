from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin

from clublink.clubs import views
from clublink.urls.common import urlpatterns as common_patterns

from rest_framework.routers import DefaultRouter
from clublink.users.viewsets import MemberRosterViewSet

router = DefaultRouter()
router.register(r'members', MemberRosterViewSet)

urlpatterns = [*common_patterns]


handler500 = views.handler500
handler404 = views.handler404
handler403 = views.handler403


if settings.ADMIN_ENABLED:
    urlpatterns += [
        url(r'^admin/', admin.site.urls),
        url(r'^admin/rosetta/', include('rosetta.urls')),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import shared_session

urlpatterns += [
    url(r'^shared-session/', shared_session.urls),  # feel free to change the base url
]

urlpatterns += [
    url(r'^api/v1/', include(router.urls)),
    url(r'', include('clublink.cms.urls.clubs')),
    url(r'', include('clublink.users.urls.clubs')),
    url(r'', include('clublink.clubs.urls.clubs')),  # This should always be last
]
