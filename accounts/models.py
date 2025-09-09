from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

import uuid
from django.db import models
from django.conf import settings
from course.models import Course


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


def _default_serial():
    return uuid.uuid4().hex[:12].upper()

class Certificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')

    serial = models.CharField(max_length=32, unique=True, db_index=True, default=_default_serial)
    final_score = models.IntegerField(null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    is_revoked = models.BooleanField(default=False)

    pdf = models.FileField(upload_to='certificates/', null=True, blank=True)

    class Meta:
        unique_together = [('user', 'course')]

    def __str__(self):
        return f'Cert {self.serial} — {self.user} — {self.course}'
