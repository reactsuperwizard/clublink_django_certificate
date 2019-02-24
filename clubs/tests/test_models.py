import pytest

from clublink.clubs.tests import ClubFactory


GEOCODE_DATA = {
    'results': [
        {
            'address_components': [
                {
                    'long_name': '1600',
                    'short_name': '1600',
                    'types': ['street_number']
                },
                {
                    'long_name': 'Amphitheatre Pkwy',
                    'short_name': 'Amphitheatre Pkwy',
                    'types': ['route']
                },
                {
                    'long_name': 'Mountain View',
                    'short_name': 'Mountain View',
                    'types': ['locality', 'political']
                },
                {
                    'long_name': 'Santa Clara County',
                    'short_name': 'Santa Clara County',
                    'types': ['administrative_area_level_2', 'political']
                },
                {
                    'long_name': 'California',
                    'short_name': 'CA',
                    'types': ['administrative_area_level_1', 'political']
                },
                {
                    'long_name': 'United States',
                    'short_name': 'US',
                    'types': ['country', 'political']
                },
                {
                    'long_name': '94043',
                    'short_name': '94043',
                    'types': ['postal_code']
                }
            ],
            'formatted_address': '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
            'geometry': {
                'location': {
                    'lat': 37.4224764,
                    'lng': -122.0842499
                },
                'location_type': 'ROOFTOP',
                'viewport': {
                    'northeast': {
                        'lat': 37.4238253802915,
                        'lng': -122.0829009197085
                    },
                    'southwest': {
                        'lat': 37.4211274197085,
                        'lng': -122.0855988802915
                    }
                }
            },
            'place_id': 'ChIJ2eUgeAK6j4ARbn5u_wAGqWA',
            'types': ['street_address']
        }
    ],
    'status': 'OK'
}


@pytest.mark.django_db
class TestClub(object):
    def test_geocode_on_save(self, monkeypatch):
        c = ClubFactory(city='Hamilton', state='ON')
        assert c.latitude is ''
        assert c.longitude is ''

        # Mock MapboxClient geocode method
        from clublink.base.clients.google import GoogleMapsClient
        monkeypatch.setattr(GoogleMapsClient, 'geocode', lambda x, y: GEOCODE_DATA)

        # Check that the geocode method is not called when a location field doesn't change
        c.slug = 'testing'
        c.save()
        c.refresh_from_db()
        assert c.slug == 'testing'
        assert c.latitude is ''
        assert c.longitude is ''

        # Check that it is correctly geocoded
        c.city = 'Toronto'
        c.save()
        c.refresh_from_db()
        assert c.latitude == '37.4224764'
        assert c.longitude == '-122.0842499'
