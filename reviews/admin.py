from django.contrib import admin
from .models import Review, ReviewImage


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating', 'course')
    search_fields = ('user__username', 'text', 'course__title')
    ordering = ('-created_at',)
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(status=Review.Status.APPROVED)
    approve_reviews.short_description = "Схвалити вибрані відгуки"

    def reject_reviews(self, request, queryset):
        queryset.update(status=Review.Status.REJECTED)
    reject_reviews.short_description = "Відхилити вибрані відгуки"


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'uploaded_at')
