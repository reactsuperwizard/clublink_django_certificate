import io
import os

from uuid import uuid4

from PIL import Image

from django.conf import settings
from django.core.files.storage import default_storage
from django.http.request import split_domain_port
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.http import is_same_domain
from django.contrib.sessions.backends.base import UpdateError
from django import template



### This was failing on the data migration, so I just moved it over to a util that can be run

def create_off_premise_group():
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    from django.contrib.auth.models import Group
    from clublink.certificates.models import Certificate
    content_type = ContentType.objects.get_for_model(Certificate)
    off_prem_perm, created = Permission.objects.get_or_create(
        name='Can login off premise',
        content_type=content_type,
        codename='can_login_off_premise')
    off_prem_group, created = Group._default_manager.get_or_create(
        name='Off-premise Access')
    off_prem_group.permissions.add(off_prem_perm)


from shared_session.templatetags.shared_session import LoaderNode

class CustomLoaderNode(LoaderNode):

    def render(self, context):
        request = context['request']

        if request.session.is_empty():
            return ''

        try:
            self.ensure_session_key(request)

            return self.template.render(
                template.Context({
                    'domains': [
                        self.build_url(
                            domain='https://{}'.format(domain),
                            message=self.get_message(request, domain))
                        for domain in self.get_domains(request)
                    ]
                }))
        except UpdateError:
            return ''

    def get_message(self, request, domain):
        return super(CustomLoaderNode, self).get_message(request, domain).decode()


@deconstructible
class RandomizedUploadPath(object):
    def __init__(self, prefix=''):
        self.prefix = prefix

    def __call__(self, instance, filename):
        ext = filename.split('.').pop()
        return os.path.join(self.prefix, '{}.{}'.format(uuid4(), ext))


def today():
    return timezone.localtime(timezone.now()).date()


def sanitize_string(string):
    """Strips extra whitespace and carriage returns."""
    string = string.strip()
    string = string.replace('\r\n', '\n')
    string = string.replace('\r', '')
    return string


def get_matching_allowed_host(host):
    """Find the first host in ALLOWED_HOSTS that matches the provided host."""
    host, port = split_domain_port(host)
    host = host[:-1] if host.endswith('.') else host

    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
    for pattern in allowed_hosts:
        if is_same_domain(host, pattern):
            return pattern

    return None


def set_multidomain_cookie(request, response, *args, **kwargs):
    """A proxy for response.set_cookie that sets the domain correctly from ALLOWED_HOSTS."""
    config = {
        'secure': getattr(settings, 'SESSION_COOKIE_SECURE', False)
    }
    config.update(kwargs)
    domain = get_matching_allowed_host(request.get_host())
    config['domain'] = domain
    response.set_cookie(*args, **config)


def list_intersect(a, b):
    return list(set(a) & set(b))


def list_union(a, b):
    return list(set(a) | set(b))


def optimize_jpeg(image, max_size=(1920, 1080)):
    # Open image to memory
    with default_storage.open(image.name, 'rb') as image_file:
        input_buffer = io.BytesIO(image_file.read())
        input_buffer.seek(0)

    # Optimize the image
    optimized = Image.open(input_buffer)
    optimized.thumbnail(max_size, Image.ANTIALIAS)

    # Save the image to memory
    output_buffer = io.BytesIO()
    optimized.save(output_buffer, 'JPEG', quality=60, optimize=True, progressive=True)
    output_buffer.seek(0)

    # Write the optimized image to storage
    with default_storage.open(image.name, 'wb') as image_file:
        image_file.write(output_buffer.getvalue())

    input_buffer.close()
    output_buffer.close()
