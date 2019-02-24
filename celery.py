from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

import logging

# Get an instance of a logger
log = logging.getLogger(__name__)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clublink.settings')

os.environ.setdefault('DJANGO_CONFIGURATION', 'Development')

# This is required as per: http://django-configurations.readthedocs.io/en/stable/cookbook/#id4
from configurations import importer
if not importer.installed:
    importer.install()

app = Celery('clublink')

## Broker settings.
# broker_url = '	amqp://kugwjdey:pXoRMussdXbx3laOwioSoEswFtSsfwNH@emu.rmq.cloudamqp.com/kugwjdey'

# ## Using the database to store task state and results.
# result_backend = 'redis://localhost/8'

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

from django.core.mail import EmailMultiAlternatives


@app.task
def send_email_later(**kwargs):
    '''
    Sends an email at a later time, given all of the components in a regular email send.

    TODO - adjust this when switching to Anymail
    '''
    if 'message_html' in kwargs:
        message_html = kwargs.pop('message_html')
    
    # print('before email')
    # print(kwargs)
    email = EmailMultiAlternatives(**kwargs)
    # print('before message_html')
    if message_html:
        email.attach_alternative (message_html, 'text/html')
    # print('AFTER HTML')
    output = email.send()
    # print(output)