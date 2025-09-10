from typing import List, Dict, Any
from rest_framework import serializers
from .models import Test, Question, Choice, TestAttempt, AnswerAttempt


# ---------- Choices ----------

class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ['id','text', 'is_correct', 'order']


class ChoicePublicSerializer(serializers.ModelSerializer):
    """Варіант без is_correct — якщо захочеш віддавати без додаткової очистки у view."""
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']
        read_only_fields = ['id']

class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id','text', 'type', 'points', 'order', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)

        # Для short/long — створюємо один Choice як правильну текстову відповідь
        if question.type in ['short', 'long'] and choices_data:
            Choice.objects.create(
                question=question,
                text=choices_data[0].get('text', ''),
                is_correct=True,
                order=1
            )

        for choice_data in choices_data:
            if question.type not in ['short', 'long']:
                Choice.objects.create(question=question, **choice_data)
                
        return question
    

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)

        # update question fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if choices_data is not None:
            keep_ids = []
            for choice_data in choices_data:
                choice_id = choice_data.get('id')
                if choice_id:
                    choice = Choice.objects.get(id=choice_id, question=instance)
                    for attr, value in choice_data.items():
                        setattr(choice, attr, value)
                    choice.save()
                    keep_ids.append(choice.id)
                else:
                    choice = Choice.objects.create(question=instance, **choice_data)
                    keep_ids.append(choice.id)

            # видаляємо ті, що не передані
            Choice.objects.filter(question=instance).exclude(id__in=keep_ids).delete()

        return instance
    
    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)

        # Оновлюємо поля питання
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if choices_data is not None:
            if instance.type in ['short', 'long']:
                # беремо перший choice як правильну відповідь
                if choices_data:
                    choice = instance.choices.filter(is_correct=True).first()
                    if choice:
                        choice.text = choices_data[0].get('text', '')
                        choice.save()
                    else:
                        Choice.objects.create(
                            question=instance,
                            text=choices_data[0].get('text', ''),
                            is_correct=True,
                            order=1
                        )
                # видаляємо всі інші варіанти
                instance.choices.exclude(is_correct=True).delete()
            else:
                # стандартне оновлення для інших типів
                keep_ids = []
                for choice_data in choices_data:
                    choice_id = choice_data.get('id')
                    if choice_id:
                        choice = Choice.objects.get(id=choice_id, question=instance)
                        for attr, value in choice_data.items():
                            setattr(choice, attr, value)
                        choice.save()
                        keep_ids.append(choice.id)
                    else:
                        choice = Choice.objects.create(question=instance, **choice_data)
                        keep_ids.append(choice.id)
                Choice.objects.filter(question=instance).exclude(id__in=keep_ids).delete()

        return instance

class TestSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Test
        fields = ['id', 'lesson', 'title', 'description', 'status', 'time_limit_sec', 'attempts_allowed', 'pass_mark', 'questions']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        test = Test.objects.create(**validated_data)
        for question_data in questions_data:
            choices_data = question_data.pop('choices', [])
            question = Question.objects.create(test=test, **question_data)
            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)
        return test
    

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)

        # update test fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if questions_data is not None:
            keep_ids = []
            for q_data in questions_data:
                q_id = q_data.get('id')
                if q_id:
                    question = Question.objects.get(id=q_id, test=instance)
                    self.fields['questions'].update(question, q_data)
                    keep_ids.append(question.id)
                else:
                    choices_data = q_data.pop('choices', [])
                    question = Question.objects.create(test=instance, **q_data)
                    for choice_data in choices_data:
                        Choice.objects.create(question=question, **choice_data)
                    keep_ids.append(question.id)

            # видаляємо ті, що не передані
            Question.objects.filter(test=instance).exclude(id__in=keep_ids).delete()

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
