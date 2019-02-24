import json

from urllib import request
from urllib.parse import quote_plus

from django.conf import settings
from zeep import Client as ZeepClient
from zeep.helpers import serialize_object

import logging
logger = logging.getLogger(__name__)


def serialized(func):
    def wrapper(*args, **kwargs):
        value = func(*args, **kwargs)
        return serialize_object(value)
    return wrapper


class BaseClient(object):
    wsdl_setting_name = None
    client = None

    class ImproperlyConfigured(Exception):
        pass

    def __init__(self, *args, **kwargs):
        if not self.wsdl_setting_name:
            raise BaseClient.ImproperlyConfigured()
        self.wsdl = kwargs.get('wsdl') or getattr(settings, self.wsdl_setting_name)

    @property
    def wsdl(self):
        return self.client.wsdl

    @wsdl.setter
    def wsdl(self, value):
        self.client = ZeepClient(value)


class WebMemberClient(BaseClient):
    """A wrapper for the IBS SOAP API."""
    wsdl_setting_name = 'IBS_API_WSDL'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get('user') or getattr(settings, 'IBS_API_USER')
        self.password = kwargs.get('password') or getattr(settings, 'IBS_API_PASSWORD')

    @serialized
    def ping(self):
        """Ping the API and confirm credentials work."""
        return self.client.service.AreYouThere(self.user, self.password)

    @serialized
    def get_inventory(self, inventoryNumber, searchType):
        """New endpoint as per Carolyn and IBS."""
        return self.client.service.SearchOnHandRetailInventory(self.user, self.password,
                                               inventoryNumber, searchType)

    @serialized
    def get_fb_departments(self):
        """Get a list of food and beverage departments."""
        result = self.client.service.GetSystemCodeAllFBDepartments(self.user, self.password)
        if result:
            return result['GetSystemCodeAllFBDepartmentsResult']['CodeDescriptionPair']
        return []

    @serialized
    def get_retail_departments(self):
        """Get a list of retail departments."""
        result = self.client.service.GetSystemCodeAllRetailDepartments(self.user, self.password)
        if result:
            return result['GetSystemCodeAllRetailDepartmentsResult']['CodeDescriptionPair']
        return []

    def get_departments(self):
        """Get a list of all the departments."""
        departments = self.get_fb_departments()
        departments += self.get_retail_departments()
        return departments

    @serialized
    def get_tender_methods_for_department(self, department):
        """Get a list of the tender methods for a department."""
        results = self.client.service.GetTenderAllTenderMethodsForDepartment(
            self.user, self.password, department.id)
        return results['GetTenderAllTenderMethodsForDepartmentResult']['TenderData']

    @serialized
    def get_tax_codes_for_department(self, department):
        """Get a list of the tax codes for a department."""
        results = self.client.service.GetSystemCodeAllTaxCodesForDepartment(
            self.user, self.password, department.id)
        return results['GetSystemCodeAllTaxCodesForDepartmentResult']['TaxCodeData']

    @serialized
    def create_ticket(self, batch_xml):
        """Create a new ticket."""

        logger.info(
            'IBS: Create ticket'
        )

        return self.client.service.CreateTickets(self.user, self.password, batch_xml)


class WebResClient(object):
    """A wrapper for the IBS Web Res API"""
    LINKLINE_ONLINE = 'LinkLineOnLine'
    LINKLINE_ONLINE_US = 'LinkLineOnLineUS'
    PLAYERS_CLUB = 'PlayersClub'
    PLAYERS_CARD = 'PlayerCard'

    class TokenGenerationFailed(Exception):
        pass

    def __init__(self, club_friendly_name, **kwargs):
        self.club_friendly_name = club_friendly_name
        self.api_root = kwargs.get('api_root') or getattr(settings, 'IBS_WEBRES_API_ROOT')
        self.user = kwargs.get('user') or getattr(settings, 'IBS_WEBRES_API_USER')
        self.password = kwargs.get('password') or getattr(settings, 'IBS_WEBRES_API_PASSWORD')

    def call(self, endpoint, **kwargs):
        params = ['{}={}'.format(key, quote_plus(kwargs[key])) for key in kwargs]
        url = '{}{}?{}'.format(self.api_root, endpoint, '&'.join(params))
        api_request = request.Request(url, headers={'Accept': 'application/json'})
        response = request.urlopen(api_request)
        return json.loads(response.read().decode())

    def get_master_token(self):
        result = self.call('User/GetNewUserTokenFromLogin', authToken='', userName=self.user,
                           password=self.password, clubFriendlyName=self.club_friendly_name)
        if result.get('IsSuccessStatusCode'):
            return result.get('Value')

    def get_member_token(self, master_token, member_number):
        result = self.call('User/GetNewUserTokenByMemberNumber', authToken='',
                           userToken=master_token, clubFriendlyName=self.club_friendly_name,
                           memberNumber=member_number, memberExtension='000')
        if result.get('IsSuccessStatusCode'):
            return result.get('Value')
        else:
            raise self.TokenGenerationFailed(json.dumps(result))
