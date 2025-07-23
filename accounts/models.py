from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class CustomUser(AbstractUser):
    is_email_verified = models.BooleanField(default=True)
    is_teacher = models.BooleanField(default=False)
    is_certified_teacher = models.BooleanField(default=False, null=True, blank=True)

    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        default='profile_pictures/default.png', 
        blank=True, 
        null=True
    )

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_users_groups",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_users_permissions",
        blank=True
    )

    def __str__(self):
        return self.username


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TeacherProfile: {self.user.username}"

class QualificationDocument(models.Model):
    teacher_profile = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document = models.ImageField(upload_to='qualification_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.teacher_profile.user.username}"
