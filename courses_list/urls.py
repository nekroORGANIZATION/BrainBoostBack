from django.urls import path
from .views import CourseListAPIView, CourseDetailAPIView

urlpatterns = [
    path('', CourseListAPIView.as_view(), name='course_list_api'),
    path('<int:course_id>/details/', CourseDetailAPIView.as_view(), name='course-detail'),
]
