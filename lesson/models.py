from django.db import models
from django.conf import settings
from course.models import Course


class Module(models.Model):
    """Логічний розділ курсу."""
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order       = models.PositiveIntegerField(default=0, db_index=True)
    is_visible  = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('course', 'title')]

    def __str__(self):
        return f'{self.course.title} — {self.title}'


class Lesson(models.Model):
    class Status(models.TextChoices):
        DRAFT     = 'draft', 'Draft'
        SCHEDULED = 'scheduled', 'Scheduled'
        PUBLISHED = 'published', 'Published'
        ARCHIVED  = 'archived', 'Archived'

    course       = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    module       = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons')

    title        = models.CharField(max_length=200)
    # slug є, але ми ним не користуємось для валідації/унікальності
    slug         = models.SlugField(max_length=255, null=True, blank=True)

    summary      = models.TextField(blank=True)   # для карток/пошуку (може генеритись з першого текст-блоку)
    order        = models.PositiveIntegerField(default=0, db_index=True)
    status       = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    duration_min = models.PositiveIntegerField(null=True, blank=True)
    cover_image  = models.ImageField(upload_to='lesson_covers/', null=True, blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes  = [
            models.Index(fields=['course']),
            models.Index(fields=['module']),
            models.Index(fields=['status']),
        ]
        # ⬇️ важливо: НЕ обмежуємо унікальність (course, title) і НЕ робимо slug унікальним

    def __str__(self):
        return self.title


class LessonContent(models.Model):
    """
    Блочний контент уроку.
    data — JSON зі структурою під тип.
    """
    class Type(models.TextChoices):
        TEXT      = 'text',      'Text'       # data: {html | text}
        IMAGE     = 'image',     'Image'      # data: {url, caption?}
        VIDEO     = 'video',     'Video'      # data: {url}
        CODE      = 'code',      'Code'       # data: {language, code, runnable?}
        FILE      = 'file',      'File'       # data: {url, name?}
        QUOTE     = 'quote',     'Quote'      # data: {text, cite?}
        CHECKLIST = 'checklist', 'Checklist'  # data: {items: [{text, checked}]}
        HTML      = 'html',      'HTML'       # data: {html}
        COLUMNS   = 'columns',   'Columns'    # data: {cols: [{html}, {html}]}
        CALLOUT   = 'callout',   'Callout'    # data: {tone: info|warn|ok, html}

    lesson    = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='contents')
    type      = models.CharField(max_length=16, choices=Type.choices)
    data      = models.JSONField(default=dict, blank=True)
    order     = models.PositiveIntegerField(default=0, db_index=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'id']
        indexes  = [models.Index(fields=['lesson', 'order'])]

    def __str__(self):
        return f'[{self.type}] {self.lesson.title} #{self.order}'


class LessonProgress(models.Model):
    class State(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not started'
        STARTED     = 'started',     'Started'
        COMPLETED   = 'completed',   'Completed'

    user           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson         = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    state          = models.CharField(max_length=16, choices=State.choices, default=State.NOT_STARTED)
    result_percent = models.IntegerField(null=True, blank=True)
    started_at     = models.DateTimeField(null=True, blank=True)
    completed_at   = models.DateTimeField(null=True, blank=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'lesson')]
        indexes = [
            models.Index(fields=['user', 'lesson']),
            models.Index(fields=['lesson', 'state']),
        ]

    def __str__(self):
        return f'{self.user} — {self.lesson} — {self.state}'