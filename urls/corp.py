from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static

from clublink.urls.common import urlpatterns as common_patterns


urlpatterns = [*common_patterns]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    url(r'', include('clublink.cms.urls.clubs')),
    url(r'', include('clublink.users.urls.corp')),
    url(r'', include('clublink.corp.urls.corp')),  # This should always be last
]

import shared_session

urlpatterns += [
    url(r'^shared-session/', shared_session.urls),  # feel free to change the base url
]