from django.db import models
from django.conf import settings


class Course(models.Model):
    title: str = models.CharField(max_length=200)
    description: str = models.TextField()
    price: float = models.DecimalField(max_digits=10, decimal_places=2)
    author: str = models.CharField(max_length=100)
    language: str = models.CharField(max_length=50)
    topic: str = models.CharField(max_length=100)
    image = models.ImageField(upload_to='course_images/', blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Comment by {self.author} on {self.course.title}'
