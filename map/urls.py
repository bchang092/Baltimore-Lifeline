from django.contrib import admin
from django.urls import path, include
from .views import resources_map

urlpatterns = [
    path("", resources_map, name="resources_map")
]
