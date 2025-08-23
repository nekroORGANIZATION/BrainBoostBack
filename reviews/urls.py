from django.urls import path
from .views import (
    ReviewListAPIView,
    ReviewCreateAPIView,
    MyReviewsAPIView,
    ReviewModerationAPIView,
    ReviewSummaryAPIView,
    # NEW:
    ReviewAdminListAPIView,
    ReviewPendingListAPIView,
)

urlpatterns = [
    path('', ReviewListAPIView.as_view(), name='review-list'),
    path('create/', ReviewCreateAPIView.as_view(), name='review-create'),
    path('mine/', MyReviewsAPIView.as_view(), name='review-mine'),
    path('<int:pk>/moderate/', ReviewModerationAPIView.as_view(), name='review-moderate'),
    path('summary/', ReviewSummaryAPIView.as_view(), name='review-summary'),

    # NEW:
    path('admin/', ReviewAdminListAPIView.as_view(), name='review-admin-list'),
    path('pending/', ReviewPendingListAPIView.as_view(), name='review-pending-list'),
]

