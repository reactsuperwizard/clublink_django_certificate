import pytest

from django.conf import settings

from clublink.certificates.tests import DepartmentFactory, EmailSignatureFactory
from clublink.users.tests import UserFactory


def generate_valid_step1_data():
    d = DepartmentFactory()
    s = EmailSignatureFactory()
    return {
        'language': 'en',
        'recipient_name': 'John',
        'recipient_email': 'jdoe@test.com',
        'email_signature': str(s.pk),
        'department': str(d.pk),
        'account_number': settings.DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER,
    }


@pytest.mark.django_db
class TestLogin(object):
    def test_it_works(self, gc_client):
        gc_client.logout()
        res = gc_client.get('/login/')
        assert res.status_code == 200

    def test_login_redirects_for_authed_user(self, gc_client):
        res = gc_client.get('/login/')
        assert res.status_code == 302
        assert res.url == '/'

    def test_logging_in(self, gc_client):
        gc_client.logout()
        u = UserFactory(password='testpass')
        res = gc_client.post('/login/?next=/step-1/', data={'username': u.username,
                                                            'password': 'testpass'})
        assert res.status_code == 302
        assert res.url == '/step-1/'

        res = gc_client.get('/login/')
        assert res.status_code == 302

    def test_login_failed(self, gc_client):
        gc_client.logout()
        u = UserFactory(password='testpass')
        res = gc_client.post('/login/', data={'username': u.username, 'password': 'wrong'})
        assert res.status_code == 200
        assert 'Invalid username or password.' in res.content.decode()


@pytest.mark.django_db
class TestLogout(object):
    def test_it_works(self, gc_client):
        res = gc_client.get('/logout/')
        assert res.status_code == 302
        assert res.url == '/login/'

        res = gc_client.get('/login/')
        assert res.status_code == 200


@pytest.mark.django_db
class TestStep1(object):
    def test_it_works(self, gc_client):
        res = gc_client.get('/step-1/')
        assert res.status_code == 200

    def test_requires_login(self, gc_client):
        gc_client.logout()
        res = gc_client.get('/step-1/')
        assert res.status_code == 302

    def test_invalid_data(self, gc_client):
        res = gc_client.post('/step-1/')
        assert res.status_code == 200
        assert 'errorlist' in res.content.decode()

    def test_form_is_populated_from_session(self, gc_client):
        session = gc_client.session
        session['gc_step1_data'] = {'account_number': '123456'}
        session.save()

        res = gc_client.get('/step-1/')
        assert res.status_code == 200
        assert 'value="123456"' in res.content.decode()

    def test_valid_data(self, gc_client):
        data = generate_valid_step1_data()
        res = gc_client.post('/step-1/', data=data)
        assert res.status_code == 302
        assert res.url == '/step-2/'
        assert gc_client.session['gc_step1_data'] == data


@pytest.mark.django_db
class TestStep2(object):
    @pytest.fixture(autouse=True)
    def setup_method(self, gc_client):
        self.client = gc_client
        session = self.client.session
        session['gc_step1_data'] = generate_valid_step1_data()
        session.save()

    def test_it_works(self):
        res = self.client.get('/step-2/')
        assert res.status_code == 200
        assert len(self.client.session['gc_step2_data']) == 1

    def test_validate_step1_data(self):
        session = self.client.session
        del session['gc_step1_data']
        session.save()

        res = self.client.get('/step-2/')
        assert res.status_code == 302
        assert res.url == '/step-1/'

        res = self.client.get('/step-1/')
        assert res.status_code == 200
        assert 'You must complete this step before proceeding.' in res.content.decode()

    def test_form_is_populated_from_session(self):
        session = self.client.session
        session['gc_step2_data'] = [('1', {'expiry_date': '12/12/2020'})]
        session.save()

        res = self.client.get('/step-2/')
        assert res.status_code == 200
        assert 'value="12/12/2020"' in res.content.decode()

    def test_add_form(self):
        session = self.client.session
        session['gc_step2_data'] = [('1', {'expiry_date': '12/12/2020'})]
        session.save()

        res = self.client.post('/step-2/', data={'add': '1', 'gc1-expiry_date': '12/12/2020'})
        assert res.status_code == 302
        assert res.url.startswith('/step-2/#gc-')

        res = self.client.get('/step-2/')
        assert 'Gift Certificate #2' in res.content.decode()
        assert len(self.client.session['gc_step2_data']) == 2
        assert self.client.session['gc_step2_data'][0][1] == {'expiry_date': '12/12/2020'}
        assert self.client.session['gc_step2_data'][1][1] == {}

        res = self.client.post('/step-2/', follow=True,
                               data={'add': '1', 'gc1-expiry_date': '20/12/2020'})
        assert res.status_code == 200
        assert 'Gift Certificate #3' in res.content.decode()
        assert len(self.client.session['gc_step2_data']) == 3
        assert self.client.session['gc_step2_data'][0][1] == {'expiry_date': '20/12/2020'}
        assert self.client.session['gc_step2_data'][1][1] == {}
        assert self.client.session['gc_step2_data'][2][1] == {}

    def test_duplicate_form(self):
        session = self.client.session
        session['gc_step2_data'] = [('1', {'expiry_date': '12/12/2020'})]
        session.save()

        res = self.client.post('/step-2/', data={'duplicate': '1',
                                                 'gc1-expiry_date': '12/12/2020'})
        assert res.status_code == 302
        assert res.url.startswith('/step-2/#gc-')

        res = self.client.get('/step-2/')
        assert 'Gift Certificate #2' in res.content.decode()
        assert len(self.client.session['gc_step2_data']) == 2
        assert self.client.session['gc_step2_data'][0][1] == {'expiry_date': '12/12/2020'}
        assert self.client.session['gc_step2_data'][1][1] == {'expiry_date': '12/12/2020'}

        res = self.client.post('/step-2/', follow=True,
                               data={'duplicate': '1', 'gc1-expiry_date': '20/12/2020'})
        assert res.status_code == 200
        assert 'Gift Certificate #3' in res.content.decode()
        assert len(self.client.session['gc_step2_data']) == 3
        assert self.client.session['gc_step2_data'][0][1] == {'expiry_date': '20/12/2020'}
        assert self.client.session['gc_step2_data'][1][1] == {}
        assert self.client.session['gc_step2_data'][2][1] == {'expiry_date': '20/12/2020'}

    def test_delete_form(self):
        session = self.client.session
        session['gc_step2_data'] = [('1', {}), ('2', {})]
        session.save()

        res = self.client.post('/step-2/', data={'delete': '1'})
        assert res.status_code == 302
        assert res.url.startswith('/step-2/#gc-')

        res = self.client.get('/step-2/')
        assert res.status_code == 200
        assert 'Gift Certificate #2' not in res.content.decode()
        assert len(self.client.session['gc_step2_data']) == 1
        assert self.client.session['gc_step2_data'][0][0] == '2'

        res = self.client.post('/step-2/', follow=True, data={'delete': '2'})
        assert res.status_code == 200
        assert 'Gift Certificate #1' in res.content.decode()
        assert 'You must have at least one certificate.' in res.content.decode()
        assert len(self.client.session['gc_step2_data']) == 1
        assert self.client.session['gc_step2_data'][0][0] == '2'
