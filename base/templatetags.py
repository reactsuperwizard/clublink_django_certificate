from urllib.parse import urljoin

from django.conf import settings
from django.shortcuts import reverse
from django.utils.http import urlquote_plus
from django_jinja import library


@library.global_function
@library.render_with('stubs/csrf.jinja')
def csrf_input(token):
    return {
        'csrf_token': token,
    }


@library.global_function()
def curr_url(request, **kwargs):
    qs_params = dict(request.GET)
    qs_params.update(kwargs)

    qs = []
    for k in qs_params:
        v = qs_params[k]

        if isinstance(v, list):
            v = v[0]

        if v is not None:
            qs.append('{}={}'.format(k, quote_plus(v)))

    qs = '&'.join(qs)

    if qs:
        return '{}?{}'.format(request.path, qs)
    else:
        return request.path


@library.global_function()
def club_url(club, viewname, request=None, currentsite=None, destinationsite=None, args=None, kwargs=None):

    # What we're doing here is isolating the path from the domain, since they want to be able to access
    # the same clubs from either admin sites.  

    url = reverse(viewname, urlconf='clublink.urls.clubs', args=args, kwargs=kwargs)
    path = url if url is not '/' else None

    if currentsite and destinationsite:
        baseurl = settings.CLUB_SITE_URL.replace(currentsite.domain, destinationsite.domain)
    elif request:
        baseurl = settings.CLUB_SITE_URL.replace(request.site.domain, club.site.domain)
    else:
        baseurl = settings.CLUB_SITE_URL

    return urljoin(baseurl.replace("{slug}", club.slug), path)


@library.global_function()
def corp_url(viewname, currentsite=None, destinationsite=None, args=None, kwargs=None):

    url = reverse(viewname, urlconf='clublink.urls.corp', args=args, kwargs=kwargs)
    path = url if url is not '/' else None

    if currentsite and destinationsite:
        baseurl = settings.CORP_SITE_URL.replace(currentsite.domain, destinationsite.domain)
    else:
        baseurl = settings.CORP_SITE_URL
    return urljoin(baseurl, path)


@library.global_function()
def gc_url(viewname, args=None, kwargs=None):
    url = reverse(viewname, urlconf='clublink.urls.gc', args=args, kwargs=kwargs)
    return urljoin(getattr(settings, 'GIFT_CERTIFICATE_SITE_URL'), url)


@library.global_function()
def admin_url(viewname, args=None, kwargs=None):
    url = reverse(viewname, urlconf='clublink.urls.admin', args=args, kwargs=kwargs)
    return urljoin(getattr(settings, 'ADMIN_SITE_URL'), url)


@library.filter()
def model_attr(model, attr_name):
    attr = getattr(model, attr_name)
    value = attr() if callable(attr) else attr
    return '' if value is None else value


@library.global_function(name='len')
def jinja_len(obj):
    return len(obj)


@library.filter()
def quote_plus(url, safe=''):
    unicode_url = u'%s' % url
    return urlquote_plus(unicode_url, safe)
