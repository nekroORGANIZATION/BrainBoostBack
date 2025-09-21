from __future__ import annotations
from typing import Any, Dict

from django.db import transaction
from django.db.models import Max
from rest_framework import serializers

from .models import Module, Lesson, LessonContent, LessonProgress


# ---------- Modules ----------
class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'description', 'order', 'is_visible']


class ModuleReorderSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        help_text="[{id: <int>, order: <int>}, ...]"
    )


# Легка версія модуля для вбудовування в уроки
class ModuleLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'title', 'order']


# ---------- Lesson blocks ----------
class LessonBlockSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = LessonContent
        fields = ['id', 'type', 'data', 'order', 'is_hidden']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        t = attrs.get('type') or getattr(self.instance, 'type', None)
        data = attrs.get('data', getattr(self.instance, 'data', {})) or {}

        def strf(x): return isinstance(x, str)

        if t == 'text':
            if not (strf(data.get('html', '')) or strf(data.get('text', ''))):
                raise serializers.ValidationError({'data': 'text: need html or text'})
        elif t in ('image', 'video', 'file'):
            if not strf(data.get('url', '')):
                raise serializers.ValidationError({'data': f'{t}.url required'})
        elif t == 'code':
            if not strf(data.get('code', '')) or not strf(data.get('language', '')):  # language: js, py, md тощо
                raise serializers.ValidationError({'data': 'code.code & code.language required'})
        elif t == 'quote':
            if not strf(data.get('text', '')):
                raise serializers.ValidationError({'data': 'quote.text required'})
        elif t == 'checklist':
            items = data.get('items', [])
            if not isinstance(items, list):
                raise serializers.ValidationError({'data': 'checklist.items must be list'})
        elif t == 'html':
            if not strf(data.get('html', '')):
                raise serializers.ValidationError({'data': 'html.html required'})
        elif t == 'columns':
            cols = data.get('cols', [])
            if not (isinstance(cols, list) and len(cols) >= 2):
                raise serializers.ValidationError({'data': 'columns.cols must be at least 2'})
        elif t == 'callout':
            if data.get('tone') not in ('info', 'warn', 'ok'):
                raise serializers.ValidationError({'data': 'callout.tone must be info|warn|ok'})
            if not strf(data.get('html', '')):
                raise serializers.ValidationError({'data': 'callout.html required'})
        # інші типи — без додаткової валідації
        return attrs


