from django.conf.urls import url

from clublink.certificates import views


urlpatterns = [
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^$', views.step1, name='home'),
    url(r'^step-1/$', views.step1, name='step1'),
    url(r'^step-2/$', views.Step2View.as_view(), name='step2'),
    url(r'^confirm/$', views.confirm, name='confirm'),
    url(r'^preview/(?P<pk>[0-9]+?)/$', views.preview, name='preview'),
    url(r'^download/(?P<code>[^/]+?)/$', views.download, name='download'),
]
