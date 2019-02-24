from django.conf.urls import url, include
from django.conf import settings

from clublink.landings import views


urlpatterns = [
    url(r'^$', views.gift_cards, name='home'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]    

import shared_session

urlpatterns += [
    url(r'^shared-session/', shared_session.urls),  # feel free to change the base url
]