# ---------- Lessons ----------
class LessonSerializer(serializers.ModelSerializer):
    contents = LessonBlockSerializer(many=True, required=False)

    # READ: nested module (може бути null)
    module = ModuleLiteSerializer(read_only=True)

    # WRITE: приймаємо module_id + можна кинути module або ?module=
    module_id = serializers.PrimaryKeyRelatedField(
        source='module',
        queryset=Module.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    # Сумісність зі старим плоским форматом
    type = serializers.CharField(write_only=True, required=False, allow_blank=False)
    content_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    content_url  = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'course',
            'module', 'module_id',          # read + write
            'title', 'slug',
            'summary', 'order', 'status', 'scheduled_at', 'published_at',
            'duration_min', 'cover_image',
            'contents',
            'type', 'content_text', 'content_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    # --- Мапимо body.module/qp ?module у module_id ---
    def to_internal_value(self, data):
        data = data.copy() if isinstance(data, dict) else data

        if isinstance(data, dict) and 'module_id' not in data and 'module' in data:
            mod_val = data.get('module')
            if isinstance(mod_val, dict) and 'id' in mod_val:
                data['module_id'] = mod_val['id']
            else:
                data['module_id'] = mod_val

        # ?module=<id>
        if isinstance(data, dict) and 'module_id' not in data:
            req = self.context.get('request')
            if req:
                qp_mod = req.query_params.get('module')
                if qp_mod not in (None, ''):
                    data['module_id'] = qp_mod

        # Нормалізуємо module_id до int або None (щоб '3' не валив валідацію)
        if isinstance(data, dict) and 'module_id' in data and data['module_id'] not in (None, ''):
            try:
                data['module_id'] = int(data['module_id'])
            except Exception:
                pass

        return super().to_internal_value(data)
    # --- /map ---

    def _normalize_type(self, t: str) -> str:
        return (t or '').strip().lower()

    def _flat_to_contents(self, data: Dict[str, Any]) -> list[dict]:
        t = self._normalize_type(data.get('type'))
        if t == 'text':
            txt = (data.get('content_text') or '').strip()
            return [{'type': 'text', 'data': {'html': txt}}]
        if t == 'video':
            url = (data.get('content_url') or '').strip()
            return [{'type': 'video', 'data': {'url': url}}]
        if t == 'link':
            url = (data.get('content_url') or '').strip()
            return [{'type': 'html', 'data': {'html': f'<a href="{url}" target="_blank">{url}</a>'}}]
        return []

    def validate(self, attrs):
        initial = getattr(self, 'initial_data', {}) or {}

        # summary — як прийшло
        attrs['summary'] = initial.get('summary', attrs.get('summary', ''))

        # Якщо contents не передані — пробуємо зібрати зі старого плоского формату
        if not ('contents' in initial and initial['contents'] is not None):
            synth = self._flat_to_contents(initial | attrs)
            if synth:
                attrs['contents'] = synth

        # Обчислюємо order лише якщо явно не заданий
        # (None або 0 трактуємо як "не задано" — останній в межах модуля/курсу)
        if attrs.get('order') in (None, 0):
            qs = Lesson.objects.filter(course=attrs.get('course'))
            if attrs.get('module'):
                qs = qs.filter(module=attrs['module'])
            last = qs.aggregate(mx=Max('order'))['mx'] or 0
            attrs['order'] = last + 1

        # ще раз, раптом змінився тип
        synth = self._flat_to_contents(initial | attrs)
        if synth:
            attrs['contents'] = synth

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        contents = validated_data.pop('contents', [])
        # прибираємо службові зі старого формату
        validated_data.pop('type', None)
        validated_data.pop('content_text', None)
        validated_data.pop('content_url', None)

        lesson = Lesson.objects.create(**validated_data)
        if contents:
            bulk = [
                LessonContent(
                    lesson=lesson,
                    type=c['type'],
                    data=c.get('data', {}),
                    order=i,
                    is_hidden=c.get('is_hidden', False),
                ) for i, c in enumerate(contents)
            ]
            LessonContent.objects.bulk_create(bulk)
        return lesson

    @transaction.atomic
    def update(self, instance, validated_data):
        contents = validated_data.pop('contents', None)

        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        # повна заміна масиву блоків (якщо передали)
        if contents is not None:
            instance.contents.all().delete()
            bulk = [
                LessonContent(
                    lesson=instance,
                    type=c['type'],
                    data=c.get('data', {}),
                    order=i,
                    is_hidden=c.get('is_hidden', False),
                ) for i, c in enumerate(contents)
            ]
            if bulk:
                LessonContent.objects.bulk_create(bulk)
        return instance


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'user', 'lesson', 'state', 'result_percent', 'started_at', 'completed_at', 'updated_at']
        read_only_fields = ['id', 'user', 'started_at', 'completed_at', 'updated_at']


class LessonPublicListWithProgressSerializer(serializers.ModelSerializer):
    """
    Публічний список уроків із прогресом для сторінок курсу/розділів.
    """
    completed = serializers.BooleanField(read_only=True)
    result_percent = serializers.IntegerField(read_only=True, allow_null=True)

    # модуль може бути None — це ок
    module = ModuleLiteSerializer(read_only=True)
    module_id = serializers.IntegerField(source='module.id', read_only=True, allow_null=True)

    order = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'summary', 'duration_min', 'cover_image',
            'completed', 'result_percent',
            'module', 'module_id', 'order',
        ]


# (залишаємо як було — якщо десь використовується)
class LessonListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    cover_image = serializers.ImageField(read_only=True)
    description = serializers.CharField(allow_blank=True, required=False)
    course = serializers.SerializerMethodField()
    is_published = serializers.BooleanField(required=False)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
    theories_count = serializers.SerializerMethodField()

    def get_course(self, obj):
        c = getattr(obj, 'course', None)
        if not c:
            return None
        title = getattr(c, 'title', None) or getattr(c, 'name', None)
        return {'id': getattr(c, 'id', None), 'title': title, 'name': title}

    def get_theories_count(self, obj):
        t = getattr(obj, 'theories', None)
        try:
            return t.count()
        except Exception:
            return 0
