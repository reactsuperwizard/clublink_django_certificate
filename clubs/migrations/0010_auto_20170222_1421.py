# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-22 14:21
# flake8: noqa
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clubs', '0009_auto_20170216_2302'),
    ]

    operations = [
        migrations.AlterField(
            model_name='club',
            name='slug',
            field=models.CharField(max_length=64, null=True, unique=True),
        ),
    ]