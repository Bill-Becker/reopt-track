from django.core.exceptions import ValidationError
from django.db import models


class RunData(models.Model):

    name = models.CharField(default="", max_length=200, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    # TODO create a map for the analysis locations
    # TODO add geolocator to translate lat/long to city/country of analysis here
    run_country = models.CharField(max_length=200, null=True, blank=True)
    run_city = models.CharField(max_length=200, null=True, blank=True)


class RunMeta(models.Model):

    run_data = models.OneToOneField(
        RunData,
        on_delete=models.CASCADE,
        related_name="runmeta",
        null=True,
        blank=True,
    )
    webtool_run = models.BooleanField(default=False, null=True, blank=True)
    # TODO (maybe) make these uuid fields UUIDFields for Django's built-in validation
    webtool_user_uuid = models.TextField(default="", blank=True)
    webtool_portfolio_uuid = models.TextField(default="", blank=True)
    direct_api_run = models.BooleanField(default=False, null=True, blank=True)
    api_run_uuid = models.TextField(default="", blank=True)
    reoptjl_version = models.CharField(null=True, blank=True)
    STATUS_CHOICES = [
        ("optimal", "Optimal"),
        ("error", "Error"),
    ]
    status = models.CharField(
        max_length=200, choices=STATUS_CHOICES, null=True, blank=True
    )
    direct_reoptjl = models.BooleanField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    user_ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_country = models.CharField(max_length=200, null=True, blank=True)
    user_region = models.CharField(max_length=200, null=True, blank=True)
    user_city = models.CharField(max_length=200, null=True, blank=True)

    def clean(self, *args, **kwargs):
        if not self.webtool_run and not self.direct_api_run:
            self.direct_reoptjl = True
        elif self.webtool_run or self.direct_api_run:
            self.direct_reoptjl = False
        else:
            # This can't actually happen based on conditionals above
            raise ValidationError("Invalid state for direct_reoptjl")
        super(RunMeta, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.clean()
        super(RunMeta, self).save(*args, **kwargs)
