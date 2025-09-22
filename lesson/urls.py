from django.urls import path
from .views import (
    CourseLessonsWithProgressView,
    # modules
    ModuleListCreateView, ModuleDetailView, ModuleReorderView, CourseModulesView,
    # lessons
    LessonListCreateView, LessonDetailView, LessonReorderView,
    LessonBlockListCreateView, LessonBlockDetailView, LessonBlockReorderView,
    LessonPublishView,
    # public & progress
    LessonPublicDetailView, LessonPublicDetailViewById,
    LessonProgressUpsertView, LessonsByCourseView,
    # legacy theories
    LessonTheoryView, lesson_theory,
)

urlpatterns = [
    # -------- Modules (teacher)
    path('admin/modules/', ModuleListCreateView.as_view(), name='module-list'),
    path('admin/modules/reorder/', ModuleReorderView.as_view(), name='module-reorder'),
    path('admin/modules/<int:pk>/', ModuleDetailView.as_view(), name='module-detail'),

    # -------- Lessons (teacher)
    path('admin/lessons/', LessonListCreateView.as_view(), name='lesson-list'),
    path('admin/lessons/reorder/', LessonReorderView.as_view(), name='lesson-reorder'),
    path('admin/lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('admin/lessons/<int:pk>/publish/', LessonPublishView.as_view(), name='lesson-publish'),

    # Blocks (teacher)
    path('admin/lessons/<int:lesson_id>/blocks/', LessonBlockListCreateView.as_view(), name='lesson-blocks'),
    path('admin/lessons/<int:lesson_id>/blocks/reorder/', LessonBlockReorderView.as_view(), name='lesson-blocks-reorder'),
    path('admin/lessons/<int:lesson_id>/blocks/<int:block_id>/', LessonBlockDetailView.as_view(), name='lesson-block-detail'),

    # -------- Public (student)
    path('public/lessons/<int:id>/', LessonPublicDetailView.as_view(), name='lesson-public-detail'),
    path('public/lessons/id/<int:lesson_id>/', LessonPublicDetailViewById.as_view(), name='lesson-public-detail-id'),
    path('courses/<int:course_id>/lessons/', CourseLessonsWithProgressView.as_view(), name='course-lessons'),
     path('courses/<int:course_id>/modules/', CourseModulesView.as_view(), name='course-modules'),  # 👈 новий

    # -------- Progress
    path('progress/<int:lesson_id>/', LessonProgressUpsertView.as_view(), name='lesson-progress-upsert'),

    # -------- Legacy/compat «theories»
    path('lesson/theories/<int:lesson_id>/', LessonTheoryView.as_view(), name='lesson-theory-list'),
    path('lesson/theories/<int:lesson_id>/<int:theory_id>/', LessonTheoryView.as_view(), name='lesson-theory-detail'),
    path('lessons/<int:lesson_id>/theory/', lesson_theory, name='lesson-theory-legacy'),
]