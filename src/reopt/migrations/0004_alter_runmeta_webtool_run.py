# Generated by Django 5.1.3 on 2025-02-01 04:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "reopt",
            "0003_rename_battery_size_rundata_battery_energy_size_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="runmeta",
            name="webtool_run",
            field=models.BooleanField(
                blank=True, default=False, editable=False, null=True
            ),
        ),
    ]
