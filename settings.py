"""
For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os, logging

from configurations import Configuration, values, importer
if not importer.installed:
    importer.install()

from django.utils.translation import ugettext_lazy as _
from django_jinja.builtins import DEFAULT_EXTENSIONS

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AWSMixin:
    AWS_ACCESS_KEY_ID = values.Value('')
    AWS_SECRET_ACCESS_KEY = values.Value('')
    AWS_STORAGE_BUCKET_NAME = values.Value('')
    S3_BASE = values.Value('')
    AWS_QUERYSTRING_AUTH = values.BooleanValue(False)
    AWS_HEADERS = {
        'Expires': 'Sun, 30 Aug 2020 12:00:00 GMT',
        'Cache-Control': 'max-age=21600',
    }

class DebugMixin:
    DEBUG = values.Value(True)
    ADMIN_ENABLED = values.BooleanValue(True)
    INTERNAL_IPS = values.IPValue('127.0.0.1')

    @classmethod
    def pre_setup(cls):
        super(DebugMixin, cls).pre_setup()
        logging.info('\n{} loading!'.format(cls.__str__))

    @classmethod
    def post_setup(cls):
        super(DebugMixin, cls).post_setup()
        logging.info('\t\t--> Finished!'.format(cls.__str__))

class OpbeatMixin:

    def OPBEAT(self):
        return {
            'ORGANIZATION_ID': values.Value(None, environ_name='OPBEAT_ORGANIZATION_ID'),
            'APP_ID': values.Value(None, environ_name='OPBEAT_APP_ID'),
            'SECRET_TOKEN': values.Value(None, environ_name='OPBEAT_SECRET_TOKEN'),
        }

    @classmethod
    def post_setup(cls):

        LOGGING['handlers']['opbeat'] = {
            'level': 'INFO',
            'class': 'opbeat.contrib.django.handlers.OpbeatHandler',
            }


class SentryMixin:

    import raven

    @classmethod
    def setup(cls):
        super(SentryMixin, cls).setup()
        logging.info('SentryMixin loaded!')

        cls.MIDDLEWARE = [
            'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
            'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
        ] + cls.MIDDLEWARE

    @classmethod
    def post_setup(cls):

        logging.info('''
            Middleware is now:
            {}
            '''.format(cls.MIDDLEWARE)
            )

    RAVEN_CONFIG = values.DictValue({})
    RAVEN_LOG_API_ERRORS = values.BooleanValue(False)

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'sentry'],
        },
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s '
                        '%(process)d %(thread)d %(message)s'
            },
        },
        'handlers': {
            'sentry': {
                'level': 'INFO', # To capture more than ERROR, change to WARNING, INFO, etc.
                'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
                # 'tags': {'custom-tag': 'x'},
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose'
            }
        },
        'loggers': {
            # This package outputs a lot of garbage that wasn't taken out
            'dicttoxml': {
                'level': 'ERROR',
                'handlers': ['console'],
                'propogate': False
            },
            # We have some debug statements here that should not be going to sentry
            'clublink.cms': {
                'level': 'INFO',
                'handlers': ['console'],
                'propogate': False
            },
            'django': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'django.db.backends': {
                'level': 'ERROR',
                'handlers': ['console', 'sentry'],
                'propagate': False,
            },
            'raven': {
                'level': 'ERROR',
                'handlers': ['console', 'sentry'],
                'propagate': False,
            },
            'sentry.errors': {
                'level': 'ERROR',
                'handlers': ['console'],
                'propagate': False,
            },
        },
    }


class CacheopsMixin:
    CACHEOPS_DEGRADE_ON_FAILURE = True
    CACHEOPS_REDIS = values.Value('redis://127.0.0.1:6379/2')
    COLLECTFAST_CACHE = values.Value('collectfast')
    CACHEOPS = {
        'auth.user': {'ops': 'get', 'timeout': 60*15},
        '*.*': {'ops': '*', 'timeout': 60*60}
        }
    COLLECTFAST_THREADS = 20
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"

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

class Base(Configuration):
    '''
    All configurations should sublcass this base class.
    
    This contains all that is required, aside from custom endpoints that will
    vary per deployment and/or environment.

    Defaults have been set to err on the side of caution, so DEBUG, ADMIN, etc 
    will have to be explictly turned on where necessary.
    '''

    # Quick-start development settings - unsuitable for production
    # See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

    # THIS IS JUST A DEFAULT THAT WAS GENERATED FOR LOCAL DEVELOPMENT

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = values.Value('abceasyas123')

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = values.BooleanValue(False)
    ADMIN_ENABLED = values.BooleanValue(False)

    SESSION_EXPIRE_AT_BROWSER_CLOSE = values.BooleanValue(True)

    AUTH_USER_MODEL = values.Value('users.User')

    MEMBERSHIP_ENCODE_KEY = values.Value('')
    MEMBERSHIP_RENEWAL_URL_BASE = values.URLValue('')

    SHARED_SESSION_SITES = values.ListValue([])
    SESSION_COOKIE_DOMAIN = values.Value()
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    ALLOWED_HOSTS = values.ListValue([])
    SITE_ID = values.IntegerValue(1)

    ADMINS = [('Sir Terence', 'terryhong@gmail.com')]

    SERVER_EMAIL = 'errors@clublink.ca'

    # SESSION_COOKIE_AGE = 60*60*24

    X_FRAME_OPTIONS = 'ALLOW'

    INSTALLED_APPS = values.ListValue([
        # Django packages
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.sites',
        'django.contrib.sitemaps',

        # External packages
        'captcha',
        'debug_toolbar',
        'django_jinja',
        'raven.contrib.django.raven_compat',
        'rest_framework_swagger',
        'rest_framework.authtoken',
        'rest_framework',
        'rosetta',
        'shared_session',
        'storages',
        'webpack_loader',
        'cacheops',
        'robots',
        'import_export',

        # Application packages
        'clublink.base',
        'clublink.certificates',
        'clublink.clubs',
        'clublink.cms',
        'clublink.corp',
        'clublink.landings',
        'clublink.users',
        'clublink.emails',

    ])

    MIDDLEWARE = values.ListValue([
        'debug_toolbar.middleware.DebugToolbarMiddleware',

        # Custom middleware
        'clublink.base.middleware.HostnameRoutingMiddleware',
        'clublink.base.middleware.ShortCircuitMiddleware',

        # Django middleware
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',

        # Sites middleware
        'django.contrib.sites.middleware.CurrentSiteMiddleware',

        # Custom middleware
        'clublink.base.middleware.SpoofedUserMiddleware',
        'clublink.base.middleware.ScaffoldingMiddleware',
        'clublink.base.middleware.LocaleMiddleware'

    ])

    ROOT_URLCONF = values.Value('clublink.urls.common')

    TEMPLATES = values.ListValue([
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
                    'jinja2.ext.i18n',
                    'cacheops.jinja2.cache',
                    'clublink.base.extensions.SharedSession',
                ],
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.i18n',
                    'django.template.context_processors.media',
                    'django.template.context_processors.static',
                    'django.template.context_processors.tz',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                    # Custom context processors
                    'clublink.base.context_processors.globals'
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
        }
    ])

    WSGI_APPLICATION = values.Value('clublink.wsgi.application')

    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': values.Value('redis://127.0.0.1:6379/1',
                                        environ_name='CACHES_DEFAULT_LOCATION'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

    # Database
    # https://docs.djangoproject.com/en/1.11/ref/settings/#

    # As per: https://github.com/kennethreitz/dj-database-url#url-schema
    ### <-----------------------------------------------------------------> ###
    ### NOTE!!!! THIS IS THE ONE VALUE THAT IS NOT PREFIXED WITH DJANGO_ ###
    # DATABASE_DICT = values.DictValue()

    # LEGACY_DATABASE_DICT = values.DictValue()
    ### <-----------------------------------------------------------------> ###

    DATABASE_ENGINE = values.Value("django.db.backends.mysql")
    DATABASE_NAME = values.Value()
    DATABASE_USER = values.Value()
    DATABASE_PASSWORD = values.Value()
    DATABASE_HOST = values.Value()
    DATABASE_PORT = values.Value('3306')

    LEGACY_DATABASE_ENGINE = values.Value("django.db.backends.mysql")
    LEGACY_DATABASE_NAME = values.Value()
    LEGACY_DATABASE_USER = values.Value()
    LEGACY_DATABASE_PASSWORD = values.Value()
    LEGACY_DATABASE_HOST = values.Value()
    LEGACY_DATABASE_PORT = values.Value('3306')

    @property
    def DATABASES(self):
        DATABASES = {
            'default': {
                'ENGINE': self.DATABASE_ENGINE,
                'NAME': self.DATABASE_NAME,
                'USER': self.DATABASE_USER,
                'PASSWORD': self.DATABASE_PASSWORD,
                'HOST': self.DATABASE_HOST,
                'PORT': self.DATABASE_PORT
                }
        }
        return DATABASES

    # Password validation
    # https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

    AUTH_PASSWORD_VALIDATORS = values.ListValue([
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ])


    # Internationalization
    # https://docs.djangoproject.com/en/1.11/topics/i18n/

    LANGUAGE_CODE = values.Value('en')
    LANGUAGES = values.SingleNestedTupleValue((
        ('en', _('English')),
        ('fr', _('French')),
    ))
    LOCALE_PATHS = values.SingleNestedTupleValue((
        os.path.join(BASE_DIR, 'locale'),
    ))

    TIME_ZONE = values.Value('America/Toronto')

    USE_I18N = values.BooleanValue(True)

    USE_L10N = values.BooleanValue(True)

    USE_TZ = values.BooleanValue(True)


    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/1.11/howto/static-files/
    DEFAULT_FILE_STORAGE=values.Value('django.contrib.staticfiles.storage.StaticFilesStorage')
    STATICFILES_DIRS = (
        os.path.join(BASE_DIR, 'assets'),
    )

    # STATIC #
    STATIC_URL = values.Value('/static/')
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')
    STATICFILES_LOCATION = values.Value('static')
    STATICFILES_STORAGE=values.Value('django.contrib.staticfiles.storage.StaticFilesStorage')

    # ASSETS #
    ASSETS_URL = values.Value('/asset_files/')
    ASSETS_ROOT = os.path.join(BASE_DIR, 'asset_files')
    ASSETS_LOCATION = values.Value('assets')
    ASSETS_FILE_STORAGE=values.Value('django.contrib.staticfiles.storage.StaticFilesStorage')

    # MEDIA #
    MEDIA_URL = values.Value('/media/')
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    MEDIA_LOCATION = values.Value('media')

    # WEBPACK #
    WEBPACK_LOADER = values.DictValue({
        'DEFAULT': {
            'BUNDLE_DIR_NAME': 'bundles/',
            'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json')
        },
    })

    SWAGGER_SETTINGS = values.DictValue({
        'DOC_EXPANSION': 'list',
        'JSON_EDITOR': True,
    })

    CSRF_COOKIE_HTTPONLY = values.BooleanValue(True)
    SECURE_REDIRECT_EXEMPT = values.ListValue([
        r'^__health__/$'
    ])

    GIFT_CERTIFICATE_SITE_URL = values.URLValue()
    CORP_SITE_URL = values.URLValue()
    CLUB_SITE_URL = values.Value()
    ADMIN_SITE_URL = values.URLValue()

    ADMIN_HOSTNAME = values.RegexValue(r'^admin\.')
    CORP_HOSTNAME = values.RegexValue(r'^(www\.)?')
    API_HOSTNAME = values.RegexValue(r'^api\.')
    GIFT_CERTIFICATE_HOSTNAME = values.RegexValue(r'^giftcertificates\.')
    GIFT_CARDS_HOSTNAME = values.RegexValue(r'^giftcards\.')

    def HOSTNAME_URLCONFS(self):
        return (
            (self.ADMIN_HOSTNAME, 'clublink.urls.admin'),
            (self.CORP_HOSTNAME, 'clublink.urls.corp'),
            (self.API_HOSTNAME, 'clublink.urls.api'),
            (self.GIFT_CERTIFICATE_HOSTNAME, 'clublink.urls.gc'),
            (self.GIFT_CARDS_HOSTNAME, 'clublink.urls.gift_cards'),
        )

    def HOSTNAME_LANGUAGES(self):
        return (
            (self.ADMIN_HOSTNAME, ('en',)),
            (self.GIFT_CERTIFICATE_HOSTNAME, ('en',)),
        )

    VPN_PROTECTED_VIEWS_ENABLED = values.BooleanValue(True)
    VPN_IP_ADDRESS = values.Value('10.8.0.1')

    EMAIL_HOST = values.Value()
    EMAIL_PORT = values.IntegerValue(587)
    EMAIL_HOST_USER = values.Value()
    EMAIL_HOST_PASSWORD = values.Value()
    EMAIL_USE_TLS = values.BooleanValue(True)

    DEFAULT_FROM_EMAIL_ADDRESS = values.EmailValue('noreply@clublink.ca')
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

    DEFAULT_CERTIFICATE_EMPLOYEE_NUMBER = values.Value()
    DEFAULT_CERTIFICATE_MEMBERSHIP_NUMBER = values.Value('')
    CERTIFICATES_BATCH_LIMIT = values.IntegerValue(150)

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

    PASSWORD_RESET_DEBUG = values.BooleanValue(True)
    PASSWORD_RESET_DEBUG_EMAIL_ADDRESSES = values.ListValue()

    ASSETS_FILE_STORAGE = values.Value('django.core.files.storage.FileSystemStorage')

    SEARCH_ENGINE_INDEXING_DISABLED = values.BooleanValue(False)

    SESSION_EXPIRE_AT_BROWSER_CLOSE = values.BooleanValue(True)

    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework.authentication.TokenAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ),
        'DEFAULT_PERMISSION_CLASSES': (
            'rest_framework.permissions.IsAuthenticated',
        ),
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        ),
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 50,
        'EXCEPTION_HANDLER': 'clublink.base.api.handlers.logging_exception_handler',
    }

    CELERY_BROKER_URL = values.Value()
    CELERY_RESULT_BACKEND = values.Value()


class Development(AWSMixin, CacheopsMixin, DebugMixin, Base):
    SECRET_KEY = 'on!*t@k$#jr0uzscw72tcp#qkg*r-i_2f==at$!pc^#*iiijjy'
    DOTENV = os.path.join(BASE_DIR, '.dev-env')
    EMAIL_HOST = 'smtp.mailtrap.io'
    EMAIL_HOST_USER = '1fd7ebee0792d6'
    EMAIL_HOST_PASSWORD = 'b3fd4f7695e57f'
    EMAIL_PORT = '2525'
    EMAL_USE_TLS = True

    CELERY_BROKER_URL = 'amqp://kugwjdey:pXoRMussdXbx3laOwioSoEswFtSsfwNH@emu.rmq.cloudamqp.com/kugwjdey'

    ## Using the database to store task state and results.
    CELERY_RESULT_BACKEND = 'redis://localhost/8'


class USDevelopment(Development):
    DOTENV = os.path.join(BASE_DIR, '.dev-usa-env')

    CELERY_BROKER_URL = 'amqp://kugwjdey:pXoRMussdXbx3laOwioSoEswFtSsfwNH@emu.rmq.cloudamqp.com/kugwjdey'

    ## Using the database to store task state and results.
    CELERY_RESULT_BACKEND = 'redis://localhost/8'


class Staging(AWSMixin, CacheopsMixin, DebugMixin, Base):
    SITE_ID = 1
    DOTENV = os.path.join(BASE_DIR, '.staging-env')

    # TODO - Configurations messes up
    EMAIL_HOST = 'smtp.mailtrap.io'
    EMAIL_HOST_USER = '1ea5b555fad5b9'
    EMAIL_HOST_PASSWORD = 'ce224fb2c049ce'
    EMAIL_PORT = '2525'
    EMAL_USE_TLS = True

class USStaging(Staging):
    SITE_ID = 2
    DOTENV = os.path.join(BASE_DIR, '.staging-usa-env')

class Production(AWSMixin, CacheopsMixin, Base):
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
    SESSION_COOKIE_NAME = 'prodsessionid'
    SITE_ID = 1
    DOTENV = os.path.join(BASE_DIR, '.prod-env')

class USProduction(Production):
    SITE_ID = 2
    DOTENV = os.path.join(BASE_DIR, '.prod-usa-env')

class LBProduction(Production):
    SITE_ID = 1
    DOTENV = os.path.join(BASE_DIR, '.prod-lb-env')
