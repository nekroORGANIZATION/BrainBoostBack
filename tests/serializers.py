from typing import List, Dict, Any
from rest_framework import serializers
from .models import Test, Question, Choice, TestAttempt, AnswerAttempt


# ---------- Choices ----------

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct', 'order']


class ChoicePublicSerializer(serializers.ModelSerializer):
    """Варіант без is_correct — якщо захочеш віддавати без додаткової очистки у view."""
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']
        read_only_fields = ['id']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ['text', 'type', 'points', 'order', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question

class TestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Test
        fields = ['lesson', 'title', 'description', 'status', 'time_limit_sec', 'attempts_allowed', 'pass_mark', 'questions']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        test = Test.objects.create(**validated_data)
        for question_data in questions_data:
            choices_data = question_data.pop('choices', [])
            question = Question.objects.create(test=test, **question_data)
            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)
        return test

# ---------- Attempts (read-only серіалізатори для відповідей) ----------

class AnswerAttemptReadSerializer(serializers.ModelSerializer):
    selected_option_ids = serializers.SerializerMethodField()

    class Meta:
        model = AnswerAttempt
        fields = [
            'question', 'is_correct', 'score_awarded', 'selected_option_ids',
            'free_text', 'free_json', 'answered_at', 'needs_manual'
        ]

    def get_selected_option_ids(self, obj: AnswerAttempt) -> List[int]:
        return list(obj.selected_options.values_list('id', flat=True))


class TestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAttempt
        fields = [
            'id', 'test', 'user', 'attempt_no', 'status',
            'started_at', 'finished_at', 'duration_sec',
            'score', 'max_score', 'pass_mark'
        ]
        read_only_fields = [
            'id', 'user', 'status',
            'started_at', 'finished_at', 'duration_sec',
            'score', 'max_score', 'pass_mark'
        ]


# Опційно: «повний» серіалізатор спроби з відповідями (для вчителя/after_close)
class TestAttemptDetailSerializer(TestAttemptSerializer):
    answers = AnswerAttemptReadSerializer(many=True, read_only=True)

    class Meta(TestAttemptSerializer.Meta):
        fields = TestAttemptSerializer.Meta.fields + ['answers']
