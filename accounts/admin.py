from django.contrib import admin
from .models import CustomUser, Certificate

admin.site.register(CustomUser),


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("id", "user")           # додай поля, які є в моделі (наприклад course/created_at)
    search_fields = ("id", "user__email", "user__username")
