from django.contrib import admin
from django.urls import path, include
from .views import resources_map, home_page,ping

urlpatterns = [
    path("",home_page, name = "homepage"),
    path("ping/", ping),
    path("map/", resources_map, name="resources_map")
    
]
