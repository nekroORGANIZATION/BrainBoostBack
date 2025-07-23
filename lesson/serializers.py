from rest_framework import serializers
from .models import (
    Lesson, CourseTheory, TestQuestion,
    TestAnswer, TrueFalseQuestion, OpenQuestion, Test
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
        fields = '__all__'

class TestQuestionSerializer(serializers.ModelSerializer):
    answers = TestAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = TestQuestion
        fields = '__all__'

class TrueFalseQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrueFalseQuestion
        fields = '__all__'

class OpenQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenQuestion
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    theories = CourseTheorySerializer(many=True, read_only=True)
    test_questions = TestQuestionSerializer(many=True, read_only=True)
    true_false_questions = TrueFalseQuestionSerializer(many=True, read_only=True)
    open_questions = OpenQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = '__all__'
