from django.contrib import admin

from .models import RunData
from .models import RunMeta

# Register your models here.
admin.site.register(RunMeta)
admin.site.register(RunData)
