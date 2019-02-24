import os

from configurations import Configuration, values
from django.utils.translation import ugettext_lazy as _
from django_jinja.builtins import DEFAULT_EXTENSIONS


class Core(Configuration):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ROOT_URLCONF = 'clublink.urls.common'

    INTERNAL_IPS = '127.0.0.1'

    TEMPLATES = [
        {
            'BACKEND': 'django_jinja.backend.Jinja2',
            'DIRS': [
                'templates',
            ],
            'APP_DIRS': True,
            'OPTIONS': {
                'match_regex': '.+(\.jinja|\.txt)',
                'match_extension': None,
                'extensions': DEFAULT_EXTENSIONS + [
                    'webpack_loader.contrib.jinja2ext.WebpackExtension',
                    'cacheops.jinja2.cache',
                    'clublink.base.extensions.SharedSession',
                ],
                'context_processors': [
                    'django.contrib.auth.context_processors.auth',
                    'django.template.context_processors.debug',
                    'django.template.context_processors.i18n',
                    'django.template.context_processors.media',
                    'django.template.context_processors.static',
                    'django.template.context_processors.tz',
                    'django.contrib.messages.context_processors.messages',
                    'clublink.base.context_processors.globals',
                ],
            }
        },
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ]

    WSGI_APPLICATION = 'clublink.wsgi.production.application'

    AUTH_PASSWORD_VALIDATORS = [
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
        {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
        {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
        {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    ]

    AUTHENTICATION_BACKENDS = [
        'django.contrib.auth.backends.ModelBackend',
    ]

    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    ]

    AUTH_USER_MODEL = 'users.User'

    LANGUAGE_CODE = 'en'
    USE_I18N = True
    USE_L10N = True
    USE_TZ = True

    LANGUAGES = (
        ('en', _('English')),
        ('fr', _('French')),
    )

    LOCALE_PATHS = (
        os.path.join(BASE_DIR, 'locale'),
    )

    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')

    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

    ASSETS_URL = '/asset_files/'
    ASSETS_ROOT = os.path.join(BASE_DIR, 'asset_files')

    STATICFILES_DIRS = (
        os.path.join(BASE_DIR, 'assets'),
    )

    WEBPACK_LOADER = {
        'DEFAULT': {
            'BUNDLE_DIR_NAME': 'bundles/',
            'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json')
        },
    }

    SWAGGER_SETTINGS = {
        'DOC_EXPANSION': 'list',
        'JSON_EDITOR': True,
    }

    CSRF_COOKIE_HTTPONLY = True

    SECURE_REDIRECT_EXEMPT = [
        r'^__health__/$'
    ]


class Base(Core):
    DOTENV_EXISTS = os.path.exists(os.path.join(Core.BASE_DIR, '.env'))
    DOTENV = os.path.join(Core.BASE_DIR, '.env') if DOTENV_EXISTS else None

    SECRET_KEY = values.SecretValue()

    DEBUG = values.BooleanValue(False)
    ADMIN_ENABLED = values.BooleanValue(DEBUG)

    ALLOWED_HOSTS = values.ListValue()
    # SESSION_COOKIE_NAME = 'clublink_session_id'
    SITE_ID = 1

    def INSTALLED_APPS(self):
        return [
            'collectfast',

            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'django.contrib.sites',

            'captcha',
            #'ddtrace.contrib.django',
            'django_jinja',
            'raven.contrib.django.raven_compat',
            'rest_framework',
            'rest_framework.authtoken',
            'rest_framework_swagger',
            'rosetta',
            'storages',
            'webpack_loader',

            'shared_session',

            'clublink.base',
            'clublink.users',
            'clublink.certificates',
            'clublink.clubs',
            'clublink.corp',
            'clublink.cms',
            'clublink.landings',
        ]

    def MIDDLEWARE(self):
        return [
            'clublink.base.middleware.HostnameRoutingMiddleware',
            'clublink.base.middleware.ShortCircuitMiddleware',
            #'ddtrace.contrib.django.TraceMiddleware',
            'django.middleware.security.SecurityMiddleware',

            # THIS WON'T WORK
            # 'clublink.base.middleware.MultiDomainSessionMiddleware',

            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            'clublink.base.middleware.SpoofedUserMiddleware',
            'clublink.base.middleware.ScaffoldingMiddleware',
            'clublink.base.middleware.LocaleMiddleware',
            'django.contrib.sites.middleware.CurrentSiteMiddleware',
        ]

    TIME_ZONE = values.Value('America/Toronto')

    GIFT_CERTIFICATE_SITE_URL = values.Value()
    CORP_SITE_URL = values.Value()
    CLUB_SITE_URL = values.Value()
    ADMIN_SITE_URL = values.Value()

    ADMIN_HOSTNAME = values.RegexValue(r'^admin\.')
    CORP_HOSTNAME = values.RegexValue(r'^www\.')
    API_HOSTNAME = values.RegexValue(r'^api\.')
    GIFT_CERTIFICATE_HOSTNAME = values.RegexValue(r'^gc\.')
    GIFT_CARDS_HOSTNAME = values.RegexValue(r'^giftcards\.')

    def HOSTNAME_URLCONFS(self):
        return (
            (self.ADMIN_HOSTNAME, 'clublink.urls.admin'),
            (self.CORP_HOSTNAME, 'clublink.urls.corp'),
            (self.API_HOSTNAME, 'clublink.urls.api'),
            (self.GIFT_CERTIFICATE_HOSTNAME, 'clublink.urls.gc'),
            (self.GIFT_CARDS_HOSTNAME, 'clublink.urls.gift_cards'),
        )

    LANGUAGES = Core.LANGUAGES

    def HOSTNAME_LANGUAGES(self):
        return (
            (self.ADMIN_HOSTNAME, ('en',)),
            (self.GIFT_CERTIFICATE_HOSTNAME, ('en',)),
        )

    DATABASES = values.DatabaseURLValue('mysql://mysql@localhost/clublink')

    VPN_PROTECTED_VIEWS_ENABLED = values.BooleanValue(True)
    VPN_IP_ADDRESS = values.Value('10.8.0.1')

    EMAIL_HOST = values.Value()
    EMAIL_PORT = values.IntegerValue(587)
    EMAIL_HOST_USER = values.Value()
    EMAIL_HOST_PASSWORD = values.Value()
    EMAIL_USE_TLS = values.BooleanValue(True)

    DEFAULT_FROM_EMAIL_ADDRESS = 'noreply@clublink.ca'
    MEMBER_SERVICES_EMAIL_ADDRESS = values.EmailValue('memberservices@clublink.ca')
    GIFT_CERTIFICATE_EMAIL_ADDRESS = values.EmailValue('giftcertificates@clublink.ca')
    CORPORATE_EVENTS_EMAIL_ADDRESS = values.EmailValue('corporateevents@clublink.ca')
    MEMBERSHIP_SALES_EMAIL_ADDRESS = values.EmailValue('membershipsales@clublink.ca')
    EVENTS_EMAIL_ADDRESSES = values.ListValue([
        'greatweddings@clublink.ca',
        'greatmeetings@clublink.ca',
        'greatbanquets@clublink.ca',
    ])

    IBS_API_WSDL = values.Value()
    IBS_API_USER = values.Value()
    IBS_API_PASSWORD = values.Value()

    IBS_WEBRES_API_ROOT = values.Value()
    IBS_WEBRES_API_USER = values.Value()
    IBS_WEBRES_API_PASSWORD = values.Value()

    GOOGLE_MAPS_API_KEY = values.Value()
    GOOGLE_ANALYTICS_TRACKING_ID = values.Value()

    def REST_FRAMEWORK(self):
        return {
            'DEFAULT_AUTHENTICATION_CLASSES': (
                'rest_framework.authentication.TokenAuthentication',
                'rest_framework.authentication.SessionAuthentication',
            ),
            'DEFAULT_PERMISSION_CLASSES': (
                'rest_framework.permissions.IsAuthenticated',
            ),
            'DEFAULT_RENDERER_CLASSES': (
                'rest_framework.renderers.JSONRenderer',
                values.ListValue(environ_name='REST_FRAMEWORK_DEFAULT_RENDERER_CLASSES'),
            ),
            'DEFAULT_PAGINATION_CLASS': None,
            'PAGE_SIZE': 50,
            'EXCEPTION_HANDLER': 'clublink.base.api.handlers.logging_exception_handler',
        }

    def CACHES(self):
        return {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': values.Value('redis://127.0.0.1:6379/1',
                                         environ_name='CACHES_DEFAULT_LOCATION'),
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            },
            'collectfast': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': values.Value('redis://127.0.0.1:6379/3',
                                         environ_name='CACHES_COLLECTFAST_LOCATION'),
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'MAX_ENTRIES': 5000,
                },
                'TIMEOUT': 21600
            },
        }

    CACHEOPS_REDIS = values.Value('redis://127.0.0.1:6379/2')

    def OPBEAT(self):
        return {
            'ORGANIZATION_ID': values.Value(None, environ_name='OPBEAT_ORGANIZATION_ID'),
            'APP_ID': values.Value(None, environ_name='OPBEAT_APP_ID'),
            'SECRET_TOKEN': values.Value(None, environ_name='OPBEAT_SECRET_TOKEN'),
        }

    def RAVEN_CONFIG(self):
        return {
            'dsn': values.URLValue(None, environ_name='RAVEN_CONFIG_DSN'),
            'string_max_length': values.IntegerValue(
                2000, environ_name='RAVEN_CONFIG_STRING_MAX_LENGTH')
        }

    RAVEN_LOG_API_ERRORS = values.BooleanValue(False)

    DEFAULT_CERTIFICATE_EMPLOYEE_NUMBER = values.Value()
    DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER = values.Value('')
    CERTIFICATES_BATCH_LIMIT = values.IntegerValue(110)

    DATA_UPLOAD_MAX_NUMBER_FIELDS = values.IntegerValue(1000)

    GIFT_CERTIFICATE_IP_WHITELIST_ENABLED = values.BooleanValue(False)
    GIFT_CERTIFICATE_IP_WHITELIST = values.ListValue()

    AES_SHARED_KEY = values.Value()

    DYNAMICS_HOST = values.Value()
    DYNAMICS_USER = values.Value()
    DYNAMICS_PASSWORD = values.Value()
    DYNAMICS_DATABASE = values.Value()

    NOCAPTCHA = values.BooleanValue(True)
    RECAPTCHA_PUBLIC_KEY = values.Value()
    RECAPTCHA_PRIVATE_KEY = values.Value()

    COLLECTFAST_CACHE = values.Value('collectfast')

    PASSWORD_RESET_DEBUG = values.BooleanValue(True)
    PASSWORD_RESET_DEBUG_EMAIL_ADDRESSES = values.ListValue()

    ASSETS_FILE_STORAGE = values.Value('django.core.files.storage.FileSystemStorage')

    SEARCH_ENGINE_INDEXING_DISABLED = values.BooleanValue(False)

    SESSION_EXPIRE_AT_BROWSER_CLOSE = values.BooleanValue(True)

    def DATADOG_TRACE(self):
        return {
            'ENABLED': False,
        }


