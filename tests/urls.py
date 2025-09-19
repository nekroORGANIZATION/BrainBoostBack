from django.urls import path
from .views import (
    TestListCreateView,
    TestRetrieveUpdateDestroyView,
    TestPublicDetailView,
    StartAttemptView,
    SubmitAttemptView,
    CreateTestView,
    lesson_test_by_lesson,
    check_lesson_test,
)

urlpatterns = [
    # Teacher CRUD
    path('', TestListCreateView.as_view(), name='test-list'),
    path('<int:pk>/', TestRetrieveUpdateDestroyView.as_view(), name='test-detail'),
    path('create/', CreateTestView.as_view(), name='test-create'),

    # Student flow
    path('<int:pk>/public/', TestPublicDetailView.as_view(), name='test-public'),
    path('<int:pk>/attempts/start/', StartAttemptView.as_view(), name='attempt-start'),
    path('<int:pk>/attempts/<int:attempt_id>/submit/', SubmitAttemptView.as_view(), name='attempt-submit'),

    # Lesson helpers
    path('lessons/<int:lesson_id>/test/', lesson_test_by_lesson, name='lesson-test'),
    path('check/<int:lesson_id>/', check_lesson_test, name='check-lesson-test'),
]
