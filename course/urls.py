from django.urls import path
from .views import (
    CourseListCreateView, CourseDetailView, CommentListCreateView,
    CourseUpdateView, CourseDeleteView, CommentRetrieveUpdateDestroyView
)


urlpatterns = [
    path('', CourseListCreateView.as_view(), name='course-list-create'),
    path('<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    path('<int:pk>/edit/', CourseUpdateView.as_view(), name='course-edit'),
    path('<int:pk>/delete/', CourseDeleteView.as_view(), name='course-delete'),

    path('<int:course_pk>/comments/', CommentListCreateView.as_view(), name='comment-list-create'),
    path('<int:course_pk>/comments/<int:pk>/', CommentRetrieveUpdateDestroyView.as_view(), name='comment-detail'),
]
