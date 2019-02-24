# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-05-05 11:20
# flake8: noqa
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0052_auto_20170505_0041'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificatetype',
            name='category',
            field=models.IntegerField(choices=[(0, 'Default'), (1, "Player's Club"), (2, 'Merchandise'), (3, 'Resort Stay'), (4, 'Rain Check'), (5, 'Prestige 50')], default=0),
        ),
    ]