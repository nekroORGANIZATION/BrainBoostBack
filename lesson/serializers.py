# lesson/serializers.py
from __future__ import annotations
from typing import Any, Dict, List

from django.db import transaction
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


# Лёгкий модуль для встраивания в уроки
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
            if not strf(data.get('code', '')) or not strf(data.get('language', '')):
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
        return attrs


# ---------- Lessons ----------
class LessonSerializer(serializers.ModelSerializer):
    """
    Полный урок + (опционально) массив блоков.

    На ЧТЕНИЕ:
      - module -> вложенный объект ModuleLiteSerializer
    На ЗАПИСЬ:
      - module_id -> PK (write-only), чтобы не ломать совместимость форм/админки

    Поддерживает старый формат:
      - type: text|video|link
      - content_text / content_url
    """
    contents = LessonBlockSerializer(many=True, required=False)

    # READ: nested module
    module = ModuleLiteSerializer(read_only=True)
    # WRITE: PK для ForeignKey
    module_id = serializers.PrimaryKeyRelatedField(
        source='module',
        queryset=Module.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    # совместимость со старым форматом создания
    type = serializers.CharField(write_only=True, required=False, allow_blank=False)
    content_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    content_url  = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'course',
            'module', 'module_id',        # 👈 читаем объект, пишем через PK
            'title', 'slug',
            'summary', 'order', 'status', 'scheduled_at', 'published_at',
            'duration_min', 'cover_image',
            'contents',
            'type', 'content_text', 'content_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    # ---- старый формат → в массив блоков (если contents не прислали)
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

        attrs['summary'] = initial.get('summary', attrs.get('summary', ''))

        if 'contents' in initial and initial['contents'] is not None:
            return attrs

        synth = self._flat_to_contents(initial | attrs)
        if synth:
            attrs['contents'] = synth
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        contents = validated_data.pop('contents', [])
        # убираем служебные поля старого формата
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

        # обновляем плоские поля (включая module через module_id→source='module')
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        # полная замена массива блоков (если передали)
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


# ---------- Progress / списки для каталога / публичка ----------
class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'user', 'lesson', 'state', 'result_percent', 'started_at', 'completed_at', 'updated_at']
        read_only_fields = ['id', 'user', 'started_at', 'completed_at', 'updated_at']


class LessonPublicListWithProgressSerializer(serializers.ModelSerializer):
    """
    Публичный список уроков с прогрессом пользователя.
    Чтение: module — вложенный объект; order — для стабильной сортировки на фронте.
    """
    completed = serializers.BooleanField(read_only=True)
    result_percent = serializers.IntegerField(read_only=True, allow_null=True)
    module = ModuleLiteSerializer(read_only=True)
    order = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'summary', 'duration_min', 'cover_image',
            'completed', 'result_percent',
            'module', 'order',
        ]


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
