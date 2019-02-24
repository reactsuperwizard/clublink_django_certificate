import factory

from factory import fuzzy

from clublink.base.tests import FuzzyUnicode
from clublink.clubs.tests import ClubFactory
from clublink.cms.models import ClubPage


class ClubPageFactory(factory.DjangoModelFactory):
    name_en = FuzzyUnicode()
    slug = fuzzy.FuzzyText()
    club = factory.SubFactory(ClubFactory)

    class Meta:
        model = ClubPage
