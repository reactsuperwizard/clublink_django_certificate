# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-08-07 19:10
# flake8: noqa
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0059_auto_20170807_1316'),
    ]

    operations = [
        migrations.AddField(
            model_name='clubpage',
            name='alias',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='aliases', to='cms.ClubPage'),
        ),
    ]
