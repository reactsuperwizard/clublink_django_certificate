from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter

from clublink.certificates.api import views

urlpatterns = [
    url('^v1/certificate/$', views.CertificateView.as_view()),
]
