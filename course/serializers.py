from rest_framework import serializers
from .models import Course, Comment
from django.contrib.auth import get_user_model


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'author', 'author_username', 'text', 'created_at', 'course']
        read_only_fields = ['id', 'author', 'created_at', 'course']

    def get_author_username(self, obj):
        return obj.author.username if obj.author else None


class CourseSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'price', 'author_username',
            'language', 'topic', 'image', 'rating'
        ]
        read_only_fields = ['id', 'author_username']
