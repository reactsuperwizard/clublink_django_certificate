import pytest

from clublink.users.api.serializers import MemberSerializer, MemberAddressSerializer
from clublink.users.models import User
from clublink.users.tests import AddressFactory, ProfileFactory, UserFactory


@pytest.mark.django_db
class TestUserViewSet(object):
    def test_it_works(self, api_client):
        res = api_client.get('/v1/user/')
        assert res.status_code == 200
        assert len(res.data['results']) == 1


@pytest.mark.django_db
class TestMemberViewSet(object):
    def test_it_works(self, api_client):
        res = api_client.get('/v1/member/')
        assert res.status_code == 200
        assert len(res.data['results']) == 1

    def test_permissions(self, api_client):
        api_client.logout()
        u = UserFactory(password='testpass')
        api_client.login(username=u.username, passwd='testpass')
        res = api_client.get('/v1/member/')
        assert res.status_code == 403

    def test_lookup_field(self, api_client):
        u = UserFactory()
        res = api_client.get('/v1/member/{}/'.format(u.membership_number))
        assert res.status_code == 200
        assert res.data == MemberSerializer(u).data

    def test_create_on_put(self, api_client):
        res = api_client.put('/v1/member/NEW123/', format='json', data={
            'username': 'testing',
            'membership_number': 'NEW123',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@mail.com',
            'profile': {
                'gender': 'M',
            }
        })
        assert res.status_code == 201
        assert res.data['membership_number'] == 'NEW123'
        assert User.objects.filter(membership_number='NEW123').exists()

    def test_update_on_put(self, api_client):
        u = UserFactory()
        ProfileFactory(user=u, subscribe_score=False)

        res = api_client.put('/v1/member/{}/'.format(u.membership_number), format='json', data={
            'username': u.username,
            'membership_number': 'NEW123',
            'email': u.email,
            'profile': {
                'subscribe_score': True,
            },
        })
        assert res.status_code == 200
        assert res.data['membership_number'] == 'NEW123'
        assert res.data['profile']['subscribe_score'] is True

        u.refresh_from_db()
        u.profile.refresh_from_db()
        assert u.membership_number == 'NEW123'
        assert u.profile.subscribe_score


@pytest.mark.django_db
class TestMemberAddressViewSet(object):
    def test_it_works(self, api_client):
        u = UserFactory(membership_number='123')
        res = api_client.get('/v1/member/{}/address/'.format(u.membership_number))
        assert res.status_code == 200
        assert res.data == MemberAddressSerializer(u.addresses, many=True).data

    def test_404_for_invalid_membership_number(self, api_client):
        res = api_client.get('/v1/member/_/address/')
        assert res.status_code == 404

    def test_make_billing_address(self, api_client):
        u = UserFactory()
        a = AddressFactory(user=u)
        res = api_client.post(
            '/v1/member/{}/address/{}/make_billing_address/'.format(u.membership_number, a.type))
        assert res.status_code == 204
        u.profile.refresh_from_db()
        assert u.profile.billing_address == a

    def test_make_mailing_address(self, api_client):
        u = UserFactory()
        a = AddressFactory(user=u)
        res = api_client.post(
            '/v1/member/{}/address/{}/make_mailing_address/'.format(u.membership_number, a.type))
        assert res.status_code == 204
        u.profile.refresh_from_db()
        assert u.profile.mailing_address == a
