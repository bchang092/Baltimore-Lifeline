from django.contrib import admin
from django.urls import path, include
from .views import (
    resources_map,
    home_page,
    questionnaire_page,
    actions_page,
    about_page,
    community_page,
    feature_detail_page,
    ping,
)

urlpatterns = [
    path("",home_page, name = "homepage"),
    path("actions/", actions_page, name="actions"),
    path("about/", about_page, name="about"),
    path("community/", community_page, name="community"),
    path("features/<slug:slug>/", feature_detail_page, name="feature_detail"),
    path("questionnaire/", questionnaire_page, name="questionnaire"),
    path("ping/", ping),
    path("map/", resources_map, name="resources_map")
    
]
