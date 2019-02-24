# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-06-25 05:14
# flake8: noqa

from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0017_clubpage_visibility'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorpWeddingGallery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.CharField(max_length=64)),
                ('sort', models.IntegerField(default=0)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ('sort', '-id'),
            },
        ),
        migrations.AlterUniqueTogether(
            name='corpweddinggallery',
            unique_together=set([('slug',)]),
        ),
    ]
