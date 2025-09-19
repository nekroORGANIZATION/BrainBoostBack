from django.db.models import Q
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chat, Message, ReadMarker
from .serializers import (
    ChatSerializer, ChatStartSerializer,
    MessageSerializer, ReadMarkerSerializer,
)


class IsParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Chat):
            return request.user.id in (obj.student_id, obj.teacher_id)
        if isinstance(obj, Message):
            return request.user.id in (obj.chat.student_id, obj.chat.teacher_id)
        if isinstance(obj, ReadMarker):
            return request.user.id in (obj.chat.student_id, obj.chat.teacher_id)
        return False

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class ChatViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated, IsParticipant]

    def get_queryset(self):
        u = self.request.user
        return (
            Chat.objects
            .select_related(
                "last_message",
                "theory", "theory__lesson",
                "lesson", "course",
                "student", "teacher",
            )
            .filter(Q(student=u) | Q(teacher=u))
            .order_by("-updated_at")
        )


class StartChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ChatStartSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        chat = ser.save()
        out = ChatSerializer(chat, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)


class MessageViewSet(mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsParticipant]

    def get_queryset(self):
        u = self.request.user
        chat_id = self.request.query_params.get("chat")

        qs = (
            Message.objects
            .select_related("chat", "sender")
            .filter(Q(chat__student=u) | Q(chat__teacher=u))
        )
        if chat_id:
            qs = qs.filter(chat_id=chat_id)
        return qs.order_by("id")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class ReadMarkerView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ReadMarkerSerializer
    permission_classes = [permissions.IsAuthenticated, IsParticipant]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx
