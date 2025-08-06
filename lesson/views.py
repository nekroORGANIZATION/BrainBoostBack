from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import (
    Lesson, CourseTheory, TestQuestion,
    TestAnswer, TrueFalseQuestion, OpenQuestion, Test,
    TestAttempt, QuestionAttempt
)
from .serializers import (
    LessonSerializer, CourseTheorySerializer, TestQuestionSerializer,
    TestAnswerSerializer, TrueFalseQuestionSerializer, OpenQuestionSerializer, TestSerializer,
    TestAttemptSerializer
)


# ------------------ TEST ------------------
class TestListCreateView(generics.ListCreateAPIView):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [permissions.AllowAny]


class TestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [permissions.AllowAny]


# ------------------ LESSON ------------------
class LessonListCreateView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]


class LessonDetailView(generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]


class LessonUpdateView(generics.UpdateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]


class LessonDeleteView(generics.DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]


# ------------------ COURSE THEORY ------------------
class CourseTheoryListCreateView(generics.ListCreateAPIView):
    queryset = CourseTheory.objects.all()
    serializer_class = CourseTheorySerializer
    permission_classes = [permissions.AllowAny]


class CourseTheoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CourseTheory.objects.all()
    serializer_class = CourseTheorySerializer
    permission_classes = [permissions.AllowAny]


# ------------------ TEST QUESTION ------------------
class TestQuestionListCreateView(generics.ListCreateAPIView):
    queryset = TestQuestion.objects.all()
    serializer_class = TestQuestionSerializer
    permission_classes = [permissions.AllowAny]


class TestQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestQuestion.objects.all()
    serializer_class = TestQuestionSerializer
    permission_classes = [permissions.AllowAny]


# ------------------ TEST ANSWER ------------------
class TestAnswerListCreateView(generics.ListCreateAPIView):
    queryset = TestAnswer.objects.all()
    serializer_class = TestAnswerSerializer
    permission_classes = [permissions.AllowAny]


class TestAnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestAnswer.objects.all()
    serializer_class = TestAnswerSerializer
    permission_classes = [permissions.AllowAny]


# ------------------ TRUE/FALSE QUESTION ------------------
class TrueFalseQuestionListCreateView(generics.ListCreateAPIView):
    queryset = TrueFalseQuestion.objects.all()
    serializer_class = TrueFalseQuestionSerializer
    permission_classes = [permissions.AllowAny]


class TrueFalseQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TrueFalseQuestion.objects.all()
    serializer_class = TrueFalseQuestionSerializer
    permission_classes = [permissions.AllowAny]


# ------------------ OPEN QUESTION ------------------
class OpenQuestionListCreateView(generics.ListCreateAPIView):
    queryset = OpenQuestion.objects.all()
    serializer_class = OpenQuestionSerializer
    permission_classes = [permissions.AllowAny]


class OpenQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OpenQuestion.objects.all()
    serializer_class = OpenQuestionSerializer
    permission_classes = [permissions.AllowAny]


# ------------------ USER TEST ATTEMPTS ------------------
class UserTestAttemptsView(generics.ListAPIView):
    serializer_class = TestAttemptSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return TestAttempt.objects.filter(user=self.request.user).order_by('-completed_at')


# ------------------ SUBMIT TEST ATTEMPT ------------------
class SubmitTestAttemptView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = request.user
        data = request.data
        try:
            test = Test.objects.get(id=data['test_id'])
        except Test.DoesNotExist:
            return Response({"detail": "Test not found"}, status=status.HTTP_404_NOT_FOUND)

        score = 0
        max_score = 0

        attempt = TestAttempt.objects.create(user=user, test=test)

        # Обработка multiple choice
        for answer in data.get('multiple_choice', []):
            question = TestQuestion.objects.get(id=answer['question_id'])
            correct_ids = list(question.answers.filter(is_correct=True).values_list('id', flat=True))
            is_correct = answer['selected'] in correct_ids
            QuestionAttempt.objects.create(
                attempt=attempt,
                question_text=question.question_text,
                user_answer=str(answer['selected']),
                correct_answer=str(correct_ids),
                is_correct=is_correct
            )
            score += 1 if is_correct else 0
            max_score += 1

        # Обработка True/False
        for answer in data.get('true_false', []):
            question = TrueFalseQuestion.objects.get(id=answer['question_id'])
            is_correct = str(answer['selected']).lower() == str(question.is_true).lower()
            QuestionAttempt.objects.create(
                attempt=attempt,
                question_text=question.question_text,
                user_answer=str(answer['selected']),
                correct_answer=str(question.is_true),
                is_correct=is_correct
            )
            score += 1 if is_correct else 0
            max_score += 1

        # Обработка открытых вопросов
        for answer in data.get('open_questions', []):
            question = OpenQuestion.objects.get(id=answer['question_id'])
            is_correct = answer['response'].strip().lower() == question.correct_answer.strip().lower()
            QuestionAttempt.objects.create(
                attempt=attempt,
                question_text=question.question_text,
                user_answer=answer['response'],
                correct_answer=question.correct_answer,
                is_correct=is_correct
            )
            score += 1 if is_correct else 0
            max_score += 1

        attempt.score = score
        attempt.save()

        return Response({'score': score, 'max_score': max_score}, status=status.HTTP_201_CREATED)
