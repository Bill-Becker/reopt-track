# Generated by Django 5.1.3 on 2025-02-08 04:41

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    replaces = [
        ("reopt", "0007_rename_city_rundata_run_city_and_more"),
        ("reopt", "0008_runmeta_user_ip_address"),
        ("reopt", "0009_runmeta_user_city_runmeta_user_country"),
        ("reopt", "0010_runmeta_user_region"),
    ]

    dependencies = [
        ("reopt", "0006_runmeta_direct_api_run"),
    ]

    operations = [
        migrations.RenameField(
            model_name="rundata",
            old_name="city",
            new_name="run_city",
        ),
        migrations.RenameField(
            model_name="rundata",
            old_name="country",
            new_name="run_country",
        ),
        migrations.RemoveField(
            model_name="rundata",
            name="battery_energy_size",
        ),
        migrations.RemoveField(
            model_name="rundata",
            name="battery_power_size",
        ),
        migrations.RemoveField(
            model_name="rundata",
            name="pv_size",
        ),
        migrations.AddField(
            model_name="runmeta",
            name="user_ip_address",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="runmeta",
            name="user_city",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="runmeta",
            name="user_country",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="runmeta",
            name="user_region",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
