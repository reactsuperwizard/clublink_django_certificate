# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-06-26 01:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0019_corpweddinggalleryimage'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CorpWeddingGallery',
            new_name='CorpEventsGallery',
        ),
        migrations.RenameModel(
            old_name='CorpWeddingGalleryImage',
            new_name='CorpEventsGalleryImage',
        ),
    ]
