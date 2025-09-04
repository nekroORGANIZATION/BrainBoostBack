# chat/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

UserModel = settings.AUTH_USER_MODEL


class Chat(models.Model):
    title = models.CharField(max_length=255, blank=True)

    course = models.ForeignKey(
        'course.Course', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='chats'
    )
    lesson = models.ForeignKey(
        'lesson.Lesson', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='chats'
    )
    theory = models.ForeignKey(
        'lesson.LessonContent', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='chats'
    )

    student = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name='student_chats'
    )
    teacher = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name='teacher_chats'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message = models.ForeignKey(
        'Message', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            # один чат на пару (student, teacher) по одной теории
            models.UniqueConstraint(
                fields=['student', 'teacher', 'theory'],
                name='uniq_chat_student_teacher_theory'
            ),
        ]

    def __str__(self):
        base = self.title or f'Chat #{self.pk}'
        if self.theory_id:
            return f'{base} (theory={self.theory_id})'
        return base


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='messages_sent')

    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']  # стабильная пагинация по id

    def soft_delete(self):
        self.is_deleted = True
        self.text = ''
        self.edited_at = timezone.now()
        self.save(update_fields=['is_deleted', 'text', 'edited_at'])


class ReadMarker(models.Model):
    """
    Для непрочитанных: на какого message_id пользователь дочитал чат.
    """
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='read_markers')
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='chat_read_markers')
    last_read_message_id = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ('chat', 'user')

    def __str__(self):
        return f'RM(chat={self.chat_id}, user={self.user_id}, last={self.last_read_message_id})'
