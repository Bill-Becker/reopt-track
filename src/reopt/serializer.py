from rest_framework import serializers
from .models import RunData


class DataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunData
        fields = ("id", "name")
