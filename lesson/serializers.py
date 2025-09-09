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

class LessonSerializer(serializers.ModelSerializer):
    contents = LessonContentSerializer(many=True, required=False)

    # --- write-only поля для СТАРОГО плоского формата ---
    type = serializers.CharField(write_only=True, required=False, allow_blank=False)
    content_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    content_url = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'module', 'title', 'slug',
            'summary', 'order', 'status', 'scheduled_at', 'published_at',
            'duration_min', 'cover_image',
            'contents',           # новый блочный формат
            'type', 'content_text', 'content_url',  # старый плоский формат (write-only)
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    # ---- helpers ----
    def _normalize_type(self, t: str) -> str:
        """Принимаем VIDEO|TEXT|LINK (в любом регистре) и внутренние типы ('text','video','html',...)."""
        if not t:
            return ''
        t_low = str(t).strip().lower()
        # входящие значения из старого API
        if t_low in ('text', 'video', 'link'):
            return t_low
        # вдруг пришли в аппер кейсе
        if t_low in ('video', 'text', 'link'):
            return t_low
        # поддержим, если кто-то прислал уже внутренние типы
        if t_low in ('html', 'image', 'code', 'file', 'quote', 'checklist'):
            return t_low
        return t_low  # вернём как есть — пусть валидация ниже отработает

    def _flat_to_contents(self, attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Преобразует старый плоский формат (type + content_*) в contents[0]."""
        t_in = self._normalize_type(attrs.get('type', ''))
        cont: List[Dict[str, Any]] = []

        if not t_in:
            return cont

        if t_in == 'text':
            text = (attrs.get('content_text') or '').strip()
            cont.append({'type': 'text', 'data': {'text': text}})
        elif t_in == 'video':
            url = (attrs.get('content_url') or '').strip()
            cont.append({'type': 'video', 'data': {'url': url}})
        elif t_in == 'link':
            url = (attrs.get('content_url') or '').strip()
            # в нашей модели нет 'link' — сохраним как html-блок
            cont.append({'type': 'html', 'data': {'html': f'<a href="{url}" target="_blank" rel="noopener">{url}</a>'}})
        else:
            # если пришёл внутренний тип — оставим попытку как есть (но это уже не "старый" формат)
            pass

        return cont

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Принимаем два сценария:
        1) новый: передан contents (валидируется дочерним сериализатором);
        2) старый: переданы type + content_text|content_url → превратим в contents[0].
        """
        # NB: initial_data — чтобы видеть поля, которых нет в attrs (write_only или read_only и т.д.)
        initial = getattr(self, 'initial_data', {}) or {}

        # Если прям прислали contents — оставим, только убедимся, что это массив
        if 'contents' in initial and initial['contents'] is not None:
            if not isinstance(initial['contents'], list):
                raise serializers.ValidationError({'contents': 'Має бути масивом.'})
            # Ничего не делаем — дочерний сериализатор провалидирует при .create/.update
            return attrs

        # Иначе пробуем старый формат
        t_in = initial.get('type') or attrs.get('type')
        t_norm = self._normalize_type(t_in or '')

        if not t_norm:
            # для обратной совместимости оставим то самое сообщение, которое ты видел в логах
            raise serializers.ValidationError({'detail': 'Invalid payload. Required: course, title, type [VIDEO|TEXT|LINK].'})

        # Подготовим «виртуальный» contents[0] на основе плоских полей
        synth = self._flat_to_contents(initial | attrs)
        if not synth:
            raise serializers.ValidationError({'detail': 'Invalid payload. Missing content for the given type.'})

        # Подложим synthesized contents в attrs (чтобы create/update уже работали одинаково)
        attrs['contents'] = synth
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> Lesson:
        # contents пришёл либо из запроса, либо синтезирован в validate()
        contents = validated_data.pop('contents', [])
        # выкидываем write-only плоские поля, чтобы не провалились в Lesson(**validated_data)
        validated_data.pop('type', None)
        validated_data.pop('content_text', None)
        validated_data.pop('content_url', None)

        # создаём урок
        lesson = Lesson.objects.create(**validated_data)

        # создаём контент-блоки
        bulk = []
        for idx, c in enumerate(contents):
            bulk.append(LessonContent(
                lesson=lesson,
                type=c['type'],
                data=c.get('data', {}),
                order=c.get('order', idx),
                is_hidden=c.get('is_hidden', False),
            ))
        if bulk:
            LessonContent.objects.bulk_create(bulk)

        return lesson

    @transaction.atomic
    def update(self, instance: Lesson, validated_data: Dict[str, Any]) -> Lesson:
        contents = validated_data.pop('contents', None)
        validated_data.pop('type', None)
        validated_data.pop('content_text', None)
        validated_data.pop('content_url', None)

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
