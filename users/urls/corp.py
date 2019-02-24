from clublink.users.urls import auth_urlpatterns


auth_kwargs = {
    'base_template': 'corp/login/base.jinja',
}

urlpatterns = auth_urlpatterns(auth_kwargs)
