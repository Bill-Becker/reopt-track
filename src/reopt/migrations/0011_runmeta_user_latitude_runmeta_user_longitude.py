# Generated by Django 5.1.3 on 2025-02-17 04:44

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        (
            "reopt",
            "0007_rename_city_rundata_run_city_and_more_squashed_0010_runmeta_user_region",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="runmeta",
            name="user_latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="runmeta",
            name="user_longitude",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
