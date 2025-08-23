from typing import Any, Dict
from rest_framework import serializers
from django.db.models import Count, Avg
from .models import Course, Category, PurchasedCourse, Comment
from django.conf import settings


class CategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "courses_count"]


class AuthorMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class CourseListSerializer(serializers.ModelSerializer):
    author = AuthorMiniSerializer(source="author.__dict__", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    total_lessons = serializers.IntegerField(read_only=True)
    is_purchased = serializers.SerializerMethodField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "slug", "title", "description", "price", "language", "topic",
            "image", "rating", "category", "category_name",
            "status", "created_at", "updated_at",
            "total_lessons", "is_purchased", "author",
        ]

    def get_is_purchased(self, obj: Course) -> bool:
        user = self.context.get("request") and self.context["request"].user or None
        if not user or not user.is_authenticated:
            return False
        return PurchasedCourse.objects.filter(user=user, course=obj, is_active=True).exists()


class CourseDetailSerializer(CourseListSerializer):
    average_rating = serializers.SerializerMethodField()

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + ["average_rating"]

    def get_average_rating(self, obj: Course):
        return obj.average_rating


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "id",  # важно!
            "title", "slug", "description", "price",
            "language", "topic", "image", "category", "status",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def create(self, validated_data: Dict[str, Any]) -> Course:
        user = self.context["request"].user
        return Course.objects.create(author=user, **validated_data)

    def update(self, instance: Course, validated_data: Dict[str, Any]) -> Course:
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance


class PurchasedCourseSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = PurchasedCourse
        fields = ["id", "course", "purchased_at", "is_active"]


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "course", "author", "author_name", "text", "created_at"]
        read_only_fields = ["author", "created_at"]

    def get_author_name(self, obj):
        # підлаштуй під свою модель користувача
        if hasattr(obj.author, "first_name") or hasattr(obj.author, "last_name"):
            fn = (obj.author.first_name or "").strip()
            ln = (obj.author.last_name or "").strip()
            full = (fn + " " + ln).strip()
            return full or obj.author.username
        return getattr(obj.author, "username", "User")

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["author"] = request.user
        return super().create(validated_data)
