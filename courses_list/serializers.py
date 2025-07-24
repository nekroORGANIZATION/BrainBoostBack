from rest_framework import serializers
from course.models import Course, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class CourseSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True, allow_null=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'price', 'author', 'language',
            'topic', 'image', 'rating', 'category'
        ]
