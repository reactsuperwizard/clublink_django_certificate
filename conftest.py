import pytest

from django.conf import settings
from django.test.client import Client
from rest_framework.test import APIClient

from clublink.users.tests import ProfileFactory


@pytest.fixture(scope='session')
def django_db_modify_db_settings():
    settings.DATABASES['default']['TEST'].update(CHARSET='utf8', COLLATION='utf8_general_ci')


@pytest.fixture
def gc_client():
    profile = ProfileFactory()
    user = profile.user
    user.set_password('testpass')
    user.is_staff = True
    user.is_superuser = True
    user.save()

    client = Client(HTTP_HOST='gc.testserver')
    client.login(username=user.username, password='testpass')
    return client


@pytest.fixture
def api_client():
    """Fixture to provide a DRF API client."""
    profile = ProfileFactory()
    user = profile.user
    user.set_password('testpass')
    user.is_staff = True
    user.is_superuser = True
    user.save()

    client = APIClient(HTTP_HOST='api.testserver')
    client.force_authenticate(user=user)
    return client
