import pytest

from clublink.clubs.models import Club, Department
from clublink.clubs.tests import ClubFactory, DepartmentFactory
from clublink.users.tests import UserFactory


@pytest.mark.django_db
class TestClubManager():
    def test_objects_for_user(self):
        c1 = ClubFactory()
        ClubFactory()
        u = UserFactory()
        c1.admins.add(u)
        clubs = Club.objects.for_user(u)
        assert clubs.count() == 1
        assert list(clubs) == [c1]

        u = UserFactory()
        clubs = Club.objects.for_user(u)
        assert clubs.count() == 0

    def test_objects_for_department_admin(self):
        c = ClubFactory()
        d = DepartmentFactory()
        d.clubs.add(c)
        u = UserFactory()
        d.admins.add(u)
        clubs = Club.objects.for_user(u)
        assert clubs.count() == 1
        assert list(clubs) == [c]

    def test_objects_for_super_user(self):
        c1 = ClubFactory()
        ClubFactory()
        u = UserFactory(is_superuser=True)
        c1.admins.add(u)
        clubs = Club.objects.for_user(u)
        assert clubs.count() == Club.objects.all().count()


@pytest.mark.django_db
class TestDepartmentManager():
    def test_objects_for_user(self):
        d1 = DepartmentFactory()
        DepartmentFactory()
        u = UserFactory()
        d1.admins.add(u)
        departments = Department.objects.for_user(u)
        assert departments.count() == 1
        assert list(departments) == [d1]

        u = UserFactory()
        departments = Department.objects.for_user(u)
        assert departments.count() == 0

    def test_objects_for_super_user(self):
        d1 = DepartmentFactory()
        DepartmentFactory()
        u = UserFactory(is_superuser=True)
        d1.admins.add(u)
        departments = Department.objects.for_user(u)
        assert departments.count() == Department.objects.all().count()
