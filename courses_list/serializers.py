from rest_framework import serializers
from course.models import Course, Category
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_admin']

    def get_is_admin(self, obj):
        return obj.is_staff or obj.is_superuser


class CourseSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), write_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'price', 'author', 'language',
            'topic', 'image', 'rating', 'category', 'category_detail'
        ]


