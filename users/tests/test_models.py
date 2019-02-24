import pytest

from django.db import IntegrityError

from clublink.users.models import User
from clublink.users.tests import UserFactory, UserCategoryFactory


@pytest.mark.django_db
class TestUser(object):
    def test_null_membership_number(self):
        UserFactory(membership_number=None)
        assert User.objects.count() == 1

        UserFactory(membership_number=None)
        assert User.objects.count() == 2

    def test_membership_number_unique(self):
        UserFactory(membership_number='ABC123')
        with pytest.raises(IntegrityError):
            UserFactory(membership_number='ABC123')

    def test_delete_user_category(self):
        category = UserCategoryFactory()
        user = UserFactory(category=category)
        category.delete()
        assert User.objects.filter(pk=user.pk).exists()
