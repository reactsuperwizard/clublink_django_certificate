from django.core.management.base import BaseCommand

from clublink.certificates.models import CertificateBatch
from clublink.certificates.utils import send_certificate_batch_email


class Command(BaseCommand):
    """
    Send the certificate batch email to an email address.
    """
    help = 'Send the certificate batch email.'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs=1, type=int)
        parser.add_argument('-e', '--recipient-email', nargs='?')
        parser.add_argument('-u', '--url', nargs='?')
        parser.add_argument('--skip-bcc', nargs='?', const=True)

    def handle(self, *args, **options):
        batch_id = options.pop('id')[0]
        try:
            batch = CertificateBatch.objects.get(pk=batch_id)
        except CertificateBatch.DoesNotExist:
            print('Invalid certificate batch.')
        else:
            base_url = options.pop('url')
            if base_url:
                send_certificate_batch_email(options.get('url'), batch, **options)
            else:
                print('URL is required.')
