from django.db import models
from django.core.exceptions import ValidationError
# import requests

# TODO make sure RunMeta fields are really Meta, and RunData fields are really run data
class RunData(models.Model):
    
    name = models.CharField(default="", max_length=200, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    # TODO add geolocator to translate lat/long to city/country
    country = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    pv_size = models.FloatField(null=True, blank=True)
    battery_size = models.FloatField(null=True, blank=True)


class RunMeta(models.Model):

    run_data = models.OneToOneField(RunData, on_delete=models.CASCADE, related_name='runmeta', null=True, blank=True)
    webtool_uuid = models.TextField(default="", blank=True, editable=False)
    user_uuid = models.TextField(default="", blank=True, editable=False)
    portfolio_uuid = models.TextField(default="", blank=True, editable=False)
    run_uuid = models.TextField(default="", blank=True, editable=False)
    api_version = models.CharField(null=True, blank=True)
    reoptjl_version = models.CharField(null=True, blank=True)
    STATUS_CHOICES = [
        ('optimal', 'Optimal'),
        ('error', 'Error'),
    ]
    status = models.CharField(max_length=200, choices=STATUS_CHOICES, null=True, blank=True)
    direct_reoptjl = models.BooleanField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def clean(self, *args, **kwargs):
        if self.webtool_uuid == "" and self.run_uuid == "":
            self.direct_reoptjl = True
        elif self.webtool_uuid != "" or self.run_uuid != "":
            self.direct_reoptjl = False
        else:
            # This can't actually happen based on conditionals above
            raise ValidationError("Invalid state for direct_reoptjl")
        super(RunMeta, self).clean(*args, **kwargs)


# TODO get user's location from IP address contained in headers (maybe), but this may require permissions
# Google Geolocation API (not the one below) is subscription based, but NREL might have an account?
# def get_user_location(ip_address):
#     api_key = "YOUR_API_KEY"  # Replace with your geolocation API key
#     url = f"https://api.ipgeolocation.io/v1/YOUR_API_KEY?apiKey={api_key}&ip={ip_address}"
#     response = requests.get(url)
#     location_data = response.json()

#     return location_data

# def get_user_ip(request):
#     x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#     if x_forwarded_for:
#         ip = x_forwarded_for.split(',')[0]
#     else:
#         ip = request.META.get('REMOTE_ADDR')
#     return ip

# def get_user_location_from_request(request):
#     ip = get_user_ip(request)
#     location_data = get_user_location(ip)
#     print(f"User location: {location_data['city']}, {location_data['country']}")
#     return location_data