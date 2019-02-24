from datetime import date

import factory

from factory import fuzzy

from clublink.base.tests import FuzzyUnicode
from clublink.clubs.tests import ClubFactory
from clublink.users.models import Address, ClubCorp, Profile, User, UserCategory, UserType


class ClubCorpFactory(factory.DjangoModelFactory):
    id = fuzzy.FuzzyText(length=6)
    name = FuzzyUnicode()

    class Meta:
        model = ClubCorp


class UserCategoryFactory(factory.DjangoModelFactory):
    id = fuzzy.FuzzyText(length=6)
    name = FuzzyUnicode()

    class Meta:
        model = UserCategory


class UserTypeFactory(factory.DjangoModelFactory):
    id = fuzzy.FuzzyText(length=6)
    name = FuzzyUnicode()

    class Meta:
        model = UserType


class UserFactory(factory.DjangoModelFactory):
    username = FuzzyUnicode()
    password = factory.PostGenerationMethodCall('set_password', 'testpass')
    email = factory.Faker('email')
    membership_number = fuzzy.FuzzyText(length=15)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    middle_name = factory.Faker('first_name')
    category = factory.SubFactory(UserCategoryFactory)
    clubcorp = factory.SubFactory(ClubCorpFactory)
    clubcorp_number = fuzzy.FuzzyText(length=5)
    customer_id = membership_number
    home_club = factory.SubFactory(ClubFactory)
    type = factory.SubFactory(UserTypeFactory)

    class Meta:
        model = User

    @factory.post_generation
    def profile(self, created, extracted, **kwargs):
        if extracted or extracted is None:
            ProfileFactory(user=self)


class AddressFactory(factory.DjangoModelFactory):
    type = fuzzy.FuzzyText(length=10)
    user = factory.SubFactory(UserFactory)
    address1 = factory.Faker('street_address')
    cell_phone = factory.Faker('phone_number')
    city = factory.Faker('city')
    country = factory.Faker('country_code')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    state = factory.Faker('state_abbr')
    postal_code = factory.Faker('postalcode')

    class Meta:
        model = Address


class ProfileFactory(factory.DjangoModelFactory):
    user = factory.SubFactory(UserFactory, profile=False)
    title = factory.Faker('prefix')
    dob = fuzzy.FuzzyDate(start_date=date(1960, 1, 1), end_date=date.today())
    gender = 'M'
    statement_cycle_id = fuzzy.FuzzyText(length=2)

    class Meta:
        model = Profile
        django_get_or_create = ('user',)

    @factory.post_generation
    def billing_address(self, created, extracted, **kwargs):
        if extracted is None:
            AddressFactory(user=self.user)
        elif extracted:
            self.billing_address = extracted
            self.save()

    @factory.post_generation
    def mailing_address(self, created, extracted, **kwargs):
        if extracted is None:
            AddressFactory(user=self.user)
        elif extracted:
            self.mailing_address = extracted
            self.save()
