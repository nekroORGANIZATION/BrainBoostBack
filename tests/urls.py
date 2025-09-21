# tests/urls.py
from django.urls import path
from .views import (
    TestListCreateView, TestRetrieveUpdateDestroyView, TestPublicDetailView,
    StartAttemptView, SubmitAttemptView, CreateTestView,
    LessonTestByLessonView, check_lesson_test,
)

urlpatterns = [
    path('', TestListCreateView.as_view(), name='test-list'),
    path('<int:pk>/', TestRetrieveUpdateDestroyView.as_view(), name='test-detail'),
    path('create/', CreateTestView.as_view(), name='test-create'),

    path('<int:pk>/public/', TestPublicDetailView.as_view(), name='test-public'),
    path('<int:pk>/attempts/start/', StartAttemptView.as_view(), name='attempt-start'),
    path('<int:pk>/attempts/<int:attempt_id>/submit/', SubmitAttemptView.as_view(), name='attempt-submit'),

    path('lessons/<int:lesson_id>/test/', LessonTestByLessonView.as_view(), name='lesson-test'),
    path('check/<int:lesson_id>/', check_lesson_test, name='check-lesson-test'),
]
