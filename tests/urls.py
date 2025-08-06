from django.urls import path
from .views import *

urlpatterns = [
    path('tests/', TestListCreateView.as_view()),
    path('tests/<int:pk>/', TestRetrieveUpdateDestroyView.as_view()),
    path('questions/', QuestionListCreateView.as_view()),
    path('questions/<int:pk>/', QuestionRetrieveUpdateDestroyView.as_view()),
    path('choices/', ChoiceListCreateView.as_view()),
    path('choices/<int:pk>/', ChoiceRetrieveUpdateDestroyView.as_view()),
    path('answers/', AnswerListCreateView.as_view()),
    path('submit-answers/', SubmitAnswersView.as_view()),
]