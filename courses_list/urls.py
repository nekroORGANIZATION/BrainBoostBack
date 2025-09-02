from django.urls import path
from .views import PublicCourseListAPIView, PublicCourseDetailAPIView

urlpatterns = [
    path("", PublicCourseListAPIView.as_view(), name="public-course-list"),
    path("<slug:slug>/", PublicCourseDetailAPIView.as_view(), name="public-course-detail"),
]
