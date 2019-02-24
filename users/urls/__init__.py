from django.conf.urls import url

from clublink.users import views


def auth_urlpatterns(kwargs):
    return [
        url(r'^login/$', views.LoginView.as_view(), name='login', kwargs=kwargs),
        url(r'^login/forgot/$', views.ForgotPasswordView.as_view(), name='login.forgot',
            kwargs=kwargs),
        url(r'^login/forgot/success/$', views.ForgotPasswordSuccessView.as_view(),
            name='login.forgot-success', kwargs=kwargs),
        url(r'^login/forgot/failure/$', views.ForgotPasswordFailureView.as_view(),
            name='login.forgot-failure', kwargs=kwargs),
        url(r'^login/challenge/$', views.LoginChallengeView.as_view(),
            name='login.challenge', kwargs=kwargs),
        url(r'^login/challenge/success/$', views.LoginChallengeSuccessView.as_view(),
            name='login.challenge-success', kwargs=kwargs),
        url(r'^login/reset/$', views.ResetPasswordView.as_view(),
            name='login.reset', kwargs=kwargs),
    ]
