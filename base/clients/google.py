import json

from urllib import request
from urllib.parse import quote_plus as quote_plus

from django.conf import settings


def api_key_or_default(default=None):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if not self.api_key:
                return default
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


class GoogleMapsClient(object):
    def __init__(self, api_key=None):
        django_gmaps_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        self.api_key = django_gmaps_api_key if api_key is None else api_key

    @api_key_or_default(default={})
    def geocode(self, address):
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        url += '?address={}&key={}'.format(quote_plus(address.encode()),
                                           quote_plus(self.api_key.encode()))
        response = request.urlopen(url)
        return json.loads(response.read().decode())

    def get_lat_lng(self, address):
        data = self.geocode(address)

        lat = None
        lng = None

        if 'results' in data and len(data['results']):
            result = data['results'][0]
            geometry = result.get('geometry', {})
            location = geometry.get('location', {})
            lat = location.get('lat', None)
            lng = location.get('lng', None)

        return lat, lng
