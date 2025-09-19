from typing import List, Dict, Any
from rest_framework import serializers
from .models import Test, Question, Choice, TestAttempt, AnswerAttempt


# ---------- Choice ----------

class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order', 'feedback']


class ChoicePublicSerializer(serializers.ModelSerializer):
    """Public variant without correctness flag."""
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']
        read_only_fields = ['id']


# ---------- Question ----------

class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'id', 'text', 'type', 'points', 'order',
            'explanation', 'difficulty', 'required', 'spec',
            'choices'
        ]

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        q = Question.objects.create(**validated_data)

        # Short/Long — keep single "etalon" choice as correct (for uniform FE DTO)
        if q.type in ['short', 'long'] and choices_data:
            Choice.objects.create(
                question=q, text=choices_data[0].get('text', ''), is_correct=True, order=1
            )
        else:
            for c in choices_data:
                Choice.objects.create(question=q, **c)
        return q

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if choices_data is not None:
            if instance.type in ['short', 'long']:
                # single etalon
                if choices_data:
                    etalon = instance.choices.filter(is_correct=True).first()
                    text_val = choices_data[0].get('text', '')
                    if etalon:
                        etalon.text = text_val
                        etalon.order = 1
                        etalon.is_correct = True
                        etalon.save()
                    else:
                        Choice.objects.create(
                            question=instance, text=text_val, is_correct=True, order=1
                        )
                # drop others
                instance.choices.exclude(is_correct=True).delete()
            else:
                keep_ids = []
                for cd in choices_data:
                    cid = cd.get('id')
                    if cid:
                        ch = Choice.objects.get(id=cid, question=instance)
                        for a, v in cd.items():
                            setattr(ch, a, v)
                        ch.save()
                        keep_ids.append(ch.id)
                    else:
                        ch = Choice.objects.create(question=instance, **cd)
                        keep_ids.append(ch.id)
                Choice.objects.filter(question=instance).exclude(id__in=keep_ids).delete()

        return instance


# ---------- Test ----------

class TestSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Test
        fields = [
            'id', 'lesson', 'title', 'description',
            'status', 'opens_at', 'closes_at',
            'time_limit_sec', 'attempts_allowed', 'pass_mark',
            'shuffle_questions', 'shuffle_options', 'show_feedback_mode',
            'questions'
        ]

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        test = Test.objects.create(**validated_data)
        # keep order from payload
        for qd in questions_data:
            choices = qd.pop('choices', [])
            q = Question.objects.create(test=test, **qd)
            for cd in choices:
                Choice.objects.create(question=q, **cd)
        return test

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if questions_data is not None:
            keep_ids = []
            # Reuse the QuestionSerializer.update for nested updates
            qser = QuestionSerializer()
            for qd in questions_data:
                qid = qd.get('id')
                if qid:
                    q = Question.objects.get(id=qid, test=instance)
                    qser.update(q, qd)
                    keep_ids.append(q.id)
                else:
                    choices = qd.pop('choices', [])
                    q = Question.objects.create(test=instance, **qd)
                    for cd in choices:
                        Choice.objects.create(question=q, **cd)
                    keep_ids.append(q.id)

            Question.objects.filter(test=instance).exclude(id__in=keep_ids).delete()

        return instance


# ---------- Read-only for attempts ----------

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


class TestAttemptDetailSerializer(TestAttemptSerializer):
    """Full attempt (teacher or after_close)"""
    answers = AnswerAttemptReadSerializer(many=True, read_only=True)

    class Meta(TestAttemptSerializer.Meta):
        fields = TestAttemptSerializer.Meta.fields + ['answers']
