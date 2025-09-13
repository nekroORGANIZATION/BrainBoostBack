# lesson/serializers.py
from typing import Any, Dict, List
from django.db import transaction
from rest_framework import serializers
from .models import Module, Lesson, LessonContent, LessonProgress


# ============================================================================================

class LessonContentSerializer(serializers.ModelSerializer):
    """
    Блочний контент уроку. Минимально необходим для редактирования.
    """
    id = serializers.IntegerField(required=False)

    class Meta:
        model = LessonContent
        fields = ['id', 'type', 'data', 'order', 'is_hidden']


class LessonSerializer(serializers.ModelSerializer):
    """
    Сериализатор урока с возможностью редактирования основных полей и контента.
    Поддерживает:
      - PATCH/PUT с обычными полями
      - Полную замену contents (если массив передан) с upsert по id и удалением «лишних» блоков
      - Загрузку cover_image через multipart/form-data
    """
    contents = LessonContentSerializer(many=True, required=False)

    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'module', 'title', 'slug',
            'summary', 'order', 'status', 'scheduled_at', 'published_at',
            'duration_min', 'cover_image',
            'contents',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_status(self, value: str) -> str:
        # нормализуем на случай разных регистров
        return (value or '').lower() or Lesson.Status.DRAFT

    @transaction.atomic
    def update(self, instance: Lesson, validated_data: Dict[str, Any]) -> Lesson:
        """
        Обновляем сам урок + (при наличии) полностью пересобираем blocks (contents).
        Если в payload присутствует поле contents — считаем это намерением обновить структуру.
        Алгоритм:
          1) Собираем map существующих блоков по id.
          2) Для пришедших с id — апдейтим поля.
          3) Для пришедших без id — создаём новые.
          4) Блоки, которых нет в пришедшем массиве, удаляем.
        """
        incoming_contents: List[Dict[str, Any]] | None = validated_data.pop('contents', None)

        # Простая очистка cover_image: если пришло пустое значение строкой — обнуляем
        # (актуально для JSON PATCH)
        cover_in = self.context.get('request').data.get('cover_image') if self.context.get('request') else None
        if cover_in in ['', 'null', 'None']:
            instance.cover_image = None

        # Обновляем «плоские» поля урока
        for field in ['course', 'module', 'title', 'slug', 'summary',
                      'order', 'status', 'scheduled_at', 'published_at',
                      'duration_min', 'cover_image']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        # Если контент не прислали — выходим
        if incoming_contents is None:
            return instance

        # 1) существующие блоки
        existing = {c.id: c for c in instance.contents.all()}

        # 2) обрабатываем входящие
        seen_ids: set[int] = set()
        to_create: list[LessonContent] = []
        to_update: list[LessonContent] = []

        for idx, c in enumerate(incoming_contents):
            cid = c.get('id')
            base = {
                'type': c.get('type'),
                'data': c.get('data', {}) or {},
                'order': c.get('order', idx),
                'is_hidden': c.get('is_hidden', False),
            }
            if cid and cid in existing:
                # апдейт существующего
                block = existing[cid]
                block.type = base['type']
                block.data = base['data']
                block.order = base['order']
                block.is_hidden = base['is_hidden']
                to_update.append(block)
                seen_ids.add(cid)
            else:
                # создаём новый
                to_create.append(LessonContent(
                    lesson=instance,
                    **base
                ))

        # 3) удаляем отсутствующие
        to_delete_ids = [bid for bid in existing.keys() if bid not in seen_ids]
        if to_delete_ids:
            LessonContent.objects.filter(id__in=to_delete_ids, lesson=instance).delete()

        # 4) массовые операции
        if to_create:
            LessonContent.objects.bulk_create(to_create)
        if to_update:
            LessonContent.objects.bulk_update(to_update, ['type', 'data', 'order', 'is_hidden'])

        return instance

# -------- Module --------==========================================================

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

        if t == 'text':
            if not isinstance(data.get('text', ''), str):
                raise serializers.ValidationError("data.text має бути рядком.")
        elif t == 'image':
            if not isinstance(data.get('url', ''), str):
                raise serializers.ValidationError("data.url (image) має бути рядком (URL).")
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

from typing import Any, Dict, List
from django.db import transaction
from rest_framework import serializers
from .models import Lesson, LessonContent, Module, LessonProgress


class LessonContentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = LessonContent
        fields = ['id', 'type', 'data', 'order', 'is_hidden']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        t = attrs.get('type') or getattr(self.instance, 'type', None)
        data = attrs.get('data', getattr(self.instance, 'data', {})) or {}

        if t == 'text' and not isinstance(data.get('text', ''), str):
            raise serializers.ValidationError("data.text має бути рядком.")
        elif t == 'image' and not isinstance(data.get('url', ''), str):
            raise serializers.ValidationError("data.url (image) має бути рядком (URL).")
        elif t == 'video' and not isinstance(data.get('url', ''), str):
            raise serializers.ValidationError("data.url (video) має бути рядком (URL/YouTube).")
        elif t == 'code':
            if not isinstance(data.get('code', ''), str):
                raise serializers.ValidationError("data.code має бути рядком.")
            if not isinstance(data.get('language', ''), str):
                raise serializers.ValidationError("data.language має бути рядком.")
        elif t == 'file' and not isinstance(data.get('url', ''), str):
            raise serializers.ValidationError("data.url (file) має бути рядком (URL).")
        elif t == 'quote' and not isinstance(data.get('text', ''), str):
            raise serializers.ValidationError("data.text має бути рядком.")
        elif t == 'checklist' and not isinstance(data.get('items', []), list):
            raise serializers.ValidationError("data.items має бути масивом.")
        elif t == 'html' and not isinstance(data.get('html', ''), str):
            raise serializers.ValidationError("data.html має бути рядком HTML.")
        return attrs


class LessonSerializer(serializers.ModelSerializer):
    contents = LessonContentSerializer(many=True, required=False)
    type = serializers.CharField(write_only=True, required=False, allow_blank=False)
    content_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    content_url = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'module', 'title', 'slug',
            'summary', 'order', 'status', 'scheduled_at', 'published_at',
            'duration_min', 'cover_image',
            'contents', 'type', 'content_text', 'content_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def _normalize_type(self, t: str) -> str:
        return t.strip().lower() if t else ''

    def _flat_to_contents(self, attrs: Dict[str, Any]) -> list:
        t_in = self._normalize_type(attrs.get('type', ''))
        cont = []
        if t_in == 'text':
            cont.append({'type': 'text', 'data': {'text': attrs.get('content_text', '').strip()}})
        elif t_in == 'video':
            cont.append({'type': 'video', 'data': {'url': attrs.get('content_url', '').strip()}})
        elif t_in == 'link':
            url = attrs.get('content_url', '').strip()
            cont.append({'type': 'html', 'data': {'html': f'<a href="{url}" target="_blank">{url}</a>'}})
        return cont

    def validate(self, attrs):
        initial = getattr(self, 'initial_data', {}) or {}

        # Гарантовано беремо summary з initial_data або attrs
        attrs['summary'] = initial.get('summary', attrs.get('summary', ''))

        # Якщо є contents — лишаємо їх
        if 'contents' in initial and initial['contents'] is not None:
            return attrs

        # Старий плоский формат
        synth = self._flat_to_contents(initial | attrs)
        if not synth:
            raise serializers.ValidationError({'detail': 'Invalid payload. Missing content for the given type.'})

        attrs['contents'] = synth
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        contents = validated_data.pop('contents', [])
        validated_data.pop('type', None)
        validated_data.pop('content_text', None)
        validated_data.pop('content_url', None)

        lesson = Lesson.objects.create(**validated_data)

        bulk = [
            LessonContent(
                lesson=lesson,
                type=c['type'],
                data=c.get('data', {}),
                order=i,
                is_hidden=c.get('is_hidden', False)
            ) for i, c in enumerate(contents)
        ]
        if bulk:
            LessonContent.objects.bulk_create(bulk)
        return lesson

    @transaction.atomic
    def update(self, instance, validated_data):
        contents = validated_data.pop('contents', None)
        validated_data.pop('type', None)
        validated_data.pop('content_text', None)
        validated_data.pop('content_url', None)

        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if contents is not None:
            instance.contents.all().delete()
            bulk = [
                LessonContent(
                    lesson=instance,
                    type=c['type'],
                    data=c.get('data', {}),
                    order=i,
                    is_hidden=c.get('is_hidden', False)
                ) for i, c in enumerate(contents)
            ]
            if bulk:
                LessonContent.objects.bulk_create(bulk)
        return instance

# -------- Progress / списки (без изменений) --------

class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'user', 'lesson', 'state', 'result_percent',  'started_at', 'completed_at', 'updated_at']
        read_only_fields = ['id', 'user', 'started_at', 'completed_at', 'updated_at']


class LessonPublicListWithProgressSerializer(serializers.ModelSerializer):
    completed = serializers.BooleanField(read_only=True)
    result_percent = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'summary', 'duration_min', 'cover_image',
            'completed', 'result_percent',
        ]


class MiniCourseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)


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
