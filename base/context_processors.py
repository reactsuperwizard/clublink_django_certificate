from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.db.models import Q

from clublink.clubs.models import Club
from clublink.cms.models import CorpAdvertisement, CorpPage


def globals(request):
    try:
        language = request.LANGUAGE_CODE
    except:
        language = 'en'
    corp_ads = CorpAdvertisement.objects.filter(site=get_current_site(request))
    if 'en' not in language:
        corp_ads = corp_ads.filter(language=language)
    
    try:
        all_clubs = Club.objects.filter(site=request.site).exclude(Q(slug=None) | Q(is_resort=True) | Q(slug=''))
        corp_pages = CorpPage.objects.filter(parent=None, site=get_current_site(request))
    except:
        all_clubs = None
        corp_pages = None

    return {
        'settings': settings,
        'all_clubs': all_clubs,
        'corp_advertisements': corp_ads,
        'corp_pages': corp_pages,
        'language': language,
        'site': request.site
    }
