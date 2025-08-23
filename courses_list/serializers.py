from rest_framework import serializers
from course.models import Course


class PublicCourseCardSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    author_name = serializers.SerializerMethodField()
    total_lessons = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "slug", "title", "description", "price",
            "language", "topic", "image", "rating",
            "category", "category_name", "status",
            "total_lessons", "author_name", "created_at",
        ]

    def get_author_name(self, obj):
        u = getattr(obj, "author", None)
        if not u:
            return ""
        full = (getattr(u, "first_name", "") + " " + getattr(u, "last_name", "")).strip()
        return full or getattr(u, "username", "")
