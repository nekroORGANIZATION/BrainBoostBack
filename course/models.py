from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Avg
from decimal import Decimal, ROUND_HALF_UP


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Course(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title       = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    description = models.TextField()
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    author      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses")
    language    = models.CharField(max_length=50)
    topic       = models.CharField(max_length=100)
    image       = models.ImageField(upload_to="course_images/", blank=True, null=True)

    rating      = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses")

    status      = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:220]
            slug = base
            i = 2
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # допоміжні агрегати (не зберігаємо, щоб не плодити денормалізацію)
    @property
    def total_lessons(self) -> int:
        return getattr(self, "lessons", None) and self.lessons.count() or 0

    @property
    def average_rating(self) -> Decimal:
        # якщо у тебе є app reviews з APPROVED — можна рахувати на льоту
        if hasattr(self, "reviews"):
            agg = self.reviews.filter(status="approved").aggregate(a=Avg("rating"))
            val = Decimal(agg["a"] or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return val
        return self.rating


class PurchasedCourse(models.Model):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchased_courses")
    course       = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="purchases")
    purchased_at = models.DateTimeField(auto_now_add=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        unique_together = [("user", "course")]
        indexes = [
            models.Index(fields=["user", "course"]),
            models.Index(fields=["course", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} purchased {self.course}"


class Comment(models.Model):
    course     = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="comments")
    author     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["course", "created_at"])]

    def __str__(self) -> str:
        return f"Comment by {self.author} on {self.course.title}"


class CourseDone(models.Model):
    course       = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="courses_done")
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="done_by")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("course", "user")]
        indexes = [models.Index(fields=["user", "course"])]

    def __str__(self):
        return f"{self.user} completed {self.course.title}"
