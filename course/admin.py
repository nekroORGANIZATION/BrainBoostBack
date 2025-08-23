from django.contrib import admin
from .models import Course, Category, PurchasedCourse, Comment, CourseDone


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "status", "price", "rating", "created_at")
    list_filter = ("status", "category", "language")
    search_fields = ("title", "topic", "description")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)


@admin.register(PurchasedCourse)
class PurchasedCourseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "is_active", "purchased_at")
    list_filter = ("is_active", "purchased_at")
    raw_id_fields = ("user", "course")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "author", "created_at")
    search_fields = ("text",)
    raw_id_fields = ("course", "author")


@admin.register(CourseDone)
class CourseDoneAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "user", "completed_at")
    raw_id_fields = ("course", "user")
