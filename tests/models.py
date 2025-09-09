from django.db import models
from django.conf import settings
from lesson.models import Lesson


class Test(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        CLOSED = 'closed', 'Closed'

    lesson              = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='tests')
    title               = models.CharField(max_length=255)
    description         = models.TextField(blank=True)

    status              = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    opens_at            = models.DateTimeField(null=True, blank=True)
    closes_at           = models.DateTimeField(null=True, blank=True)
    time_limit_sec      = models.PositiveIntegerField(null=True, blank=True)  # None = без ліміту
    attempts_allowed    = models.PositiveIntegerField(default=1)              # 1..N; (0 = unlimited, якщо захочеш)
    pass_mark           = models.FloatField(default=0)                        # % чи бали — за політикою проекту
    shuffle_questions   = models.BooleanField(default=False)
    shuffle_options     = models.BooleanField(default=True)
    show_feedback_mode  = models.CharField(max_length=16, default='after_close')  # none|immediate|after_close

    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lesson']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return self.title


class Question(models.Model):
    class Type(models.TextChoices):
        SINGLE     = 'single', 'Single choice'
        MULTIPLE   = 'multiple', 'Multiple choice'
        TRUE_FALSE = 'true_false', 'True/False'
        SHORT      = 'short', 'Short answer'
        LONG       = 'long', 'Long answer'
        CODE       = 'code', 'Code'
        MATCH      = 'match', 'Matching'
        ORDER      = 'order', 'Ordering'

    test        = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    type        = models.CharField(max_length=16, choices=Type.choices)
    text        = models.TextField()
    explanation = models.TextField(blank=True)                      # показати після сабміту/закриття
    points      = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    difficulty  = models.PositiveSmallIntegerField(default=0)       # 0..5
    required    = models.BooleanField(default=True)
    spec        = models.JSONField(default=dict, blank=True)        # для MATCH/ORDER/іншого структурного
    order       = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['test']),
            models.Index(fields=['type']),
        ]

    def __str__(self) -> str:
        return self.text[:60]


class Choice(models.Model):
    """Варіанти для варіантних типів (single/multiple/true_false)."""
    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text       = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    feedback   = models.CharField(max_length=500, blank=True)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        indexes = [models.Index(fields=['question'])]

    def __str__(self) -> str:
        return self.text[:60]


class TestAttempt(models.Model):
    """Одна спроба користувача пройти тест."""
    class Status(models.TextChoices):
        STARTED   = 'started', 'Started'
        SUBMITTED = 'submitted', 'Submitted'
        GRADED    = 'graded', 'Graded'

    test        = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    attempt_no  = models.PositiveIntegerField(default=1)  # 1..attempts_allowed
    status      = models.CharField(max_length=12, choices=Status.choices, default=Status.STARTED)

    started_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_sec= models.PositiveIntegerField(null=True, blank=True)

    score       = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    max_score   = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    pass_mark   = models.FloatField(default=0)  # snapshot з Test

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'test']),
            models.Index(fields=['test', 'status']),
        ]
        unique_together = [('test', 'user', 'attempt_no')]

    def __str__(self) -> str:
        return f'{self.user} — {self.test} — try #{self.attempt_no}'


class AnswerAttempt(models.Model):
    """Відповідь на конкретне питання в межах спроби."""
    attempt          = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question         = models.ForeignKey(Question, on_delete=models.PROTECT, related_name='answer_attempts')

    # Для single/multiple/true_false:
    selected_options = models.ManyToManyField(Choice, blank=True, related_name='selected_in')

    # Для short/long/code/match/order:
    free_text        = models.TextField(blank=True)
    free_json        = models.JSONField(default=dict, blank=True)

    is_correct       = models.BooleanField(null=True, blank=True)
    score_awarded    = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    needs_manual     = models.BooleanField(default=False)

    answered_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('attempt', 'question')]
        indexes = [
            models.Index(fields=['attempt', 'question']),
            models.Index(fields=['question']),
        ]
