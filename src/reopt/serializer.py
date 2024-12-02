from rest_framework import serializers
from .models import RunMeta, RunData


class RunDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunData
        fields = "__all__"
        # exclude = (
        #     "run_meta",
        # )


class RunMetaSerializer(serializers.ModelSerializer):
    run_data = RunDataSerializer()

    class Meta:
        model = RunMeta
        fields = "__all__"
        # depth = 1

    def create(self, validated_data):
        run_data_data = validated_data.pop("run_data")
        run_data = RunData.objects.create(**run_data_data)
        run_meta = RunMeta.objects.create(run_data=run_data, **validated_data)
        return run_meta
    
    def update(self, instance, validated_data):
        run_data_data = validated_data.pop("run_data", None)

        if run_data_data:
            run_data = instance.run_data
            for attr, value in run_data_data.items():
                setattr(run_data, attr, value)
            run_data.save()

        return super().update(instance, validated_data)
