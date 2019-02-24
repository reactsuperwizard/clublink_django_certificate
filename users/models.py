import calendar
import json
import base64
import math

from datetime import datetime
from Crypto.Cipher import AES
from urllib.parse import urlencode, quote_plus
from urllib.request import quote


from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.dispatch import receiver
from django.urls import reverse
from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _

from clublink.base.crypto import AESCipher
from clublink.base.utils import today
from clublink.users.managers import UserManager
from clublink.clubs.models import Club

class UserCategory(models.Model):
    id = models.CharField(max_length=6, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<UserCategory {}>'.format(self.name)


class ClubCorp(models.Model):
    id = models.CharField(max_length=6, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<ClubCorp {}>'.format(self.name)


class UserType(models.Model):
    id = models.CharField(max_length=6, primary_key=True)
    name = models.CharField(max_length=255)
    is_corp = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<UserType {}>'.format(self.name)

class User(AbstractBaseUser, PermissionsMixin):

    STATUSES = (
        ('A', _('Active')),
        ('R', _('Resigned')),
        ('S', _('Suspended')),
    )

    username = models.CharField(max_length=48, unique=True)
    membership_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    employee_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    middle_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(null=True, blank=True)
    is_staff = models.BooleanField(
        'staff status', default=False,
        help_text='Designates whether the user can log into this admin site.')
    category = models.ForeignKey(
        UserCategory,
        null=True,
        blank=True,
        related_name='users',
        on_delete=models.SET_NULL
        )
    clubcorp = models.ForeignKey(
        ClubCorp,
        null=True,
        blank=True,
        related_name='users',
        on_delete=models.SET_NULL
        )
    clubcorp_number = models.CharField(max_length=5, null=True, blank=True)
    customer_id = models.CharField(max_length=15, null=True, blank=True)
    home_club = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        related_name='users',
        on_delete=models.SET_NULL)
    option_club = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        related_name='option_users',
        on_delete=models.SET_NULL
        )
    home_club_alternate_1 = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        related_name='alt1_users',
        on_delete=models.SET_NULL
        )
    home_club_alternate_2 = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        related_name='alt2_users',
        on_delete=models.SET_NULL
        )
    preferred_language = models.CharField(max_length=2, default=settings.LANGUAGE_CODE,
                                          choices=settings.LANGUAGES)
    status = models.CharField(max_length=1, default='A', choices=STATUSES)
    type = models.ForeignKey(
        UserType,
        null=True,
        blank=True,
        related_name='users',
        on_delete=models.SET_NULL
        )
    invited = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = (
        'email',
    )

    class InvalidToken(Exception):
        pass

    class ExpiredToken(InvalidToken):
        pass

    class Meta:
        permissions = (
            ('manage_gift_certificates', 'Can manage Gift Certificates',),
        )

    def __str__(self):
        return self.username

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    @property
    def department_list(self):
        return ', '.join(self.departments.values_list('name', flat=True))

    @property
    def club_list(self):
        return ', '.join(self.clubs.values_list('name', flat=True))
    
    @property
    def can_access_cms(self):
        if hasattr(self, 'permissions'):
            return self.permissions.can_access_cms
        else:
            return False

    @property
    def can_impersonate_user(self):
        if hasattr(self, 'permissions'):
            return self.permissions.can_impersonate_user
        else:
            return False            

    @property
    def __csv_row__(self):
        return [
            self.id,
            self.membership_number,
            self.username,
            self.first_name,
            self.last_name,
            self.email,
            self.is_superuser,
            self.status,
            self.preferred_language,
            self.department_list,
            self.club_list,
            self.can_access_cms,
            self.can_impersonate_user
        ]

    def generate_email(self):
        template = '''
        Good morning {first_name},

        We are pleased to announce the launch of the new {home_club} and ClubLink website.

        The new sites have been built on a fully responsive platform that is easy to navigate. All the familiar tools for managing your account, booking tee times with LinkLine OnLine, accessing the club roster, or signing up for events are very accessible and most importantly, mobile friendly.

        As this is a completely new system, you will need to create a new password to access the member portal. To do so, please click the link below: 
        
        {reset_base}?token={token}

        As a reminder, should you ever forget your password again in the future, you can reset your password at https://clublink.com/login/forgot/.

        Once you have logged in successfully, please familiarize yourself with the new website. We've organized things to be more user friendly based upon feedback over the years with our previous site.

        Here are a few quick tips to navigating your new site:

        Booking a tee time is now easier than ever! On the homepage, click the “Book a Tee Time” button to book tee times with LinkLine OnLine
        To view the Club Calendar, from the homepage click “My Club”
        To view your Member Account Statement, from the homepage click “My Account”
        To opt-in to online statements, under “My Account”, click “My Profile”, and then “Communications”. Check the box next to “Receive annual dues notice via email” and “Receive statement via email”
        If you encounter any issues, please email Member Services at memberservices@clublink.ca. If you need to speak to a Member Services representative, please call 1-800-273-5113.

        Member Services Call Center Hours of Operation 
        Weekdays 8 a.m. – 5:30 p.m. 
        Weekends 8 a.m. – 2 p.m.

        Regards,

        ClubLink Member Services 
        15675 Dufferin Street 
        King City, ON, L7B 1K5 
        1-800-273-5113 
        memberservices@clublink.ca 
        www.clublink.com

        '''.format(
            **{
                'first_name': self.first_name,
                'home_club': self.home_club.name if self.home_club else None,
                'reset_base': 'https://clublink.com/login/reset/',
                'token': quote(self.generate_reset_token())
            }
        )
        return template

    @property
    def option_club_name(self):
        if self.option_club:
            return self.option_club.name

        else:
            return None

    def get_roster_phone(self):
        if self.profile.show_phone:
            return self.profile.show_phone.phone
        else:
            return None

    def get_roster_cell(self):
        if self.profile.show_cell:
            return self.profile.show_cell.cell_phone
        else:
            return None

    def get_roster_email(self):
        if self.profile.show_email:
            return self.profile.show_email.email
        else:
            return None

    @property
    def my_cell_phone(self):
        if self.addresses.exists():
            return self.addresses.first().cell_phone

    @property
    def my_phone(self):
        if self.addresses.exists():
            return self.addresses.first().phone


    @property
    def is_active(self):
        return self.status != 'R'

    @property
    def legacy_renewal_link(self):
        return 'https://clublinkplayersclub.ca/?member={}'.format(
            quote_plus(self.encrypted_membership_number)
        )

    @property
    def renewal_link(self):
        data = {'firstName': self.first_name, 'lastName': self.last_name, 'membershipNumber': self.membership_number, 'email': self.email}
        roundto = math.ceil(len(str(data))/16)
        msg_text = str(data).rjust(roundto*16)
        secret_key = settings.MEMBERSHIP_ENCODE_KEY
        cipher = AES.new(secret_key, AES.MODE_ECB)
        encoded = base64.urlsafe_b64encode(cipher.encrypt(msg_text))
        link = '{}?{}'.format(
            settings.MEMBERSHIP_RENEWAL_URL_BASE,
            urlencode({'ztd': encoded})
            )
        print(link)
        decoded = cipher.decrypt(base64.urlsafe_b64decode(encoded))
        print(decoded)
        return link

    def get_full_name(self):
        return '{} {}'.format(self.first_name, self.last_name).strip()

    def get_short_name(self):
        return self.first_name

    def save(self, *args, **kwargs):
        if self.preferred_language:
            self.preferred_language = self.preferred_language.lower()
        super().save(*args, **kwargs)

    def generate_reset_token(self):
        cipher = AESCipher()
        details = {
            'timestamp': calendar.timegm(datetime.utcnow().utctimetuple()),
            'nonce': self.password,
            'pk': self.pk,
        }
        return cipher.encrypt(json.dumps(details))

    @classmethod
    def parse_reset_token(cls, token):
        cipher = AESCipher()
        try:
            token_json = cipher.decrypt(token)
        except:
            raise cls.InvalidToken()

        try:
            details = json.loads(token_json)
        except json.JSONDecodeError:
            raise cls.InvalidToken()

        now = calendar.timegm(datetime.utcnow().utctimetuple())

        if now - details['timestamp'] > 14 * 24 * 60 * 60:
            raise cls.ExpiredToken()

        try:
            nonce = details['nonce']
        except KeyError:
            raise cls.InvalidToken()

        try:
            user = cls.objects.get(pk=details['pk'], password=nonce)
        except cls.DoesNotExist:
            raise cls.InvalidToken()

        return user

    @property
    def encrypted_membership_number(self):
        if not self.membership_number:
            return None

        cipher = AESCipher()
        return cipher.encrypt(self.membership_number).decode()

    @staticmethod
    def decrypt_membership_number(encrypted):
        cipher = AESCipher()
        return cipher.decrypt(encrypted)

    def permits(self, name, default=False):
        if self.is_superuser:
            return True
        permissions, _ = UserPermissions.objects.get_or_create(user=self)
        return getattr(permissions, name, default)


