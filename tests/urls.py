from django.urls import path
from .views import (
    TestListCreateView,
    TestRetrieveUpdateDestroyView,
    TestPublicDetailView,
    StartAttemptView,
    SubmitAttemptView,
    CreateTestView
)
from . import views

urlpatterns = [
    # CRUD для викладача
    path('', TestListCreateView.as_view(), name='test-list'),
    path('<int:pk>/', TestRetrieveUpdateDestroyView.as_view(), name='test-detail'),

    # Створення тесту через конструктор
    path('create/', CreateTestView.as_view(), name='test-create'),

    # Студентський флоу
    path('check/<int:lesson_id>/', views.check_lesson_test, name='check-lesson-test'),
    path('<int:pk>/public/', TestPublicDetailView.as_view(), name='test-public'),
    path('<int:pk>/attempts/start/', StartAttemptView.as_view(), name='attempt-start'),
    path('<int:pk>/attempts/<int:attempt_id>/submit/', SubmitAttemptView.as_view(), name='attempt-submit'),
    path('lessons/<int:lesson_id>/test/', views.lesson_test_by_lesson, name='lesson-test'),
]
