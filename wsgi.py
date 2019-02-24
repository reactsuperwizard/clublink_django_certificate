import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'clublink.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Production')

from configurations.wsgi import get_wsgi_application
from raven.contrib.django.raven_compat.middleware.wsgi import Sentry

application = Sentry(get_wsgi_application())
