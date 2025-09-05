from django.contrib import admin
from .models import Course, Category, PurchasedCourse, Comment, CourseDone, Wishlist, Language
from django.contrib import messages
from django.db.models import Count


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "courses_count")
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_courses_count=Count("courses"))

    def courses_count(self, obj):
        return getattr(obj, "_courses_count", 0)
    courses_count.short_description = "Курсов"

    actions = ["safe_delete"]

    def safe_delete(self, request, queryset):
        blocked = queryset.annotate(c=Count("courses")).filter(c__gt=0)
        if blocked.exists():
            messages.error(request, f"Нельзя удалить {blocked.count()} категори(ю/и) — привязаны курсы.")
        deletable = queryset.exclude(pk__in=blocked.values_list("pk", flat=True))
        count = deletable.count()
        deletable.delete()
        if count:
            messages.success(request, f"Удалено категорий: {count}")
    safe_delete.short_description = "Безопасное удаление (не удалять с привязанными курсами)"

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "courses_count")
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_courses_count=Count("courses"))

    def courses_count(self, obj):
        return getattr(obj, "_courses_count", 0)
    courses_count.short_description = "Курсов"


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


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__username", "course__title")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "author", "created_at")
    search_fields = ("text",)
    raw_id_fields = ("course", "author")


@admin.register(CourseDone)
class CourseDoneAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "user", "completed_at")
    raw_id_fields = ("course", "user")
