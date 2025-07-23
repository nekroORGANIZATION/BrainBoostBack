from rest_framework import serializers
from .models import Course, Comment
from django.contrib.auth import get_user_model


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'course', 'author', 'author_username', 'text', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'price', 'author',
            'language', 'topic', 'image', 'rating'
        ]
        read_only_fields = ['id', 'author', 'rating']
