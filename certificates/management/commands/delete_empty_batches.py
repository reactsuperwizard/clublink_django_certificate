from django.core.management.base import BaseCommand
from django.db.models import Count

from clublink.certificates.models import CertificateBatch


class Command(BaseCommand):
    """
    Delete batches that have no certificates.
    """
    help = 'Delete batches that have no certificates'

    def handle(self, *args, **options):
        batches = CertificateBatch.objects.annotate(
            certificate_count=Count('certificates')).filter(certificate_count=0)
        batches.delete()
