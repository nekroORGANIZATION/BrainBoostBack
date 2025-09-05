from django.conf import settings
from django.db import models


def upload_teacher_doc(instance, filename):
    return f"teachers/{instance.user_id}/{filename}"

class TeacherApplication(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_application")
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    note = models.TextField(blank=True)

    # фото / документы
    selfie_photo = models.ImageField(upload_to=upload_teacher_doc, blank=True, null=True)
    id_photo = models.ImageField(upload_to=upload_teacher_doc, blank=True, null=True)
    diploma_photo = models.ImageField(upload_to=upload_teacher_doc, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"TeacherApplication(user={self.user_id}, status={self.status})"
    