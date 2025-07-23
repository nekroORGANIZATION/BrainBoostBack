from django.urls import path
from .views import ask_ai, course_recommendation_view

urlpatterns = [
    path('ask/', ask_ai, name='ask_ai'),
    path('recommend/', course_recommendation_view, name='course_recommendation'),
]
