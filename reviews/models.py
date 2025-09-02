from django.conf import settings
from django.db import models
from django.db.models import Avg
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'На модерації'
        APPROVED = 'approved', 'Схвалено'
        REJECTED = 'rejected', 'Відхилено'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    course = models.ForeignKey(
        'course.Course',
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    rating = models.PositiveSmallIntegerField()
    text = models.TextField()

    tags = models.CharField(max_length=255, blank=True, default='')
    video_url = models.URLField(blank=True, default='')

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )

    # ХТО/КОЛИ модерує
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='moderated_reviews'
    )
    moderation_reason = models.CharField(max_length=300, blank=True, default='')
    moderated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user_name_snapshot = models.CharField(max_length=255, blank=True, default='')
    user_avatar_snapshot = models.URLField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_review_per_user_course'
            )
        ]
        indexes = [
            models.Index(fields=['course', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.user} — {self.course} — {self.rating}★'


class ReviewImage(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='review_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Image for review #{self.review_id}'


@receiver(pre_save, sender=Review)
def fill_user_snapshots(sender, instance: Review, **kwargs):
    if not instance.user_id:
        return
    if not instance.user_name_snapshot:
        first = getattr(instance.user, 'first_name', '') or ''
        last = getattr(instance.user, 'last_name', '') or ''
        full = (first + ' ' + last).strip()
        instance.user_name_snapshot = full or getattr(instance.user, 'username', '')
    if not instance.user_avatar_snapshot:
        avatar = getattr(instance.user, 'profile_picture', None)
        url = ''
        if avatar:
            try:
                url = avatar.url
            except Exception:
                url = str(avatar)
        instance.user_avatar_snapshot = url


def _recalc_course_rating(course):
    from decimal import Decimal, ROUND_HALF_UP
    qs = course.reviews.filter(status=Review.Status.APPROVED)
    agg = qs.aggregate(a=Avg('rating'))
    avg = agg['a'] or 0
    avg_dec = Decimal(avg).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    course.rating = avg_dec
    course.save(update_fields=['rating'])


@receiver(post_save, sender=Review)
def update_course_rating_on_save(sender, instance: Review, created, **kwargs):
    try:
        _recalc_course_rating(instance.course)
    except Exception:
        pass


@receiver(post_delete, sender=Review)
def update_course_rating_on_delete(sender, instance: Review, **kwargs):
    try:
        _recalc_course_rating(instance.course)
    except Exception:
        pass
