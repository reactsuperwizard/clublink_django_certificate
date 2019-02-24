import base64

from random import randint

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from clublink.base.utils import RandomizedUploadPath
from clublink.certificates.generators import (
    AG30CertificateGenerator,
    DefaultCertificateGenerator,
    Prestige50CertificateGenerator,
)
from clublink.clubs.models import Club, Department
from clublink.users.models import User

class CertificateAd(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to=RandomizedUploadPath('certificate_ads'))
    image_fr = models.ImageField(upload_to=RandomizedUploadPath('certificate_ads_fr'), null=True,
                                 blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<CertificateAd: {}>'.format(self.name)


class EmailSignature(models.Model):
    name = models.CharField(max_length=255)
    text = models.TextField()
    text_fr = models.TextField(blank=True)
    plaintext = models.TextField()
    plaintext_fr = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        related_name='signatures',
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<EmailSignature: {}>'.format(self.name)


class CertificateBatch(models.Model):
    created = models.DateTimeField(default=timezone.now)
    creator = models.ForeignKey(
        User,
        related_name='certificate_batches',
        on_delete=models.PROTECT
        )
    department = models.ForeignKey(
        Department,
        related_name='certificate_batches',
        on_delete=models.PROTECT
        )
    account_number = models.CharField(max_length=48, null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=2, choices=settings.LANGUAGES,
                                default=settings.LANGUAGE_CODE)
    recipient_name = models.CharField(max_length=255)
    recipient_email = models.EmailField()
    email_signature = models.ForeignKey(
        EmailSignature,
        null=True,
        on_delete=models.PROTECT
        )

    @property
    def download_code(self):
        code = '{}:{}'.format(self.pk, self.recipient_email)
        return base64.urlsafe_b64encode(code.encode()).decode()


class Certificate(models.Model):
    POWER_CART_NOT_INCLUDED = 0
    MANDATORY_POWER_CART_NOT_INCLUDED = 1
    POWER_CART_INCLUDED = 2

    POWER_CART_CHOICES = (
        (POWER_CART_NOT_INCLUDED, _('Power cart not included')),
        (MANDATORY_POWER_CART_NOT_INCLUDED, _('Mandatory power cart not included')),
        (POWER_CART_INCLUDED, _('Power cart included')),
    )

    created = models.DateTimeField(default=timezone.now)
    type = models.ForeignKey(
        'CertificateType',
        related_name='certificates',
        on_delete=models.PROTECT
        )
    club = models.ForeignKey(
        Club,
        related_name='certificates',
        on_delete=models.PROTECT
        )
    club_secondary = models.ForeignKey(
        Club, related_name='certificates_secondary',
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )
    quantity = models.DecimalField(max_digits=6, decimal_places=2)
    tax = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    power_cart = models.IntegerField(choices=POWER_CART_CHOICES, default=POWER_CART_NOT_INCLUDED)
    expiry_date = models.DateField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    code = models.CharField(
        'Production Code',
        max_length=13, unique=True, blank=True
        )
    staging_code = models.CharField(
        'Staging Code',
        max_length=13, blank=True
        )
    batch = models.ForeignKey(
        CertificateBatch,
        related_name='certificates',
        on_delete=models.CASCADE,
        null=True,
        blank=True
        )
    note = models.CharField(null=True, blank=True, max_length=255)

    class Meta:
        ordering = ('-created',)
        permissions = (
            ('can_create', _('Can create certificates')),
            ('can_view', _('Can view certificates')),
        )

    def __str__(self):
        return self.code

    def __repr__(self):
        return '<Certificate: {}>'.format(self.code)

    def save(self, *args, **kwargs):
        if not self.code:
            self.generate_certificate_code()

        super().save(*args, **kwargs)

    @property
    def effective_header(self):
        if self.club and self.club_secondary and (self.club != self.club_secondary):
            print('FIRST IF')
            if self.type.double_header:
                print('DOUBLE HEADER')
                return self.type.double_header
            elif self.type.header:
                print('SINGLE HEADER')
                return self.type.header
            else:
                return None
        elif self.club and self.type.header:
            print('SECOND IF')
            return self.type.header
        else:
            return None


    def generate_certificate_code(self):
        code = randint(100000, 999999)
        self.code = '{}{}{}'.format(self.type.code, self.club.code, code)
        if Certificate.objects.filter(code=self.code).exists():
            self.generate_certificate_code()

    def get_member(self):
        if self.account_number is None:
            return None

        try:
            return User.objects.get(membership_number=self.account_number)
        except User.DoesNotExist:
            return None

    def generate_pdf(self):
        if self.type.template == CertificateType.AG30_TEMPLATE:
            generator_class = AG30CertificateGenerator
        elif self.type.template == CertificateType.PRESTIGE_50_TEMPLATE:
            generator_class = Prestige50CertificateGenerator
        elif self.type.template == CertificateType.GOLF_FOR_LIFE_TEMPLATE:
            generator_class = Prestige50CertificateGenerator
        else:
            generator_class = DefaultCertificateGenerator

        generator = generator_class(certificate=self)
        generator.generate()
        return generator.render()

    @property
    def issuer(self):
        return self.batch.creator.email

    @property
    def issuing_department(self):
        return self.batch.department.name

    @property
    def num_players(self):
        '''
        This is only the case for the other categories
        '''
        if self.type.category not in [
                CertificateType.RESORT_STAY_CATEGORY,
                CertificateType.MERCHANDISE_CATEGORY,
                CertificateType.RAIN_CHECK_CATEGORY
        ]:
            return self.quantity
        else:
            return None

    @property
    def num_nights(self):
        '''
        This is only the case for resort category certs
        '''
        if self.type.category in [CertificateType.RESORT_STAY_CATEGORY]:
            return self.quantity
        else:
            return None

    @property
    def dollar_amount(self):
        '''
        This is only the case for merchandise and rain check certs
        '''
        if self.type.category in [
                CertificateType.MERCHANDISE_CATEGORY,
                CertificateType.RAIN_CHECK_CATEGORY
        ]:
            return self.quantity + self.tax
        else:
            return None



class CertificateType(models.Model):
    ONE_YEAR_EXPIRY = 1
    DYNAMIC_EXPIRY_CHOICES = (
        (ONE_YEAR_EXPIRY, _('One year from creation')),
    )

    DEFAULT_TEMPLATE = 0
    AG30_TEMPLATE = 1
    PRESTIGE_50_TEMPLATE = 2
    GOLF_FOR_LIFE_TEMPLATE = 3
    TEMPLATE_CHOICES = (
        (DEFAULT_TEMPLATE, _('Default')),
        (AG30_TEMPLATE, _('AG30 Template')),
        (PRESTIGE_50_TEMPLATE, _('Prestige 50 Template')),
        (GOLF_FOR_LIFE_TEMPLATE, _('Golf for Life Template')),
    )

    DEFAULT_CATEGORY = 0
    PLAYERS_CLUB_CATEGORY = 1
    MERCHANDISE_CATEGORY = 2
    RESORT_STAY_CATEGORY = 3
    RAIN_CHECK_CATEGORY = 4
    PRESTIGE_50_CATEGORY = 5
    LEFT_SIDE_CUSTOM = 6
    US_ROUND_CERT_PROGRAM = 7
    CATEGORY_CHOICES = (
                        (DEFAULT_CATEGORY, _('Default')),
                        (PLAYERS_CLUB_CATEGORY, _("Player's Club")),
                        (MERCHANDISE_CATEGORY, _('Merchandise')),
                        (RESORT_STAY_CATEGORY, _('Resort Stay')),
                        (RAIN_CHECK_CATEGORY, _('Rain Check')),
                        (PRESTIGE_50_CATEGORY, _('Prestige 50')),
                        (LEFT_SIDE_CUSTOM, _('Left Side Custom')),
                        (US_ROUND_CERT_PROGRAM, _('US Round Cert Program'))
                    )

    GOLF_SHOP_LOCATION = 'Golf Shop'
    FRONT_DESK_LOCATION = 'Front Desk'
    REDEMPTION_LOCATION_CHOICES = (
        (GOLF_SHOP_LOCATION, _('Golf Shop')),
        (FRONT_DESK_LOCATION, _('Front Desk')),
    )

    header = models.ImageField(
        upload_to=RandomizedUploadPath('certificate_headers'),
        blank=True,
        null=True,
        help_text='Single club banner'
        )

    double_header = models.ImageField(
        upload_to=RandomizedUploadPath('certificate_headers'),
        blank=True,
        null=True,
        help_text='2-club banner'
        )


    name = models.CharField(max_length=255)
    name_fr = models.CharField(max_length=255, blank=True)
    code = models.CharField(
        'Code',
        max_length=3)
    staging_code = models.CharField(
        'Staging Code',
        max_length=3, blank=True, null=True)
    advertisement = models.ForeignKey(
        CertificateAd,
        related_name='certificate_types',
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )
    club = models.ForeignKey(
        Club,
        related_name='certificate_types',
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )
    quantity = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    power_cart = models.IntegerField(choices=Certificate.POWER_CART_CHOICES, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    dynamic_expiry = models.IntegerField(null=True, blank=True, choices=DYNAMIC_EXPIRY_CHOICES)
    message = models.TextField(blank=True)
    message_fr = models.TextField(blank=True)
    restrictions = models.TextField(blank=True)
    restrictions_fr = models.TextField(blank=True)
    redemption_location = models.CharField(max_length=64, default=GOLF_SHOP_LOCATION,
                                           choices=REDEMPTION_LOCATION_CHOICES)
    redemption_details = models.TextField(blank=True)
    redemption_details_fr = models.TextField(blank=True)
    departments = models.ManyToManyField(Department, through='DepartmentCertificateType',
                                         related_name='certificate_types')
    hide_recipient_name = models.BooleanField(default=False)
    players_club_clubs = models.ManyToManyField(Club, related_name='cpc_certificate_types',
                                                blank=True)
    players_club_daily_fee_listing = models.BooleanField(default=False)
    template = models.IntegerField(choices=TEMPLATE_CHOICES, default=DEFAULT_TEMPLATE)
    category = models.IntegerField(choices=CATEGORY_CHOICES, default=DEFAULT_CATEGORY)

    def localized(self, name, locale='en'):
        if locale.lower() == 'en':
            return getattr(self, name)
        else:
            return getattr(self, '{}_{}'.format(name, locale.lower()))

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<CertificateType: {}>'.format(self.name)


class DepartmentCertificateType(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT
        )
    certificate_type = models.ForeignKey(
        CertificateType,
        on_delete=models.PROTECT
        )
    guid = models.CharField('Production GUID', max_length=36, null=True, blank=True)
    staging_guid = models.CharField('Staging GUID', max_length=36, null=True, blank=True)


    class Meta:
        unique_together = (('department', 'certificate_type'),)

    def __str__(self):
        return '{}: {}'.format(self.department.name, self.certificate_type.name)

    def __repr__(self):
        return '<DepartmentCertificateType {}: {}>'.format(self.department.name,
                                                           self.certificate_type.name)


class CertificateGroup(models.Model):
    name = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department,
        related_name='certificate_groups',
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<CertificateGroup: {}>'.format(self.name)


class CertificateGroupTemplate(models.Model):
    group = models.ForeignKey(
        CertificateGroup,
        related_name='templates',
        on_delete=models.PROTECT
        )
    type = models.ForeignKey(
        CertificateType,
        related_name='templates',
        on_delete=models.PROTECT
        )
    count = models.PositiveIntegerField()
    club = models.ForeignKey(
        Club,
        related_name='certificate_templates',
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )
    club_secondary = models.ForeignKey(
        Club,
        related_name='secondary_certificate_templates',
        null=True,
        blank=True,
        on_delete=models.PROTECT)
    note = models.CharField(null=True, blank=True, max_length=255)
    quantity = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    power_cart = models.IntegerField(choices=Certificate.POWER_CART_CHOICES, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return '{}: {}'.format(self.group.name, self.type.name)

    def __repr__(self):
        return '<CertificateGroupTemplate: {}: {}>'.format(self.group.name, self.type.name)

sync_order = [
    CertificateAd, Department, EmailSignature,
    CertificateBatch, DepartmentCertificateType,
    CertificateType, CertificateGroupTemplate,
    Certificate
]