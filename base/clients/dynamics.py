import numbers

import pymssql

from django.conf import settings


def ibool(value, null=False):
    if null and value is None:
        return None
    return int(bool(value))


class DynamicsClient(object):
    connection = None

    class ClientError(Exception):
        code = None

        def __init__(self, *args, **kwargs):
            if not self.code:
                self.code = kwargs.pop('code', None)
            super().__init__(*args, **kwargs)

    class InternalMemberUpdatePending(ClientError):
        code = 80

    class InvalidMember(ClientError):
        code = 81

    class InvalidBillingAddress(ClientError):
        code = 82

    class InvalidMailingAddress(ClientError):
        code = 83

    class InvalidLanguage(ClientError):
        code = 84

    def raise_exception_by_code(self, code):
        if code == 80:
            raise self.InternalMemberUpdatePending()
        elif code == 81:
            raise self.InvalidMember()
        elif code == 82:
            raise self.InvalidBillingAddress()
        elif code == 83:
            raise self.InvalidMailingAddress()
        elif code == 84:
            raise self.InvalidLanguage()
        elif code != 0:
            raise self.ClientError(code=code)

    def __init__(self, **kwargs):
        self._host = kwargs.get('host', getattr(settings, 'DYNAMICS_HOST'))
        self._user = kwargs.get('user', getattr(settings, 'DYNAMICS_USER'))
        self._password = kwargs.get('password', getattr(settings, 'DYNAMICS_PASSWORD'))
        self._database = kwargs.get('database', getattr(settings, 'DYNAMICS_DATABASE'))
        self.connect()

    def connect(self):
        self.connection = pymssql.connect(self.host, self.user, self.password, self.database)

    def disconnect(self):
        self.connection.close()

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        self._host = value
        self.connect()

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
        self.connect()

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value
        self.connect()

    @property
    def database(self):
        return self._database

    @database.setter
    def database(self, value):
        self._database = value
        self.connect()

    def execute(self, procedure_name, **kwargs):
        assignments = []
        params = []

        for key in kwargs:
            value = kwargs[key]
            params.append(value)

            assignment = '@{}='.format(key)
            assignment += '%d' if isinstance(value, numbers.Number) else '%s'
            assignments.append(assignment)

        sql = 'EXEC {} {}'.format(procedure_name, ', '.join(assignments))

        cursor = self.connection.cursor()
        cursor.execute(sql, tuple(params))
        response = cursor.fetchall()
        self.connection.commit()

        return response

    def update_member(self, member_id, billing_id=None, mailing_id=None, employer=None,
                      position=None, preferred_language=None, show_in_roster=None,
                      email_dues_notice=None, email_statement=None, subscribe_score=None,
                      subscribe_clublink_info=None, subscribe_club_info=None, email_address=None):
        response = self.execute('xpIMUpdateMember', **{
            'MemberID': member_id,
            'BillingID': billing_id,
            'MailingID': mailing_id,
            'Employer': employer,
            'Position': position,
            'PreferredLanguage': preferred_language,
            'ShowInRoster': ibool(show_in_roster, null=True),
            'EmailDuesNotice': ibool(email_dues_notice, null=True),
            'EmailStatement': ibool(email_statement, null=True),
            'SubscribeScore': ibool(subscribe_score, null=True),
            'SubscribeClublinkInfo': ibool(subscribe_clublink_info, null=True),
            'SubscribeClubInfo': ibool(subscribe_club_info, null=True),
            'EmailAddr': email_address,
        })

        self.raise_exception_by_code(response[0][0])

    def update_member_address(self, member_id, type, address1, address2, cell_phone, city,
                              country, phone, state, postal_code):
        response = self.execute('xpIMUpdateMemberAddr', **{
            'MemberID': member_id,
            'Type': type,
            'Address1': address1,
            'Address2': address2,
            'CellPhone': cell_phone,
            'City': city,
            'Country': country,
            'Phone': phone,
            'State': state,
            'PostalCode': postal_code,
        })

        self.raise_exception_by_code(response[0][0])

    def get_account_summary(self, member_id):
        response = self.execute('xpIMSelectAccountSummary', **{
            'MemberID': member_id,
        })

        if not response:
            return {}

        data = response[0]

        return {
            'member_id': data[0],
            'name': data[1],
            'category': data[2],
            'house_balance': data[3],
            'annual_dues_balance': data[4],
            'membership_fee_balance': data[5],
            'unspent_minimum_balance': data[6],
            'reward_balance': data[7],
        }

    def get_linked_members(self, member_id):
        response = self.execute('xpIMSelectLinkedMembers', **{
            'MemberID': member_id,
        })

        if not response:
            return []

        data = []

        for row in response:
            data.append({
                'member_id': row[0],
                'name': row[1],
                'category': row[2],
            })

        return data
