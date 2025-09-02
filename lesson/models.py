from django.db import models
from django.conf import settings
from course.models import Course


class Module(models.Model):
    """
    Логічний розділ курсу. Допомагає групувати уроки і керувати порядком.
    """
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

    course         = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    module         = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons')

    title          = models.CharField(max_length=200)
    slug           = models.SlugField(max_length=220, unique=True)

    summary        = models.TextField(blank=True)
    order          = models.PositiveIntegerField(default=0, db_index=True)
    status         = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    scheduled_at   = models.DateTimeField(null=True, blank=True)
    published_at   = models.DateTimeField(null=True, blank=True)

    duration_min   = models.PositiveIntegerField(null=True, blank=True)  # опц.: тривалість уроку хв.
    cover_image    = models.ImageField(upload_to='lesson_covers/', null=True, blank=True)

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes  = [
            models.Index(fields=['course']),
            models.Index(fields=['module']),
            models.Index(fields=['status']),
        ]
        unique_together = [('course', 'title')]

    def __str__(self):
        return self.title


class LessonContent(models.Model):
    """
    Блочний контент уроку (редактор з блоків).
    data — JSON зі структурою під тип.
    """
    class Type(models.TextChoices):
        TEXT      = 'text',      'Text'
        IMAGE     = 'image',     'Image'
        VIDEO     = 'video',     'Video'
        CODE      = 'code',      'Code'
        FILE      = 'file',      'File'
        QUOTE     = 'quote',     'Quote'
        CHECKLIST = 'checklist', 'Checklist'
        HTML      = 'html',      'HTML'

    lesson   = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='contents')
    type     = models.CharField(max_length=16, choices=Type.choices)
    data     = models.JSONField(default=dict, blank=True)  # {text, url, language, items, ...}
    order    = models.PositiveIntegerField(default=0, db_index=True)
    is_hidden= models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'id']
        indexes  = [models.Index(fields=['lesson', 'order'])]

    def __str__(self):
        return f'[{self.type}] {self.lesson.title} #{self.order}'


class LessonProgress(models.Model):
    """
    Прогрес користувача по уроку.
    """
    class State(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not started'
        STARTED     = 'started',     'Started'
        COMPLETED   = 'completed',   'Completed'

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson      = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    state       = models.CharField(max_length=16, choices=State.choices, default=State.NOT_STARTED)
    started_at  = models.DateTimeField(null=True, blank=True)
    completed_at= models.DateTimeField(null=True, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'lesson')]
        indexes = [
            models.Index(fields=['user', 'lesson']),
            models.Index(fields=['lesson', 'state']),
        ]

    def __str__(self):
        return f'{self.user} — {self.lesson} — {self.state}'