@receiver(signals.post_save, sender=User)
def user_post_save(sender, instance, **kwargs):
    Profile.objects.get_or_create(user=instance)
    UserPermissions.objects.get_or_create(user=instance)


class Address(models.Model):
    type = models.CharField(max_length=10)

    '''
    We are moving the charfield type to a choicefield.
    Currently, there is no way to properly link things without either a FK or 
    a proper choicefield.
    '''
    HOME = 'H'
    BUSINESS = 'B'
    COTTAGE = 'C'
    OTHER = 'O'
    ADDRESS_TYPE_CHOICES = (
        (HOME, _('Home')),
        (BUSINESS, _('Business')),
        (COTTAGE, _('Cottage')),
        (OTHER, _('Other')),
    )
    _type = models.CharField(
        choices = ADDRESS_TYPE_CHOICES,
        max_length = 1,
        blank=True, null=True
    )

    user = models.ForeignKey(
        User,
        related_name='addresses',
        on_delete=models.PROTECT
        )
    address1 = models.CharField(max_length=30, null=True, blank=True)
    address2 = models.CharField(max_length=30, null=True, blank=True)
    cell_phone = models.CharField(max_length=30, null=True, blank=True)
    city = models.CharField(max_length=30, null=True, blank=True)
    country = models.CharField(max_length=3, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    state = models.CharField(max_length=3, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        unique_together = (('type', 'user'),)


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        related_name='profile',
        on_delete=models.PROTECT
        )
    joined = models.DateField(default=today)
    title = models.CharField(max_length=10, null=True, blank=True)
    dob = models.DateField(null=True)
    gender = models.CharField(max_length=1, null=True, blank=True)
    employer = models.CharField(max_length=80, null=True, blank=True)
    position = models.CharField(max_length=30, null=True, blank=True)
    statement_cycle_id = models.CharField(max_length=2, null=True, blank=True)
    show_in_roster = models.BooleanField(default=False)
    prepaid_cart = models.BooleanField(default=False)
    email_dues_notice = models.BooleanField(default=False)
    email_statement = models.BooleanField(default=False)
    subscribe_score = models.BooleanField(default=False)
    subscribe_clublink_info = models.BooleanField(default=False)
    subscribe_club_info = models.BooleanField(default=False)
    billing_address = models.ForeignKey(
        Address,
        null=True,
        related_name='billing_profile',
        on_delete=models.SET_NULL
        )
    mailing_address = models.ForeignKey(Address,
        null=True,
        related_name='mailing_profile',
        on_delete=models.SET_NULL
        )
    show_email = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        help_text='ForeignKey to know which email to show.',
        blank=True,
        null=True,
        related_name='email_profiles'
        )
    show_phone = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        help_text='ForeignKey to know which phone to show.',
        blank=True,
        null=True,
        related_name='phone_profiles'
        )
    show_cell = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        help_text='ForeignKey to know which cell to show.',
        blank=True,
        null=True,
        related_name='cell_profiles'
        )


class UserPermissions(models.Model):
    user = models.OneToOneField(
        User,
        related_name='permissions',
        on_delete=models.PROTECT
        )
    can_access_cms = models.BooleanField(default=False)
    can_impersonate_user = models.BooleanField(default=False)

sync_order = [
    ClubCorp, UserCategory, UserType,
    User, Profile, UserPermissions
    ]