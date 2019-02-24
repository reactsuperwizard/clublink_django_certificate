from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static

from clublink.base import views as base_views


urlpatterns = [
    url(r'^__health__/$', base_views.health_check),
    url(r'^__sns__/$', base_views.sns_handler),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

import shared_session

urlpatterns += [
    url(r'^shared-session/', shared_session.urls),  # feel free to change the base url
]