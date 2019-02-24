# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-15 05:16
# flake8: noqa
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20170215_0439'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='billing_address',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='billing_profile', to='users.Address'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='mailing_address',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mailing_profile', to='users.Address'),
        ),
    ]
