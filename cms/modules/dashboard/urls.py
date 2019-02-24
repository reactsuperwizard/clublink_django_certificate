from django.conf.urls import url

from clublink.cms.modules.dashboard import views


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^users/$', views.UserListView.as_view(), name='users'),
    url(r'^clubs/$', views.ClubListView.as_view(), name='clubs'),
    url(r'^departments/$', views.DepartmentListView.as_view(), name='departments'),
]
