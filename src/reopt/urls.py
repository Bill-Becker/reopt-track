from django.urls import path

from reopt import views

urlpatterns = [
    path("", views.dashboard, name="reopt_dashboard"),
    path("get/", views.getData, name="reopt_get"),
    path("post/", views.postRun, name="reopt_post"),
    path("update/", views.updateRun, name="reopt_update"),
]