class Development(Base):
    """Settings for local development."""
    SECRET_KEY = values.Value('thisisarandomstringastringstring')
    DEBUG = values.BooleanValue(True)
    ADMIN_ENABLED = DEBUG

    CORP_HOSTNAME = values.RegexValue(r'home\.')

    #
    DATABASES = values.DatabaseURLValue('mysql://clublink_dev:Fishy~123@localhost/clublink')
    ALLOWED_HOSTS = '*'    

    INTERNAL_IPS = ['127.0.0.1']
    RESULTS_CACHE_SIZE = 500
    
    SESSION_SAVE_EVERY_REQUEST = True
    #NOTE: https://stackoverflow.com/questions/6671419/django-session-cookie-domain-on-localhost
    # SESSION_COOKIE_DOMAIN='.localhost:8000'
    SHARED_SESSION_SITES = ['home.localhost:8000', 'home.localhost:8080']
    SHARED_SESSION_ALWAYS_REPLACE = True

    COLLECTFAST_ENABLED = values.BooleanValue(False)

    VPN_PROTECTED_VIEWS_ENABLED = values.BooleanValue(False)

    SWAGGER_SETTINGS = Base.SWAGGER_SETTINGS
    SWAGGER_SETTINGS['VALIDATOR_URL'] = None

    def INSTALLED_APPS(self):
        ia = super().INSTALLED_APPS()
        ia += ['debug_toolbar']
        return ia

    def MIDDLEWARE(self):
        middleware = super().MIDDLEWARE()
        middleware += [
            'querycount.middleware.QueryCountMiddleware',
            'debug_toolbar.middleware.DebugToolbarMiddleware'
            ]
        return middleware

    def QUERYCOUNT(self):
        return {
            'IGNORE_REQUEST_PATTERNS': [
                r'^/admin/'
            ],
            'IGNORE_SQL_PATTERNS': [
                r'^silk_'
            ],
            'DISPLAY_DUPLICATES': values.IntegerValue(
                environ_name='QUERYCOUNT_DISPLAY_DUPLICATES'),
        }


