from typing import Any, Dict, List
from rest_framework import serializers
from .models import Module, Lesson, LessonContent, LessonProgress


# -------- Module --------

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'description', 'order', 'is_visible']


class ModuleReorderSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        help_text="[{id: <int>, order: <int>}, ...]"
    )


# -------- LessonContent --------

class LessonContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonContent
        fields = ['id', 'type', 'data', 'order', 'is_hidden']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        t = attrs.get('type') or getattr(self.instance, 'type', None)
        data = attrs.get('data', getattr(self.instance, 'data', {})) or {}
        # Базові валідації під тип
        if t == 'text':
            if not isinstance(data.get('text', ''), str):
                raise serializers.ValidationError("data.text має бути рядком.")
        elif t == 'image':
            if not isinstance(data.get('url', ''), str):
                raise serializers.ValidationError("data.url (image) має бути рядком (URL).")
            # опц: alt
        elif t == 'video':
            if not isinstance(data.get('url', ''), str):
                raise serializers.ValidationError("data.url (video) має бути рядком (URL/YouTube).")
        elif t == 'code':
            if not isinstance(data.get('code', ''), str):
                raise serializers.ValidationError("data.code має бути рядком.")
            if not isinstance(data.get('language', ''), str):
                raise serializers.ValidationError("data.language має бути рядком (напр. 'js').")
        elif t == 'file':
            if not isinstance(data.get('url', ''), str):
                raise serializers.ValidationError("data.url (file) має бути рядком (URL).")
            # name — опц.
        elif t == 'quote':
            if not isinstance(data.get('text', ''), str):
                raise serializers.ValidationError("data.text має бути рядком.")
        elif t == 'checklist':
            items = data.get('items', [])
            if not isinstance(items, list):
                raise serializers.ValidationError("data.items має бути масивом.")
        elif t == 'html':
            if not isinstance(data.get('html', ''), str):
                raise serializers.ValidationError("data.html має бути рядком HTML.")
        return attrs


# -------- Lesson --------

class LessonSerializer(serializers.ModelSerializer):
    contents = LessonContentSerializer(many=True, required=False)

    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'module', 'title', 'slug',
            'summary', 'order', 'status', 'scheduled_at', 'published_at',
            'duration_min', 'cover_image',
            'contents',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data: Dict[str, Any]) -> Lesson:
        contents = self.initial_data.get('contents', [])
        lesson = Lesson.objects.create(**validated_data)
        for idx, c in enumerate(contents):
            LessonContent.objects.create(
                lesson=lesson,
                type=c['type'],
                data=c.get('data', {}),
                order=c.get('order', idx),
                is_hidden=c.get('is_hidden', False),
            )
        return lesson

    def update(self, instance: Lesson, validated_data: Dict[str, Any]) -> Lesson:
        contents = self.initial_data.get('contents', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if contents is not None:
            instance.contents.all().delete()
            bulk = []
            for idx, c in enumerate(contents):
                bulk.append(LessonContent(
                    lesson=instance,
                    type=c['type'],
                    data=c.get('data', {}),
                    order=c.get('order', idx),
                    is_hidden=c.get('is_hidden', False),
                ))
            LessonContent.objects.bulk_create(bulk)

        return instance


# -------- Progress --------

class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'user', 'lesson', 'state', 'started_at', 'completed_at', 'updated_at']
        read_only_fields = ['id', 'user', 'started_at', 'completed_at', 'updated_at']
