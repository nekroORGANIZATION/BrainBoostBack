from django.urls import path
from .views import UnverifiedTeachersView, VerifyTeacherView, AllUsersView, TeacherDetailView


urlpatterns = [
    path('teachers/unverified/', UnverifiedTeachersView.as_view(), name='unverified-teachers'),
    path('teachers/verify/<int:user_id>/', VerifyTeacherView.as_view(), name='verify-teacher'),
    path('teachers/<int:user_id>/', TeacherDetailView.as_view(), name='teacher-detail'),

    path('users/all/', AllUsersView.as_view(), name='all-users'),
]
