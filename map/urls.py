from django.contrib import admin
from django.urls import path, include
from .views import resources_map, home_page, questionnaire_page, actions_page, about_page, ping

urlpatterns = [
    path("",home_page, name = "homepage"),
    path("actions/", actions_page, name="actions"),
    path("about/", about_page, name="about"),
    path("questionnaire/", questionnaire_page, name="questionnaire"),
    path("ping/", ping),
    path("map/", resources_map, name="resources_map")
    
]
