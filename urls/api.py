from django.conf.urls import include, url
from rest_framework_swagger.views import get_swagger_view



urlpatterns = [
    url(r'', include('clublink.users.urls.api')),
    url(r'', include('clublink.base.urls.api')),
    url(r'', include('clublink.certificates.urls.api')),
]

urlpatterns += [
    url(r'^docs/$', get_swagger_view(title='ClubLink API', patterns=urlpatterns))
]

import shared_session

urlpatterns += [
    url(r'^shared-session/', shared_session.urls),  # feel free to change the base url
]