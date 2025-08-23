from django.urls import path
from .views import (
    # teacher
    ModuleListCreateView, ModuleDetailView, ModuleReorderView,
    LessonListCreateView, LessonDetailView, LessonReorderView, LessonContentReorderView, LessonPublishView,
    # student
    LessonPublicDetailView, LessonProgressUpsertView,
    # simple
    SimpleLessonCreateView,
)

urlpatterns = [
    # новый эндпоинт для фронта
    path('lessons/', SimpleLessonCreateView.as_view(), name='lesson-simple-create'),

    # Modules (teacher)
    path('admin/modules/', ModuleListCreateView.as_view(), name='module-list'),
    path('admin/modules/reorder/', ModuleReorderView.as_view(), name='module-reorder'),
    path('admin/modules/<int:pk>/', ModuleDetailView.as_view(), name='module-detail'),

    # Lessons (teacher)
    path('admin/lessons/', LessonListCreateView.as_view(), name='lesson-list'),
    path('admin/lessons/reorder/', LessonReorderView.as_view(), name='lesson-reorder'),
    path('admin/lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('admin/lessons/<int:pk>/publish/', LessonPublishView.as_view(), name='lesson-publish'),
    path('admin/lessons/<int:lesson_id>/contents/reorder/', LessonContentReorderView.as_view(), name='lesson-content-reorder'),

    # Public (student)
    path('public/lessons/<slug:slug>/', LessonPublicDetailView.as_view(), name='lesson-public-detail'),
    path('progress/<int:lesson_id>/', LessonProgressUpsertView.as_view(), name='lesson-progress-upsert'),
]
