import re

from urllib.parse import quote_plus
from urllib.request import URLError

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.urls import resolve, Resolver404
from django.shortcuts import redirect
from django.utils import translation
from raven.contrib.django.raven_compat.models import client as raven_client

from clublink.base.clients.ibs import WebResClient
from clublink.base.utils import get_matching_allowed_host, set_multidomain_cookie
from clublink.clubs.models import Club
from clublink.legacy import LEGACY_REDIRECTS
from clublink.users.models import User


class ShortCircuitMiddleware(object):
    """
    Middleware that skips remaining middleware when a view is marked with
    normandy.base.decorators.short_circuit_middlewares
    """
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        try:
            result = resolve(request.path, urlconf=getattr(request, 'urlconf', None))
        except Resolver404:
            pass
        else:
            if getattr(result.func, 'short_circuit_middlewares', False):
                return result.func(request, *result.args, **result.kwargs)
        return self.get_response(request)


class MultiDomainSessionMiddleware(object):
    """
    This is middleware to enable sessions on multidomain web applications.

    This must be included before SessionMiddleware.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)


        if response.cookies:
            # print('\n==================')
            # print(response.cookies)
            # print(request.session.__dict__)
            # print('==================\n')
            # # import pdb; pdb.set_trace();
            # # # import pdb; pdb.set_trace()

            # # The problem with this is that it does NOT actually match half the time.
            domain = get_matching_allowed_host(request.get_host())

            # Modify the session ID cookie
            for key in response.cookies:
                if key == settings.SESSION_COOKIE_NAME:
                    if domain is None and 'domain' in response.cookies[key]:
                        del response.cookies[key]['domain']
                    else:
                        response.cookies[key]['domain'] = domain

        return response


class HostnameRoutingMiddleware(object):
    """This is middleware to enable hostname based URL routing."""
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        for pattern, urlconf in getattr(settings, 'HOSTNAME_URLCONFS', ()):
            if re.search(pattern, request.get_host()):
                request.urlconf = urlconf
                break

        return self.get_response(request)


class ScaffoldingMiddleware(object):
    """This is middleware handles all the request processing magic for setting up a request."""

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        # Check for a legacy redirect

        legacy_redirect = self.legacy_redirect(request)
        if legacy_redirect:
            return redirect(legacy_redirect, permanent=True)

        self.set_languages(request)
        self.set_club(request)
        self.initialize_member_portal(request)

        # Adjust languages for clubs that are not bilingual
        if request.club and not request.club.bilingual:
            request.languages = [settings.LANGUAGE_CODE]

        return self.get_response(request)

    def _get_query_string(self, request, **kwargs):
        params = dict(request.GET)
        params.update(kwargs)
        params_qs = []
        for k in params:
            v = params[k]
            if isinstance(v, list):
                v = v[0]
            params_qs.append('{}={}'.format(k, quote_plus(v)))
        qs = '&'.join(params_qs)
        if qs:
            qs = '?{}'.format(qs)
        return qs

    def _strip_subdomain(self, request):
        protocol = 'https' if request.is_secure() else 'http'
        new_host = '.'.join(request.get_host().split('.')[1:])
        return '{}://{}{}'.format(protocol, new_host, request.path)

    def legacy_redirect(self, request):
        host = request.get_host()

        # Hardcoded redirects
        url = '{}{}'.format(request.get_host(), request.get_full_path())
        for pattern, redirect_url in LEGACY_REDIRECTS:
            if re.search(pattern, url):
                return redirect_url

        # Strip locale from hostname
        for locale, name in settings.LANGUAGES:
            if host.startswith('{}.'.format(locale)):
                return '{}{}'.format(self._strip_subdomain(request),
                                     self._get_query_string(request, lang=locale))

        # Strip www
        if host.startswith('www.'):
            return '{}{}'.format(self._strip_subdomain(request),
                                 self._get_query_string(request))

        # /Default.aspx
        if request.path.lower().startswith('/default.aspx'):
            return '/'

        return False

    def set_languages(self, request):
        request.languages = [l[0] for l in settings.LANGUAGES]

        for pattern, languages in getattr(settings, 'HOSTNAME_LANGUAGES', ()):
            if re.search(pattern, request.get_host()):
                request.languages = languages
                break

    def set_club(self, request):
        request.club = None

        if not hasattr(request, 'urlconf'):
            slug = request.get_host().split('.')[0]
            # domain = '.'.join(request.get_host().split('.')[1:])
            try:
                # site = Site.objects.get(domain=domain)
                request.club = Club.objects.get(slug=slug, site=request.site)
            except Club.DoesNotExist:
                pass
            else:
                request.urlconf = 'clublink.urls.clubs'

    def initialize_member_portal(self, request):
        request.member_portal = False
        member_token = None

        if request.member.is_authenticated and request.club:
            if request.member.option_club:
                request.member_portal = request.club == request.member.option_club
            else:
                request.member_portal = request.club == request.member.home_club

            if request.member_portal:
                if request.member.membership_number:
                    # Members of Florida clubs, member number starts with a "5"
                    if request.member.membership_number.startswith('5'):
                        friendly_name = WebResClient.LINKLINE_ONLINE_US

                    # Full Members of Canadian clubs, member number starts with a "1"
                    else:
                        member_club = request.member.option_club or request.member.home_club

                        players_club_types = [
                            'CHALAD',
                            'CHALAP',
                            'CHAMAD',
                            'CHALUL',
                            'CLASAD',
                            'JUNADV',
                        ]

                        players_card_types = [
                            'CHALL',
                            'CHAMP',
                            'CLASS',
                            'JUNCLA',
                            'JUNIOR',
                        ]

                        is_players_club = member_club and member_club.code == '7200'

                        if is_players_club or request.member.type.id in players_club_types:
                            friendly_name = WebResClient.PLAYERS_CLUB
                        elif request.member.type.id in players_card_types:
                            friendly_name = WebResClient.PLAYERS_CARD
                        else:
                            friendly_name = WebResClient.LINKLINE_ONLINE

                    webres = WebResClient(friendly_name)

                    cache_key = 'webres_master_token_{}'.format(friendly_name)
                    master_token = cache.get(cache_key)

                    if not master_token:
                        try:
                            master_token = webres.get_master_token()
                        except URLError:
                            pass
                        else:
                            cache.set(cache_key, master_token, 86400)

                    cache_key = 'webres_member_token_{}'.format(request.member.membership_number)
                    member_token = cache.get(cache_key)

                    if master_token and not member_token:
                        try:
                            member_token = webres.get_member_token(
                                master_token, request.member.membership_number)
                        except WebResClient.TokenGenerationFailed:
                            raven_client.captureException()
                        except URLError:
                            pass
                        else:
                            cache.set(cache_key, member_token, 3600)

                    if member_token:
                        request.webres_member_token = member_token
                        request.webres_friendly_name = friendly_name


class LocaleMiddleware(object):
    """This is middleware that stores locale selection in a cookie."""

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):

        site_languages = request.languages

        # Get a list of accepted languages
        accepted_langs = request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(',')

        # Set the default language
        default_lang = settings.LANGUAGE_CODE

        # Pick the first valid accepted language
        for l in accepted_langs:
            l = l.split(';')[0].split('-')[0]  # Strip the quality value and country code
            if l in site_languages:
                default_lang = l
                break

        # Set the language
        language = request.GET.get('lang', request.COOKIES.get('lang'))
        if language not in site_languages:
            language = default_lang
        request.LANGUAGE_CODE = language
        translation.activate(language)


        ### TODO: This middleware needs to be rewritten essentially...

        response = self.get_response(request)

        # Set a cookie if a valid language was passed in the URL
        language = request.GET.get('lang')
        if language and language in site_languages:
            set_multidomain_cookie(request, response, 'lang', language)

        return response


class SpoofedUserMiddleware(object):
    """Middleware to handle setting the `member` to be used on the member facing sites."""

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        request.member = request.user

        if 'nospoof' in request.GET and 'spoofed_user_id' in request.session:
            request.session.pop('spoofed_user_id')

        spoofed_user_id = request.GET.get('spoof', request.session.get('spoofed_user_id'))

        if request.user:
            permits = request.user.is_authenticated and request.user.permits('can_impersonate_user')
        else:
            permits = None
        if spoofed_user_id and permits:
            try:
                request.member = User.objects.get(id=spoofed_user_id)

            except User.DoesNotExist:
                print('USER DOESNOT EXIST')

            if 'spoof' in request.GET:
                request.session['spoofed_user_id'] = request.member.id


        request.is_user_spoofed = request.user != request.member

        return self.get_response(request)
