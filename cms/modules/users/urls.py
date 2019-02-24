from django.conf.urls import url

from clublink.cms.modules.users import views


urlpatterns = [
    url(r'^$', views.UsersView.as_view(), name='users.home'),
    url(r'^accounts/$', views.UserAccountsView.as_view(), name='users.accounts'),
    url(r'^accounts/new/$', views.UserAddView.as_view(), name='users.accounts-add'),
    url(r'^accounts/(?P<user_pk>[0-9]+)/edit/$', views.UserEditView.as_view(),
        name='users.accounts-edit'),
    url(r'^accounts/(?P<user_pk>[0-9]+)/delete/$', views.UserDeleteView.as_view(),
        name='users.accounts-delete'),
    url(r'^impersonate/$', views.ImpersonateUserView.as_view(), name='users.impersonate'),
    url(r'^my-account/$', views.MyAccountView.as_view(), name='users.my-account'),
]