class Production(Base):
    """Settings for production environment."""
    SECURE_SSL_REDIRECT = values.BooleanValue(True)
    SESSION_COOKIE_SECURE = values.BooleanValue(True)
    CSRF_COOKIE_SECURE = values.BooleanValue(True)

    ASSETS_FILE_STORAGE = 'clublink.base.storages.S3Boto3StorageAssets'
    DEFAULT_FILE_STORAGE = 'clublink.base.storages.S3Boto3StorageMedia'
    STATICFILES_STORAGE = 'clublink.base.storages.S3Boto3StorageStatic'

    STATICFILES_LOCATION = values.Value('static')
    MEDIA_LOCATION = values.Value('media')
    ASSETS_LOCATION = values.Value('assets')

    AWS_ACCESS_KEY_ID = values.Value()
    AWS_SECRET_ACCESS_KEY = values.Value()
    AWS_STORAGE_BUCKET_NAME = values.Value()
    AWS_S3_CUSTOM_DOMAIN = values.Value(None)

    AWS_PRELOAD_METADATA = values.BooleanValue(True)
    AWS_IS_GZIPPED = values.BooleanValue(True)
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=604800',
    }

    AWS_QUERYSTRING_AUTH = values.BooleanValue(False)
    AWS_QUERYSTRING_EXPIRE = values.BooleanValue(False)

    def DATADOG_TRACE(self):
        datadog_trace = super().DATADOG_TRACE()
        datadog_trace.update({
            'ENABLED': True,
            'TAGS': {
                'env': 'production',
            },
        })
        return datadog_trace

