from django.core.management.base import BaseCommand

from clublink.base.clients.ibs import WebMemberClient
from clublink.clubs.models import Department


class Command(BaseCommand):
    """
    Adds some helpful initial data to the site's database. If matching
    data already exists, it should _not_ be overwritten, making this
    safe to run multiple times.
    """
    help = 'Adds initial club data to database'

    def handle(self, *args, **options):
        client = WebMemberClient()
        departments = client.get_retail_departments()

        for d in departments:
            department, _ = Department.objects.update_or_create(id=d['guid'], defaults={
                'number': d['code'],
                'name': d['description'],
            })
