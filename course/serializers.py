from typing import Any, Dict
from rest_framework import serializers
from django.db.models import Count, Avg
from .models import Course, Category, PurchasedCourse, Comment, Wishlist, Language, Comment
from django.conf import settings

# ===============================================================
class CommentAuthorMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


class CommentSerializer(serializers.ModelSerializer):
    author = CommentAuthorMiniSerializer(source='author', read_only=True)
    course = serializers.PrimaryKeyRelatedField(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Comment
        fields = [
            'id', 'course', 'author', 'text',
            'parent', 'created_at', 'updated_at', 'is_edited',
        ]
        read_only_fields = ['id', 'course', 'author', 'created_at', 'updated_at', 'is_edited']

    def validate_text(self, value: str):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Текст комментария не может быть пустым.')
        if len(value) > 5000:
            raise serializers.ValidationError('Слишком длинный комментарий (макс. 5000 символов).')
        return value

    def create(self, validated_data):
        request = self.context['request']
        course = self.context['course']     
        validated_data['author'] = request.user
        validated_data['course'] = course
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'text' in validated_data and validated_data['text'] != instance.text:
            instance.is_edited = True
        return super().update(instance, validated_data)


class CommentListSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'text', 'author_username', 'created_at', 'parent']
        read_only_fields = fields
# ===========================================================================



class CategoryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "name"]


class WishlistCourseMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("id", "title", "image", "price", "rating")  # подгони поля под свою модель

class WishlistSerializer(serializers.ModelSerializer):
    course = WishlistCourseMiniSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), write_only=True, source="course"
    )

    class Meta:
        model = Wishlist
        fields = ("id", "course", "course_id", "created_at")
        read_only_fields = ("id", "created_at")


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
    language_name = serializers.CharField(source="language.name", read_only=True)
    total_lessons = serializers.IntegerField(read_only=True)
    is_purchased = serializers.SerializerMethodField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "slug", "title", "description", "price", "language", "language_name", "topic",
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
