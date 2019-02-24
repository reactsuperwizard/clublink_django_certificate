import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from clublink.clubs.models import Club


class Command(BaseCommand):
    """
    Adds some helpful initial data to the site's database. If matching
    data already exists, it should _not_ be overwritten, making this
    safe to run multiple times.
    """
    help = 'Adds initial club data to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            dest='update',
            default=False,
            help='Overwrites existing data with fixture data',
        )

    def handle(self, *args, **options):
        with open(os.path.join(settings.BASE_DIR, 'fixtures/clubs.json'), mode='r') as f:
            clubs = json.loads(f.read())
            for club in clubs:
                kwargs = {
                    'code': club['code'],
                    'defaults': {
                        'name': club['name']
                    }
                }

                if options.get('update'):
                    Club.objects.update_or_create(**kwargs)
                else:
                    Club.objects.get_or_create(**kwargs)
