import pytest

from clublink.base.tests import Whatever
from clublink.users.api.serializers import UserSerializer
from clublink.users.tests import UserFactory


@pytest.mark.django_db
class TestUserSerializer(object):
    def test_it_works(self):
        u = UserFactory()
        serializer = UserSerializer(u)

        assert serializer.data == {
            'id': u.id,
            'membership_number': u.membership_number,
            'username': u.username,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'is_active': u.is_active,
            'category': u.category.id if u.category else None,
            'clubcorp': u.clubcorp.id if u.clubcorp else None,
            'clubcorp_number': u.clubcorp_number,
            'customer_id': u.customer_id,
            'home_club': u.home_club.id if u.home_club else None,
            'home_club_alternate_1':
                u.home_club_alternate_1.id if u.home_club_alternate_1 else None,
            'home_club_alternate_2':
                u.home_club_alternate_2.id if u.home_club_alternate_2 else None,
            'is_staff': u.is_staff,
            'middle_name': u.middle_name,
            'option_club': u.option_club.id if u.option_club else None,
            'preferred_language': u.preferred_language,
            'status': u.status,
            'type': u.type.id if u.type else None,
            'profile': {
                'joined': Whatever(),
                'title': u.profile.title,
                'dob': Whatever(),
                'gender': u.profile.gender,
                'employer': u.profile.employer,
                'position': u.profile.position,
                'statement_cycle_id': u.profile.statement_cycle_id,
                'show_in_roster': u.profile.show_in_roster,
                'prepaid_cart': u.profile.prepaid_cart,
                'email_dues_notice': u.profile.email_dues_notice,
                'email_statement': u.profile.email_statement,
                'subscribe_score': u.profile.subscribe_score,
                'subscribe_clublink_info': u.profile.subscribe_clublink_info,
                'subscribe_club_info': u.profile.subscribe_club_info,
            }
        }
