from django.conf import settings
from raven.contrib.django.raven_compat.models import client as raven_client
from rest_framework.views import exception_handler


def logging_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Log to Sentry
    if getattr(settings, 'RAVEN_LOG_API_ERRORS', False):
        raven_client.context.activate()
        raven_client.context.merge({
            'extra': {
                'exc': exc,
                'context': context,
            }
        })
        raven_client.captureMessage('API failure')
        raven_client.context.clear()

    return response
