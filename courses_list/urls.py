from django.urls import path
from .views import (
    CourseListAPIView,
    CourseDetailAPIView,
    CourseUpdateAPIView,
    CourseDeleteAPIView,
    UserMeAPIView,
    CategoryListAPIView,
)

urlpatterns = [
    path('', CourseListAPIView.as_view(), name='course-list'),
    path('<int:course_id>/', CourseDetailAPIView.as_view(), name='course-detail'),
    path('<int:course_id>/edit/', CourseUpdateAPIView.as_view(), name='course-update'),
    path('<int:course_id>/delete/', CourseDeleteAPIView.as_view(), name='course-delete'),
    path('categories/', CategoryListAPIView.as_view(), name='category-list'),
    path('users/me/', UserMeAPIView.as_view(), name='user-me'),
]
