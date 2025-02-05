from django.db import connection
from django.http import HttpResponse


def index(request):
    return HttpResponse("")


def databases(request):
    connection.ensure_connection()

    return HttpResponse("")
