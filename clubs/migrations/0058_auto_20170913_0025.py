# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-09-13 04:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clubs', '0057_auto_20170912_2006'),
    ]

    operations = [
        migrations.AddField(
            model_name='clubevent',
            name='registration_close_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='clubevent',
            name='registration_close_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='clubevent',
            name='registration_open_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='clubevent',
            name='registration_open_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
