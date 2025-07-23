from rest_framework import generics
from .models import (
    Lesson, CourseTheory, TestQuestion,
    TestAnswer, TrueFalseQuestion, OpenQuestion, Test
)
from .serializers import (
    LessonSerializer, CourseTheorySerializer, TestQuestionSerializer,
    TestAnswerSerializer, TrueFalseQuestionSerializer, OpenQuestionSerializer, TestSerializer
)

class TestListCreateView(generics.ListCreateAPIView):
    queryset = Test.objects.all()
    serializer_class = TestSerializer

class TestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Test.objects.all()
    serializer_class = TestSerializer

# 🔹 LESSON
class LessonListCreateView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

class LessonDetailView(generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

class LessonUpdateView(generics.UpdateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

class LessonDeleteView(generics.DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


# 🔹 COURSE THEORY
class CourseTheoryListCreateView(generics.ListCreateAPIView):
    queryset = CourseTheory.objects.all()
    serializer_class = CourseTheorySerializer

class CourseTheoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CourseTheory.objects.all()
    serializer_class = CourseTheorySerializer


# 🔹 TEST QUESTION
class TestQuestionListCreateView(generics.ListCreateAPIView):
    queryset = TestQuestion.objects.all()
    serializer_class = TestQuestionSerializer

class TestQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestQuestion.objects.all()
    serializer_class = TestQuestionSerializer


# 🔹 TEST ANSWER
class TestAnswerListCreateView(generics.ListCreateAPIView):
    queryset = TestAnswer.objects.all()
    serializer_class = TestAnswerSerializer

class TestAnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestAnswer.objects.all()
    serializer_class = TestAnswerSerializer


# 🔹 TRUE/FALSE QUESTION
class TrueFalseQuestionListCreateView(generics.ListCreateAPIView):
    queryset = TrueFalseQuestion.objects.all()
    serializer_class = TrueFalseQuestionSerializer

class TrueFalseQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TrueFalseQuestion.objects.all()
    serializer_class = TrueFalseQuestionSerializer


# 🔹 OPEN QUESTION
class OpenQuestionListCreateView(generics.ListCreateAPIView):
    queryset = OpenQuestion.objects.all()
    serializer_class = OpenQuestionSerializer

class OpenQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OpenQuestion.objects.all()
    serializer_class = OpenQuestionSerializer
