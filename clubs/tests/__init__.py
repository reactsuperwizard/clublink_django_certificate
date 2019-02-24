import string

import factory

from factory import fuzzy

from clublink.base.tests import FuzzyUnicode
from clublink.clubs.models import Club, Department


class ClubFactory(factory.DjangoModelFactory):
    name = FuzzyUnicode()
    address = factory.Faker('address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    code = fuzzy.FuzzyText(length=4, chars=string.ascii_uppercase + string.digits)
    slug = fuzzy.FuzzyText(length=24)

    class Meta:
        model = Club


class DepartmentFactory(factory.DjangoModelFactory):
    id = factory.Faker('uuid4')
    name = FuzzyUnicode()
    number = fuzzy.FuzzyInteger(low=1, high=99)

    class Meta:
        model = Department
