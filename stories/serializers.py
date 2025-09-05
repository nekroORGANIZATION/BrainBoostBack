from rest_framework import serializers
from .models import Story


class StoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = ["id", "title", "cover", "published_at", "author_name"]


class StoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = ["id", "title", "content", "cover", "published_at", "author_name"]
