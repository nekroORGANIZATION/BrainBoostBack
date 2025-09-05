from rest_framework import serializers
from django.db.models import Q
from .models import Review, ReviewImage

class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['id', 'image']


class ReviewSerializer(serializers.ModelSerializer):
    """Публічне відображення (approved)."""
    user_name = serializers.CharField(source='user_name_snapshot', read_only=True)
    user_avatar = serializers.CharField(source='user_avatar_snapshot', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'course', 'rating', 'text', 'video_url',
            'user_name', 'user_avatar', 'images',
            'created_at'
        ]


class MyReviewSerializer(serializers.ModelSerializer):
    """Для /mine — показує також статус модерації."""
    user_name = serializers.CharField(source='user_name_snapshot', read_only=True)
    user_avatar = serializers.CharField(source='user_avatar_snapshot', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'course', 'rating', 'text', 'video_url',
            'status', 'moderation_reason',
            'created_at', 'updated_at',
            'user_name', 'user_avatar', 'images',
        ]


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['course', 'rating', 'text', 'video_url']  # ← без tags

    def validate(self, attrs):
        user = self.context['request'].user
        course = attrs.get('course')
        if Review.objects.filter(user=user, course=course).exists():
            raise serializers.ValidationError("Ви вже залишали відгук до цього курсу.")
        rating = attrs.get('rating', 0)
        if not 1 <= rating <= 5:
            raise serializers.ValidationError("Рейтинг має бути від 1 до 5.")
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        return Review.objects.create(user=user, **validated_data)


class ReviewModerationSerializer(serializers.ModelSerializer):
    """Дозволяємо змінити лише статус + причину (опційно)."""
    moderation_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Review
        fields = ['status', 'moderation_reason']

    def validate_status(self, v):
        allowed = {Review.Status.APPROVED, Review.Status.REJECTED, Review.Status.PENDING}
        if v not in allowed:
            raise serializers.ValidationError("Неприпустимий статус.")
        return v

    def update(self, instance, validated_data):
        request = self.context['request']
        instance.status = validated_data.get('status', instance.status)
        instance.moderation_reason = validated_data.get('moderation_reason', '')
        instance.moderated_by = getattr(request, 'user', None)
        from django.utils import timezone
        instance.moderated_at = timezone.now()
        instance.save()
        return instance


class ReviewAdminSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user_name_snapshot', read_only=True)
    user_avatar = serializers.CharField(source='user_avatar_snapshot', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            "id","course","rating","text","video_url",
            "status","moderation_reason","created_at",
            "user_name","user_avatar","images",
        ]
