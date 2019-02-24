from django.conf.urls import url

from clublink.base.api import views


urlpatterns = [
    url('^v1/ping/$', views.PingView.as_view()),
]
