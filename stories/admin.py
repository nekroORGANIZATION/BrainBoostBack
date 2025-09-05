from django.contrib import admin
from .models import Story


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author_name", "published_at")
    list_filter = ("published_at",)
    search_fields = ("title", "author_name")
