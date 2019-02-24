import pytest

from django.conf import settings
from django.http import Http404
from django.http.response import HttpResponse
from mock import Mock

from clublink.base.middleware import HostnameRoutingMiddleware, MultiDomainSessionMiddleware
from clublink.clubs.tests import ClubFactory


class MiddlewareTestCase(object):
    middleware_class = None
    middleware = None
    request = None

    def get_response(self, request):
        response = HttpResponse()
        return response

    def setup(self):
        self.middleware = self.middleware_class(self.get_response)
        self.request = Mock()


@pytest.mark.django_db
class TestHostnameRoutingMiddleware(MiddlewareTestCase):
    middleware_class = HostnameRoutingMiddleware

    def setup(self):
        super().setup()

        self._languages = settings.LANGUAGES
        settings.LANGUAGES = (
            ('en', 'English'),
            ('fr', 'French'),
        )

        self._hostname_urlconfs = settings.HOSTNAME_URLCONFS
        settings.HOSTNAME_URLCONFS = (
            (r'^alt\.', 'alternate'),
            (r'^other\.', 'other'),
        )

        self._hostname_languages = settings.HOSTNAME_LANGUAGES
        settings.HOSTNAME_LANGUAGES = (
            (r'^other\.', ('en',)),
        )

    def teardown(self):
        settings.LANGUAGES = self._languages
        settings.HOSTNAME_URLCONFS = self._hostname_urlconfs
        settings.HOSTNAME_LANGUAGES = self._hostname_languages

    def test_club(self):
        club = ClubFactory(slug='club')

        del self.request.club
        del self.request.urlconf
        self.request.get_host = lambda: 'club.test.com'

        self.middleware(self.request)

        assert getattr(self.request, 'urlconf') == 'clublink.urls.clubs'
        assert self.request.club == club

    def test_hostname(self):
        del self.request.club
        self.request.get_host = lambda: 'alt.test.com'

        self.middleware(self.request)

        assert self.request.urlconf == 'alternate'
        assert self.request.club is None

    def test_languages(self):
        del self.request.languages
        self.request.get_host = lambda: 'alt.test.com'
        self.middleware(self.request)
        assert self.request.languages == ['en', 'fr']

        self.request.get_host = lambda: 'other.test.com'
        self.middleware(self.request)
        assert self.request.languages == ('en',)

    def test_404(self):
        del self.request.urlconf
        self.request.get_host = lambda: 'nope.test.com'

        with pytest.raises(Http404):
            self.middleware(self.request)


class TestMultiDomainSessionMiddleware(MiddlewareTestCase):
    middleware_class = MultiDomainSessionMiddleware

    def get_response(self, request):
        response = super().get_response(request)
        response.set_cookie('sessionid')
        return response

    def setup(self):
        super().setup()
        self._allowed_hosts = settings.ALLOWED_HOSTS
        settings.ALLOWED_HOSTS = ('my.test.com', '.test.com', 'gc.test.com',)

    def teardown(self):
        settings.ALLOWED_HOSTS = self._allowed_hosts

    def test_domain(self):
        self.request.get_host = lambda: 'test.com'
        response = self.middleware(self.request)
        assert response.cookies['sessionid']['domain'] == '.test.com'

    def test_subdomain(self):
        self.request.get_host = lambda: 'my.test.com'
        response = self.middleware(self.request)
        assert response.cookies['sessionid']['domain'] == 'my.test.com'

    def test_wildcard_subdomain(self):
        self.request.get_host = lambda: 'gc.test.com'
        response = self.middleware(self.request)
        assert response.cookies['sessionid']['domain'] == '.test.com'

    def test_not_in_allowed_hosts(self):
        self.request.get_host = lambda: 'what.com'
        response = self.middleware(self.request)
        assert 'domain' not in response.cookies['sessionid']
