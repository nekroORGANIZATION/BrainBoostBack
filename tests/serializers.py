from typing import List, Dict, Any
from rest_framework import serializers
from .models import Test, Question, Choice, TestAttempt, AnswerAttempt


# ---------- Choices ----------

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']
        read_only_fields = ['id']


class ChoicePublicSerializer(serializers.ModelSerializer):
    """Варіант без is_correct — якщо захочеш віддавати без додаткової очистки у view."""
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']
        read_only_fields = ['id']


# ---------- Questions ----------

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'id', 'type', 'text', 'explanation', 'points', 'difficulty',
            'required', 'spec', 'order', 'choices'
        ]
        read_only_fields = ['id']

    # Валідація під типи
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        qtype = attrs.get('type') or getattr(self.instance, 'type', None)
        choices_payload = self.initial_data.get('choices', None)

        if qtype in ['single', 'multiple', 'true_false']:
            # Для варіантних типів мають бути choices
            if self.instance is None and not choices_payload:
                raise serializers.ValidationError("Для варіантних типів необхідний список choices.")
            if choices_payload:
                correct = [c for c in choices_payload if bool(c.get('is_correct'))]
                if qtype in ['single', 'true_false'] and len(correct) != 1:
                    raise serializers.ValidationError("Для single/true_false повинен бути рівно 1 правильний варіант.")
                if qtype == 'multiple' and len(correct) < 1:
                    raise serializers.ValidationError("Для multiple має бути щонайменше 1 правильний варіант.")

        # Для short можна задати еталони у spec['answers'] (список рядків)
        if qtype == 'short':
            spec = attrs.get('spec', getattr(self.instance, 'spec', {})) or {}
            ans = spec.get('answers')
            if ans is not None and not isinstance(ans, list):
                raise serializers.ValidationError("spec['answers'] для short має бути масивом рядків.")

        # Для match/order можна задати spec['solution'] (JSON)
        if qtype in ['match', 'order']:
            spec = attrs.get('spec', getattr(self.instance, 'spec', {})) or {}
            sol = spec.get('solution', None)
            if sol is not None and not isinstance(sol, (list, dict)):
                raise serializers.ValidationError("spec['solution'] має бути dict або list.")

        return attrs

    def create(self, validated: Dict[str, Any]) -> Question:
        choices_data = self.initial_data.get('choices', [])
        q = Question.objects.create(**validated)
        if choices_data:
            # збережемо порядок, якщо прийшов
            bulk = []
            for idx, c in enumerate(choices_data):
                bulk.append(Choice(question=q, text=c['text'], is_correct=bool(c.get('is_correct')),
                                   order=c.get('order', idx), feedback=c.get('feedback', '')))
            Choice.objects.bulk_create(bulk)
        return q

    def update(self, instance: Question, validated: Dict[str, Any]) -> Question:
        choices_data = self.initial_data.get('choices', None)

        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()

        if choices_data is not None:
            # перезапис списком — простіше для конструктора
            instance.choices.all().delete()
            bulk = []
            for idx, c in enumerate(choices_data):
                bulk.append(Choice(question=instance, text=c['text'], is_correct=bool(c.get('is_correct')),
                                   order=c.get('order', idx), feedback=c.get('feedback', '')))
            Choice.objects.bulk_create(bulk)

        return instance


# ---------- Tests ----------

class TestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Test
        fields = [
            'id', 'lesson', 'title', 'description',
            'status', 'opens_at', 'closes_at',
            'time_limit_sec', 'attempts_allowed', 'pass_mark',
            'shuffle_questions', 'shuffle_options', 'show_feedback_mode',
            'questions',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attempts_allowed = attrs.get('attempts_allowed', getattr(self.instance, 'attempts_allowed', 1))
        pass_mark = float(attrs.get('pass_mark', getattr(self.instance, 'pass_mark', 0)))
        if attempts_allowed < 0:
            raise serializers.ValidationError("attempts_allowed не може бути відʼємним.")
        # Якщо інтерпретуємо як відсоток:
        if pass_mark < 0:
            raise serializers.ValidationError("pass_mark не може бути відʼємним.")
        return attrs

    def create(self, validated: Dict[str, Any]) -> Test:
        qlist = self.initial_data.get('questions', [])
        t = Test.objects.create(**validated)
        # створимо питання пакетно
        for idx, q in enumerate(qlist):
            q_payload = {**q, 'test': t, 'order': q.get('order', idx)}
            QuestionSerializer().create(q_payload)
        return t

    def update(self, instance: Test, validated: Dict[str, Any]) -> Test:
        qlist = self.initial_data.get('questions', None)

        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()

        if qlist is not None:
            # Перезапис повним списком (зручно у конструкторі тесту)
            instance.questions.all().delete()
            for idx, q in enumerate(qlist):
                q_payload = {**q, 'test': instance, 'order': q.get('order', idx)}
                QuestionSerializer().create(q_payload)

        return instance


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
