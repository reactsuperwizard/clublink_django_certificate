import json

from urllib.request import urlopen

from django.http import HttpResponse
from django.shortcuts import render
from raven.contrib.django.raven_compat.models import client as raven_client


from clublink.base.aws_utils import (
    SNS_MESSAGE_TYPE_NOTIFICATION,
    SNS_MESSAGE_TYPE_SUB_NOTIFICATION,
    verify_sns_notification,
)
from clublink.base.decorators import short_circuit_middlewares


@short_circuit_middlewares
def health_check(request):
    return HttpResponse(status=200)


@short_circuit_middlewares
def robots_txt(request):
    return render(request, 'robots.jinja', content_type='text/plain')


@short_circuit_middlewares
def sns_handler(request):
    if verify_sns_notification(request):
        content = json.loads(request.body.decode())
        message_type = request.META.get('HTTP_X_AMZ_SNS_MESSAGE_TYPE', None)

        if message_type == SNS_MESSAGE_TYPE_SUB_NOTIFICATION:
            urlopen(content['SubscribeURL'])
        elif message_type == SNS_MESSAGE_TYPE_NOTIFICATION:
            raven_client.context.activate()
            raven_client.context.merge({
                'extra': {
                    'notification': content,
                }
            })
            raven_client.captureMessage('Bounce notification')
            raven_client.context.clear()

    return HttpResponse(status=200)
