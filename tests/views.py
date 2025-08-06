from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Test, Question, Choice, Answer
from .serializers import TestSerializer, QuestionSerializer, ChoiceSerializer, AnswerSerializer
from django.shortcuts import get_object_or_404

class TestListCreateView(generics.ListCreateAPIView):
    queryset = Test.objects.all()
    serializer_class = TestSerializer

class TestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Test.objects.all()
    serializer_class = TestSerializer

class QuestionListCreateView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

class QuestionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

class ChoiceListCreateView(generics.ListCreateAPIView):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer

class ChoiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer

class AnswerListCreateView(generics.ListCreateAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer

class SubmitAnswersView(APIView):
    def post(self, request):
        user_identifier = request.data.get('user_identifier')
        answers = request.data.get('answers', [])
        saved_answers = []
        for ans in answers:
            question = get_object_or_404(Question, id=ans.get('question_id'))
            if question.question_type == 'MC':
                choice = get_object_or_404(Choice, id=ans.get('selected_choice'))
                answer = Answer.objects.create(
                    question=question,
                    user_identifier=user_identifier,
                    selected_choice=choice
                )
            elif question.question_type == 'TF':
                answer = Answer.objects.create(
                    question=question,
                    user_identifier=user_identifier,
                    is_true_false=ans.get('is_true_false')
                )
            elif question.question_type == 'TXT':
                answer = Answer.objects.create(
                    question=question,
                    user_identifier=user_identifier,
                    text_answer=ans.get('text_answer')
                )
            saved_answers.append(AnswerSerializer(answer).data)
        return Response({'saved_answers': saved_answers}, status=status.HTTP_201_CREATED)