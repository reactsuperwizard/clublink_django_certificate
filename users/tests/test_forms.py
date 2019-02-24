import pytest

from clublink.users.forms import LoginForm
from clublink.users.tests import UserFactory


@pytest.mark.django_db
class TestLoginForm():
    def test_clean(self):
        UserFactory(username='testuser', password='testpass')
        form = LoginForm({'username': 'testuser', 'password': 'testpass'})
        assert form.is_valid()

    def test_invalid_username(self):
        UserFactory(username='testuser', password='testpass')
        form = LoginForm({'username': 'nottestuser', 'password': 'testpass'})
        assert not form.is_valid()

    def test_invalid_password(self):
        UserFactory(username='testuser', password='testpass')
        form = LoginForm({'username': 'testuser', 'password': 'nottestpass'})
        assert not form.is_valid()
