import string

from datetime import date

import factory

from factory import fuzzy

from clublink.base.tests import FuzzyUnicode
from clublink.certificates.models import Certificate, CertificateType, EmailSignature
from clublink.clubs.tests import ClubFactory, DepartmentFactory
from clublink.users.tests import UserFactory


class CertificateTypeFactory(factory.DjangoModelFactory):
    name = FuzzyUnicode()
    guid = factory.Faker('uuid4')
    code = fuzzy.FuzzyInteger(low=10000)
    certificate_code = fuzzy.FuzzyText(length=3, chars=string.ascii_uppercase + string.digits)

    class Meta:
        model = CertificateType


class CertificateFactory(factory.DjangoModelFactory):
    creator = factory.SubFactory(UserFactory)
    department = factory.SubFactory(DepartmentFactory)
    membership_number = fuzzy.FuzzyText(chars=string.digits)
    member_name = factory.Faker('name')
    recipient_name = factory.Faker('name')
    recipient_email = factory.Faker('email')
    email_signature = fuzzy.FuzzyText()
    type = factory.SubFactory(CertificateTypeFactory)
    club = factory.SubFactory(ClubFactory)
    player_count = fuzzy.FuzzyInteger(low=1, high=4)
    power_cart = Certificate.POWER_CART_NOT_INCLUDED
    expiry_date = fuzzy.FuzzyDate(start_date=date.today())

    class Meta:
        model = Certificate


class EmailSignatureFactory(factory.DjangoModelFactory):
    name = FuzzyUnicode()
    text = fuzzy.FuzzyText()
    plaintext = fuzzy.FuzzyText()

    class Meta:
        model = EmailSignature
