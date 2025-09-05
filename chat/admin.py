# chat/admin.py
from django.contrib import admin
from .models import Chat, Message, ReadMarker

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'teacher', 'theory', 'updated_at', 'last_message')
    list_filter = ('updated_at',)
    search_fields = ('id', 'title')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'sender', 'created_at', 'is_deleted')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('text',)

@admin.register(ReadMarker)
class ReadMarkerAdmin(admin.ModelAdmin):
    list_display = ('chat', 'user', 'last_read_message_id')
    search_fields = ('chat__id', 'user__id')
