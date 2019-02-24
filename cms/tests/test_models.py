import pytest

from clublink.cms.tests import ClubPageFactory


@pytest.mark.django_db
class TestClubPage(object):
    def test_full_path_on_save(self):
        p1 = ClubPageFactory(slug='the-slug')
        assert p1.full_path == 'the-slug'

        p2 = ClubPageFactory(slug='child', parent=p1)
        assert p2.full_path == 'the-slug/child'

    def test_full_path_update(self):
        p1 = ClubPageFactory()
        p1.slug = 'parent'
        p1.save()
        assert p1.full_path == 'parent'

        p2 = ClubPageFactory(slug='child', parent=p1)
        p1.slug = 'the-parent'
        p1.save()
        assert p1.full_path == 'the-parent'
        p2.refresh_from_db()
        assert p2.full_path == 'the-parent/child'

        p2.slug = 'the-child'
        p2.save()
        assert p2.full_path == 'the-parent/the-child'
