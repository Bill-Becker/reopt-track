# from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import RunMeta
from .serializer import RunMetaSerializer
# from django.core.exceptions import ValidationError


# Create your views here.
@api_view(["GET"])
def getData(request):
    # Serialize the data from the database into dict/JSON
    # The run_data is included in the run_meta objects, so we just have to serialize run_meta
    if request.query_params.get("run_meta_id"):
        run_meta = RunMeta.objects.get(id=request.query_params.get("run_meta_id"))
        run_meta_serialized = RunMetaSerializer(run_meta)
    else:
        all_meta = RunMeta.objects.all()
        run_meta_serialized = RunMetaSerializer(all_meta, many=True)
    
    return Response(run_meta_serialized.data)


@api_view(["POST"])
def postRun(request):
    # De-serialize the data from the request into python/model objects
    # The DRF Serializer validates the data before saving it to the database and handles errors
    run_meta_serializer = RunMetaSerializer(data=request.data)
    if run_meta_serializer.is_valid():
        run_meta_serializer.save()
        return Response({"run_meta_id": run_meta_serializer.data["id"]}, status=201)
    return Response(run_meta_serializer.errors, status=400)

@api_view(["PATCH"])
def updateRun(request):
    try:
        run_meta = RunMeta.objects.get(id=request.query_params.get("run_meta_id"))
    except RunMeta.DoesNotExist:
        return Response({"error": "RunMeta not found"}, status=404)

    run_meta_serializer = RunMetaSerializer(run_meta, data=request.data, partial=True)
    if run_meta_serializer.is_valid():
        run_meta_serializer.save()
        return Response(run_meta_serializer.data, status=200)
    return Response(run_meta_serializer.errors, status=400)