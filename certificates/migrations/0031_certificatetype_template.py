# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-03-06 20:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0030_auto_20170306_0906'),
    ]

    operations = [
        migrations.AddField(
            model_name='certificatetype',
            name='template',
            field=models.IntegerField(choices=[(0, 'Default'), (1, 'AG30 Template')], default=0),
        ),
    ]