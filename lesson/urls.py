from django.urls import path
from .views import (
    LessonListCreateView, LessonDetailView, LessonUpdateView, LessonDeleteView,
    CourseTheoryListCreateView, CourseTheoryDetailView,
    TestQuestionListCreateView, TestQuestionDetailView,
    TestAnswerListCreateView, TestAnswerDetailView,
    TrueFalseQuestionListCreateView, TrueFalseQuestionDetailView,
    OpenQuestionListCreateView, OpenQuestionDetailView, TestListCreateView, TestDetailView
)

urlpatterns = [
    path('lessons/', LessonListCreateView.as_view(), name='lesson-list-create'),
    path('lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('lessons/<int:pk>/edit/', LessonUpdateView.as_view(), name='lesson-edit'),
    path('lessons/<int:pk>/delete/', LessonDeleteView.as_view(), name='lesson-delete'),

    path('theories/', CourseTheoryListCreateView.as_view(), name='theory-list-create'),
    path('theories/<int:pk>/', CourseTheoryDetailView.as_view(), name='theory-detail'),

    path('test-questions/', TestQuestionListCreateView.as_view(), name='test-question-list-create'),
    path('test-questions/<int:pk>/', TestQuestionDetailView.as_view(), name='test-question-detail'),

    path('test-answers/', TestAnswerListCreateView.as_view(), name='test-answer-list-create'),
    path('test-answers/<int:pk>/', TestAnswerDetailView.as_view(), name='test-answer-detail'),

    path('true-false-questions/', TrueFalseQuestionListCreateView.as_view(), name='tf-question-list-create'),
    path('true-false-questions/<int:pk>/', TrueFalseQuestionDetailView.as_view(), name='tf-question-detail'),

    path('open-questions/', OpenQuestionListCreateView.as_view(), name='open-question-list-create'),
    path('open-questions/<int:pk>/', OpenQuestionDetailView.as_view(), name='open-question-detail'),

    path('tests/', TestListCreateView.as_view(), name='test-list-create'),
    path('tests/<int:pk>/', TestDetailView.as_view(), name='test-detail'),

]
