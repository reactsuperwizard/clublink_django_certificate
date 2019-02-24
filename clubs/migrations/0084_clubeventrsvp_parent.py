# Generated by Django 2.0.2 on 2018-03-09 13:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clubs', '0083_auto_20180309_0324'),
    ]

    operations = [
        migrations.AddField(
            model_name='clubeventrsvp',
            name='parent',
            field=models.ForeignKey(blank=True, help_text='Who did the original RSVP?', null=True, on_delete=django.db.models.deletion.CASCADE, to='clubs.ClubEventRSVP'),
        ),
    ]
