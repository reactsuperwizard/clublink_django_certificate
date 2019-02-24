from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

class NoQueryStringMixin:
    querystring_auth = settings.AWS_QUERYSTRING_AUTH

class S3Boto3StorageStatic(NoQueryStringMixin, S3Boto3Storage):
    location = getattr(settings, 'STATICFILES_LOCATION', 'static')


class S3Boto3StorageMedia(NoQueryStringMixin, S3Boto3Storage):
    location = getattr(settings, 'MEDIA_LOCATION', 'media')


class S3Boto3StorageAssets(NoQueryStringMixin, S3Boto3Storage):
    location = getattr(settings, 'ASSETS_LOCATION', 'assets')