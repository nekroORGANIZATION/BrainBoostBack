from rest_framework import serializers
from .models import (
    Lesson, CourseTheory, TestQuestion,
    TestAnswer, TrueFalseQuestion, OpenQuestion, Test, TestAttempt, QuestionAttempt, TestAttempt, TestAnswerAttempt
)

class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = '__all__'

class CourseTheorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseTheory
        fields = '__all__'

class TestAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ['id', 'answer_text']

class TestQuestionSerializer(serializers.ModelSerializer):
    answers = TestAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = TestQuestion
        fields = ['id', 'question_text', 'answers']

class TrueFalseQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrueFalseQuestion
        fields = ['id', 'question_text']

# Сериализатор для открытых вопросов
class OpenQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenQuestion
        fields = ['id', 'question_text']

# Главный сериализатор для теста со вложенными вопросами
class TestSerializer(serializers.ModelSerializer):
    test_questions = TestQuestionSerializer(many=True, read_only=True)
    true_false_questions = TrueFalseQuestionSerializer(many=True, read_only=True)
    open_questions = OpenQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = ['id', 'title', 'test_questions', 'true_false_questions', 'open_questions']

class LessonSerializer(serializers.ModelSerializer):
    theories = CourseTheorySerializer(many=True, read_only=True)
    test_questions = TestQuestionSerializer(many=True, read_only=True)
    true_false_questions = TrueFalseQuestionSerializer(many=True, read_only=True)
    open_questions = OpenQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = '__all__'


class QuestionAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionAttempt
        fields = '__all__'


class TestAnswerAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswerAttempt
        fields = ['question', 'selected_answer']

class TestAttemptSerializer(serializers.ModelSerializer):
    answers = TestAnswerAttemptSerializer(many=True)

    class Meta:
        model = TestAttempt
        fields = ['id', 'test', 'user', 'answers', 'score']
