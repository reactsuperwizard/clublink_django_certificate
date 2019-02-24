import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clublink.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Staging')

from configurations.wsgi import get_wsgi_application  # flake8: noqa

application = get_wsgi_application()