class USDevelopment(Development):

    DOTENV_EXISTS = os.path.exists(os.path.join(Core.BASE_DIR, '.usa-env'))
    DOTENV = os.path.join(Core.BASE_DIR, '.usa-env') if DOTENV_EXISTS else None
    SITE_ID=2


class Staging(Production):
    # WHY THE FUCK WOULD YOU SUBLASS PRODUCTIN WITH STAGING?
    """Settings for the staging environment."""
    SECURE_SSL_REDIRECT = values.BooleanValue(False)
    SESSION_COOKIE_SECURE = values.BooleanValue(False)
    CSRF_COOKIE_SECURE = values.BooleanValue(False)
    SEARCH_ENGINE_INDEXING_DISABLED = values.BooleanValue(True)

    SHARED_SESSION_SITES = ['can-stage-club.link', 'stage-club.link', 'usa-stage-club.link']
    # SESSION_COOKIE_NAME = 'staging_session_id'
    SESSION_COOKIE_DOMAIN = '.stage-club.link'
    SESSION_SAVE_EVERY_REQUEST = True


    # ASSETS_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    # DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    # STATICFILES_STORAGE = 'django.core.files.storage.FileSystemStorage'

    # STATIC_URL = '/static/'
    # MEDIA_URL = '/media/'
    # ASSETS_URL = '/asset_files/'    


    ## BOTO UPLOADS ARE NOT VERSIONED

    ASSETS_FILE_STORAGE = 'clublink.base.storages.S3Boto3StorageAssets'
    DEFAULT_FILE_STORAGE = 'clublink.base.storages.S3Boto3StorageMedia'
    STATICFILES_STORAGE = 'clublink.base.storages.S3Boto3StorageStatic' 

    S3_BASE = 'https://s3.amazonaws.com/ss3.cdn-club.link/'
    STATIC_URL = S3_BASE + '/static/'
    MEDIA_URL = S3_BASE +'/media/'
    ASSETS_URL = S3_BASE +'/asset_files/'

    # def INSTALLED_APPS(self):
    #     ia = super().INSTALLED_APPS()
    #     ia += ['opbeat.contrib.django']
    #     return ia


    # OPBEAT = {
    #     'ORGANIZATION_ID': '1ae899b3f6d346a3996898f017846a1a',
    #     'APP_ID': 'afe8898b90',
    #     'SECRET_TOKEN': '66ef91e750a4aa0cdc5da7a049af5d409ce5bf0f',
    # }    

    # def MIDDLEWARE(self):
    #     middleware = super().MIDDLEWARE()
    #     middleware = [
    #         'opbeat.contrib.django.middleware.OpbeatAPMMiddleware'
    #         ].extend(middleware)
    #     return middleware
    

    # def DATADOG_TRACE(self):
    #     datadog_trace = super().DATADOG_TRACE()
    #     datadog_trace['TAGS'].update({
    #         'env': 'staging',
    #     })
    #     return datadog_trace

