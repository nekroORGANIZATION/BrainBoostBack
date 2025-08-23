from django.urls import path
from .views import (
    TestListCreateView,
    TestRetrieveUpdateDestroyView,
    TestPublicDetailView,
    StartAttemptView,
    SubmitAttemptView,
)

urlpatterns = [
    # CRUD для викладача
    path('', TestListCreateView.as_view(), name='test-list'),
    path('<int:pk>/', TestRetrieveUpdateDestroyView.as_view(), name='test-detail'),

    # Студентський флоу
    path('<int:pk>/public/', TestPublicDetailView.as_view(), name='test-public'),
    path('<int:pk>/attempts/start/', StartAttemptView.as_view(), name='attempt-start'),
    path('<int:pk>/attempts/<int:attempt_id>/submit/', SubmitAttemptView.as_view(), name='attempt-submit'),
]
