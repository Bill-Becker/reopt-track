from django.urls import path

from reopt import views

urlpatterns = [
    path("", views.getData, name="get"),
    path("post/", views.postRun, name="post")
]
