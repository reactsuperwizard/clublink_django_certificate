from clublink.base.clients.google import GoogleMapsClient


class TestGoogleMapsClient(object):
    def test_geocode(self, monkeypatch):
        import urllib.request

        def fake_urlopen(url):
            class FakeResponse(object):
                def __init__(self, data):
                    self.data = data

                def read(self):
                    return self.data.encode()

            return FakeResponse('{"success": true}')

        monkeypatch.setattr(urllib.request, 'urlopen', fake_urlopen)

        g = GoogleMapsClient(api_key='FAKE_KEY')
        assert g.geocode('Fake address') == {'success': True}

    def test_geocode_no_api_key(self):
        g = GoogleMapsClient(api_key=None)
        assert g.geocode('Fake address') == {}
