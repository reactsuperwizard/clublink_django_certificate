# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-27 00:07
# flake8: noqa
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0019_auto_20170226_1953'),
    ]

    operations = [
        migrations.AddField(
            model_name='certificatetype',
            name='dynamic_expiry',
            field=models.IntegerField(blank=True, choices=[(1, 'One year from creation')], null=True),
        ),
    ]
