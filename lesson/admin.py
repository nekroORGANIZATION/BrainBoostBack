from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django import forms

from .models import Lesson, Module, LessonContent, LessonProgress


# ====== ЗАГАЛЬНІ НАЛАШТУВАННЯ ======
class JSONTextarea(forms.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("rows", 10)
        kwargs["attrs"].setdefault("style", "font-family: monospace;")
        super().__init__(*args, **kwargs)


class LessonContentInline(admin.TabularInline):
    model = LessonContent
    extra = 0
    fields = ("type", "order", "is_hidden", "data")
    ordering = ("order", "id")
    # JSONField у сучасному Django і так має нормальний віджет, але на всяк:
    formfield_overrides = {
        # Якщо у вас models.JSONField — Django сам поставить JSONEditor.
        # Якщо це TextField — примусово робимо моноширинний textarea:
        # models.TextField: {"widget": JSONTextarea},  # розкоментуйте, якщо data=TextField
    }
    # Не даємо міняти lesson з інлайну (FK фіксований)
    readonly_fields = ()
    show_change_link = True


# ====== MODULE ADMIN ======
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course", "order", "is_visible", "lessons_count")
    list_filter = ("is_visible", "course")
    search_fields = ("title", "description")
    ordering = ("course", "order", "id")
    # Використай raw_id_fields щоб не залежати від autocomplete у чужих адмінах
    raw_id_fields = ("course",)

    actions = ("make_visible", "make_hidden", "normalize_order")

    @admin.display(description="К-сть уроків")
    def lessons_count(self, obj: Module) -> int:
        # related_name у вас не вказаний у коді вище, тому fallback:
        try:
            return obj.lesson_set.count()
        except Exception:
            try:
                return obj.lessons.count()
            except Exception:
                return 0

    @admin.action(description="Зробити видимими")
    def make_visible(self, request, queryset):
        n = queryset.update(is_visible=True)
        self.message_user(request, f"Оновлено {n} модулів: видимі.", messages.SUCCESS)

    @admin.action(description="Приховати")
    def make_hidden(self, request, queryset):
        n = queryset.update(is_visible=False)
        self.message_user(request, f"Оновлено {n} модулів: приховані.", messages.SUCCESS)

    @admin.action(description="Нормалізувати порядок (1..N)")
    def normalize_order(self, request, queryset):
        # Всередині кожного курсу відсортуємо модулі за поточним order,id і перенумеруємо
        by_course = {}
        for m in queryset.order_by("course", "order", "id"):
            by_course.setdefault(m.course_id, []).append(m)
        total = 0
        for _, mods in by_course.items():
            for idx, m in enumerate(mods, start=1):
                if m.order != idx:
                    m.order = idx
                    m.save(update_fields=["order"])
                    total += 1
        self.message_user(request, f"Переупорядковано елементів: {total}.", messages.INFO)


# ====== LESSON ADMIN ======
class HasCoverFilter(admin.SimpleListFilter):
    title = "обкладинка"
    parameter_name = "has_cover"

    def lookups(self, request, model_admin):
        return (("yes", "є"), ("no", "нема"))

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.exclude(cover_image="")
        if val == "no":
            return queryset.filter(cover_image="")
        return queryset


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    inlines = [LessonContentInline]

    # — колонки списку
    list_display = (
        "id", "title", "course", "module", "order",
        "status", "duration_min", "content_blocks",
        "created_at", "published_at", "preview_link",
    )
    list_filter = ("status", "course", "module", HasCoverFilter, "created_at", "published_at")
    search_fields = ("title", "slug", "summary")
    date_hierarchy = "created_at"
    ordering = ("course", "module", "order", "id")

    # — поля форми
    fieldsets = (
        ("Базове", {
            "fields": (
                ("course", "module"),
                ("title", "slug"),
                "summary",
                ("order", "status"),
            )
        }),
        ("Планування/публікація", {
            "classes": ("collapse",),
            "fields": (("scheduled_at", "published_at"), "duration_min"),
        }),
        ("Медіа", {
            "fields": ("cover_image",),
        }),
        ("Службові", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )
    readonly_fields = ("created_at", "updated_at")
    # raw_id_fields щоб не залежати від адмінок інших застосунків
    raw_id_fields = ("course", "module")

    save_on_top = True
    list_per_page = 50

    actions = ("mark_published", "mark_draft", "reseq_in_module")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Оптимізація джоїнів і підрахунку блоків
        try:
            qs = qs.select_related("course", "module").prefetch_related("contents")
        except Exception:
            qs = qs.select_related("course", "module")
        return qs

    @admin.display(description="Блоків", ordering=False)
    def content_blocks(self, obj: Lesson) -> int:
        try:
            return obj.contents.count()
        except Exception:
            try:
                return obj.lessoncontent_set.count()
            except Exception:
                return 0

    @admin.display(description="Перегляд", ordering=False)
    def preview_link(self, obj: Lesson):
        # Публічна деталь у ваших urls: /lesson/public/lessons/id/<id>/
        url = f"/lesson/public/lessons/id/{obj.id}/"
        return format_html('<a href="{}" target="_blank">відкрити →</a>', url)

    # ---- дії ----
    @admin.action(description="Опублікувати вибрані (status='published')")
    def mark_published(self, request, queryset):
        n = queryset.update(status="published", published_at=timezone.now())
        self.message_user(request, f"Опубліковано уроків: {n}.", messages.SUCCESS)

    @admin.action(description="Зробити чернеткою (status='draft')")
    def mark_draft(self, request, queryset):
        n = queryset.update(status="draft")
        self.message_user(request, f"Переведено у чернетку уроків: {n}.", messages.INFO)

    @admin.action(description="Нормалізувати порядок в межах кожного модуля (1..N)")
    def reseq_in_module(self, request, queryset):
        by_module = {}
        for l in queryset.order_by("module", "order", "id"):
            by_module.setdefault(l.module_id, []).append(l)
        total = 0
        for _, lessons in by_module.items():
            for idx, l in enumerate(lessons, start=1):
                if l.order != idx:
                    l.order = idx
                    l.save(update_fields=["order"])
                    total += 1
        self.message_user(request, f"Переупорядковано позицій: {total}.", messages.INFO)


# ====== LESSON CONTENT ADMIN (окремий список, якщо треба масово правити) ======
@admin.register(LessonContent)
class LessonContentAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "type", "order", "is_hidden", "data_short")
    list_filter = ("type", "is_hidden")
    search_fields = ("lesson__title",)
    ordering = ("lesson", "order", "id")
    raw_id_fields = ("lesson",)

    @admin.display(description="data (коротко)")
    def data_short(self, obj: LessonContent):
        # показуємо перші ~120 символів JSON
        try:
            s = str(obj.data)
        except Exception:
            s = ""
        return (s[:120] + "…") if len(s) > 120 else s


# ====== LESSON PROGRESS ADMIN ======
@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "lesson", "state", "result_percent", "updated_at")
    list_filter = ("state", "updated_at")
    search_fields = ("user__username", "user__email", "lesson__title")
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    raw_id_fields = ("user", "lesson")
