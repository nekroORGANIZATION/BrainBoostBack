from django.urls import path
from .views import (
    UnverifiedTeachersView,
    VerifyTeacherView,
    AllUsersView,
    TeacherDetailView,
    TeacherApplicationListView,
    TeacherApplicationApproveView,
    TeacherApplicationRejectView,
    TeacherApplicationCreateView,   # ✅ новый
)

urlpatterns = [
    # ==== Teachers / Users ====
    path('teachers/unverified/', UnverifiedTeachersView.as_view(), name='unverified-teachers'),
    path('teachers/verify/<int:user_id>/', VerifyTeacherView.as_view(), name='verify-teacher'),
    path('teachers/<int:user_id>/', TeacherDetailView.as_view(), name='teacher-detail'),
    path('users/all/', AllUsersView.as_view(), name='all-users'),

    # ==== Teacher applications ====
    path('teacher-applications/', TeacherApplicationListView.as_view(), name='teacher-applications'),   # список (только для админов)
    path('teacher-applications/create/', TeacherApplicationCreateView.as_view(), name='teacher-app-create'),  # ✅ новая точка для учителя
    path('teacher-applications/<int:pk>/approve/', TeacherApplicationApproveView.as_view(), name='teacher-app-approve'),
    path('teacher-applications/<int:pk>/reject/', TeacherApplicationRejectView.as_view(), name='teacher-app-reject'),
]