class StagingUSA(Staging):
    DOTENV_EXISTS = os.path.exists(os.path.join(Core.BASE_DIR, '.usa-env'))
    DOTENV = os.path.join(Core.BASE_DIR, '.usa-env') if DOTENV_EXISTS else None
    SITE_ID=2
    SHARED_SESSION_SITES = ['can-stage-club.link', 'stage-club.link', 'usa-stage-club.link']
    # SESSION_COOKIE_NAME = 'staging_session_id'
    SESSION_COOKIE_DOMAIN = '.usa-stage-club.link'        
    SESSION_SAVE_EVERY_REQUEST = True

class Build(Production):
    """Settings for building the Docker image."""
    SECRET_KEY = values.Value('not a secret')



class Test(Production):
    """Settings for test runner."""
    SECRET_KEY = values.Value('not a secret')
    EMAIL_BACKEND = values.Value('django.core.mail.backends.locmem.EmailBackend')
    CACHEOPS_REDIS = values.Value('redis://localhost:6379/5', environ_name='CACHEOPS_REDIS_TEST')
    IBS_API_USER = ''
    IBS_API_PASSWORD = ''
    GOOGLE_MAPS_API_KEY = None
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    ASSETS_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    STATICFILES_STORAGE = 'django.core.files.storage.FileSystemStorage'

    def DATADOG_TRACE(self):
        datadog_trace = super().DATADOG_TRACE()
        datadog_trace.update({
            'ENABLED': False
        })
        return datadog_trace
