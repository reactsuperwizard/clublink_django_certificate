import json
import re

from base64 import b64decode
from binascii import a2b_base64
from urllib.request import urlopen

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Util.asn1 import DerSequence
from django.core.cache import cache


SNS_CERT_URL_RE = r'^https:\/\/[^\/]+amazonaws\.com\/'

SNS_MESSAGE_TYPE_SUB_NOTIFICATION = 'SubscriptionConfirmation'
SNS_MESSAGE_TYPE_NOTIFICATION = 'Notification'
SNS_MESSAGE_TYPE_UNSUB_NOTIFICATION = 'UnsubscribeConfirmation'

SNS_MESSAGE_TYPES_SUBSCRIPTION = [SNS_MESSAGE_TYPE_SUB_NOTIFICATION,
                                  SNS_MESSAGE_TYPE_UNSUB_NOTIFICATION]


def canonical_message_builder(content, format):
    m = ''

    for field in sorted(format):
        try:
            m += field + '\n' + content[field] + '\n'
        except KeyError:
            pass

    return str(m)


def get_rsa_key(cert_data):
    pem = cert_data
    lines = pem.replace(' ', '').split()
    der = a2b_base64(''.join(lines[1:-1]))

    # Extract subjectPublicKeyInfo field from X.509 certificate (see RFC3280)
    cert = DerSequence()
    cert.decode(der)
    tbsCertificate = DerSequence()
    tbsCertificate.decode(cert[0])
    subjectPublicKeyInfo = tbsCertificate[6]

    return RSA.importKey(subjectPublicKeyInfo)


def verify_sns_notification(request):
    canonical_sub_unsub_format = ['Message', 'MessageId', 'SubscribeURL', 'Timestamp', 'Token',
                                  'TopicArn', 'Type']
    canonical_notification_format = ['Message', 'MessageId', 'Subject', 'Timestamp', 'TopicArn',
                                     'Type']

    try:
        content = json.loads(request.body.decode())
    except json.JSONDecodeError:
        return False

    decoded_signature = b64decode(content['Signature'])

    if request.META.get('HTTP_X_AMZ_SNS_MESSAGE_TYPE', None) in SNS_MESSAGE_TYPES_SUBSCRIPTION:
        canonical_message = canonical_message_builder(content, canonical_sub_unsub_format)
    elif request.META.get('HTTP_X_AMZ_SNS_MESSAGE_TYPE', None) == SNS_MESSAGE_TYPE_NOTIFICATION:
        canonical_message = canonical_message_builder(content, canonical_notification_format)
    else:
        raise ValueError('Message Type ({}) is not recognized'.format(
            request.META.get('HTTP_X_AMZ_SNS_MESSAGE_TYPE', None)))

    cert_url = content['SigningCertURL']
    if not re.search(SNS_CERT_URL_RE, cert_url):
        raise ValueError('Invalid signing certificate ({}).'.format(cert_url))

    cache_key = 'SNS_CERT_{}'.format(cert_url)
    cert_data = cache.get(cache_key)
    if not cert_data:
        cert_data = urlopen(cert_url).read().decode()
        cache.set(cache_key, cert_data)

    rsa_key = get_rsa_key(cert_data)
    signer = PKCS1_v1_5.new(rsa_key)
    digest = SHA.new()

    digest.update(canonical_message.encode())

    return signer.verify(digest, decoded_signature)
