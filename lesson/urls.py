from django.urls import path
from .views import (
    # teacher
    ModuleListCreateView, ModuleDetailView, ModuleReorderView,
    LessonListCreateView, LessonDetailView, LessonReorderView, LessonContentReorderView, LessonPublishView,
    # student
    LessonPublicDetailView, LessonProgressUpsertView, LessonPublicDetailViewById,
    # simple
    SimpleLessonCreateView, MyLessonsListView, LessonTheoryView, LessonsByCourseView
)
from . import views

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
    path('public/lessons/<int:id>/', LessonPublicDetailView.as_view(), name='lesson-public-detail'),
    path('public/lessons/id/<int:lesson_id>/', LessonPublicDetailViewById.as_view(), name='lesson-public-detail-id'),
    path('lessons/<int:lesson_id>/theory/', views.lesson_theory),
    path('progress/<int:lesson_id>/', LessonProgressUpsertView.as_view(), name='lesson-progress-upsert'),

    path('lessons/mine/', MyLessonsListView.as_view(), name='lesson-mine'),
    path('courses/<int:course_id>/lessons/', LessonsByCourseView.as_view(), name='course-lessons'),
    # Теорія уроку
    path('lesson/theories/<int:lesson_id>/', LessonTheoryView.as_view(), name='lesson-theory-list'),
    path('lesson/theories/<int:lesson_id>/<int:theory_id>/', LessonTheoryView.as_view(), name='lesson-theory-detail'),
]
