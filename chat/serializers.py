from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Chat, Message, ReadMarker
from lesson.models import LessonContent  # якщо імпорт інший — підправ

# ---------- Mini: теорія ----------
class TheoryMiniSerializer(serializers.ModelSerializer):
    """
    Безпечний міні-серіалізатор теорії:
    - title обчислюється (в моделі може не бути title)
    - lesson_id через SerializerMethodField (аби уникнути assert DRF)
    - lesson_title через lesson.title (якщо є)
    """
    title = serializers.SerializerMethodField()
    lesson_id = serializers.SerializerMethodField()
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)

    class Meta:
        model = LessonContent
        fields = ["id", "title", "lesson_id", "lesson_title"]

    def get_title(self, obj: LessonContent) -> str:
        for attr in ("title", "name", "heading", "caption"):
            val = getattr(obj, attr, None)
            if val:
                return str(val)
        lesson = getattr(obj, "lesson", None)
        if lesson is not None:
            for attr in ("title", "name"):
                val = getattr(lesson, attr, None)
                if val:
                    return str(val)
        return f"Теорія #{obj.pk}"

    def get_lesson_id(self, obj: LessonContent):
        # повертає FK-значення навіть без select_related
        return getattr(obj, "lesson_id", None)


# ---------- Chat ----------
class ChatSerializer(serializers.ModelSerializer):
    theory = TheoryMiniSerializer(read_only=True)
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id", "title",
            "course", "lesson", "theory",
            "student", "teacher",
            "created_at", "updated_at",
            "last_message", "last_message_preview",
            "unread_count",
        ]
    read_only_fields = [
        "id", "created_at", "updated_at",
        "last_message", "last_message_preview", "unread_count",
    ]

    def get_last_message_preview(self, obj: Chat):
        m = obj.last_message
        if not m:
            return None
        return {
            "id": m.id,
            "sender": m.sender_id,
            "text": (m.text or "")[:150],
            "created_at": m.created_at,
            "is_deleted": m.is_deleted,
        }

    def get_unread_count(self, obj: Chat) -> int:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        try:
            rm = obj.read_markers.get(user=request.user)
            last_seen = rm.last_read_message_id or 0
        except ReadMarker.DoesNotExist:
            last_seen = 0
        return obj.messages.filter(id__gt=last_seen).exclude(sender=request.user).count()


# ---------- Start Chat ----------
# ---------- Start Chat ----------
class ChatStartSerializer(serializers.Serializer):
    """
    Вхід: peer (id співрозмовника), theory_id (необов'язковий, якщо є lesson_id).
    Повертає існуючий або створює новий чат по цій теорії.
    """
    peer = serializers.IntegerField()
    theory_id = serializers.IntegerField(required=False, allow_null=True)   # ← було required=True
    lesson_id = serializers.IntegerField(required=False, allow_null=True)   # ← фолбек

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        errors = {}

        # ---- peer ----
        User = get_user_model()
        try:
            peer = User.objects.get(id=attrs["peer"])
        except User.DoesNotExist:
            errors["peer"] = ["Користувач (peer) не знайдений."]
            raise serializers.ValidationError(errors)

        if peer.id == user.id:
            errors["peer"] = ["Неможливо відкрити чат із самим собою."]
            raise serializers.ValidationError(errors)

        # ---- theory / lesson ----
        theory = None
        theory_id = attrs.get("theory_id")
        lesson_id = attrs.get("lesson_id")

        if theory_id is None and lesson_id is None:
            # ключове: принаймні одне з полів обов’язкове
            raise serializers.ValidationError({
                "theory_id": ["Заповніть theory_id або lesson_id."],
                "lesson_id": ["Заповніть lesson_id або theory_id."],
            })

        if theory_id is not None:
            try:
                theory = (
                    LessonContent.objects
                    .select_related("lesson", "lesson__course")
                    .get(id=theory_id)
                )
            except LessonContent.DoesNotExist:
                errors["theory_id"] = ["Теорія не знайдена."]

        # фолбек по lesson_id, якщо theory досі не знайдено
        if theory is None and lesson_id is not None:
            theory = (
                LessonContent.objects
                .select_related("lesson", "lesson__course")
                .filter(lesson_id=lesson_id)
                .order_by("id")
                .first()
            )
            if theory is None:
                errors["lesson_id"] = ["Для цього уроку теорію не знайдено."]

        if errors:
            raise serializers.ValidationError(errors)

        attrs["peer_obj"] = peer
        attrs["theory_obj"] = theory
        attrs["lesson_obj"] = getattr(theory, "lesson", None)
        attrs["course_obj"] = getattr(theory.lesson, "course", None) if getattr(theory, "lesson", None) else None
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        peer = validated_data["peer_obj"]
        theory = validated_data["theory_obj"]
        lesson = validated_data["lesson_obj"]
        course = validated_data["course_obj"]

        chat, _ = Chat.objects.get_or_create(
            student=user,
            teacher=peer,
            theory=theory,
            defaults={
                "title": "",
                "course": course,
                "lesson": lesson,
            },
        )
        return chat



# ---------- Message ----------
class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "chat", "sender", "text", "attachment", "created_at", "edited_at", "is_deleted"]
        read_only_fields = ["id", "sender", "created_at", "edited_at", "is_deleted"]

    def validate(self, attrs):
        text = (attrs.get("text") or "").strip()
        file = attrs.get("attachment")
        if not text and not file:
            # FIX: помилка по полю
            raise serializers.ValidationError({"text": ["Message must contain text or attachment."]})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        chat: Chat = validated_data["chat"]

        if user.id not in (chat.student_id, chat.teacher_id):
            raise serializers.ValidationError({"chat": ["You are not a participant of this chat."]})

        msg = Message.objects.create(sender=user, **validated_data)
        Chat.objects.filter(pk=chat.pk).update(last_message=msg, updated_at=timezone.now())
        return msg


# ---------- Read marker ----------
class ReadMarkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadMarker
        fields = ["chat", "last_read_message_id"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        chat = attrs["chat"]
        if user.id not in (chat.student_id, chat.teacher_id):
            raise serializers.ValidationError({"chat": ["You are not a participant of this chat."]})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        rm, _ = ReadMarker.objects.update_or_create(
            chat=validated_data["chat"],
            user=user,
            defaults={"last_read_message_id": validated_data["last_read_message_id"]},
        )
        return rm
