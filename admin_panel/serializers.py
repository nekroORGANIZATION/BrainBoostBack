from rest_framework import serializers
from django.contrib.auth import get_user_model

from accounts.models import TeacherProfile, QualificationDocument
from .models import TeacherApplication

User = get_user_model()


# ===== Users / Profiles =====

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_teacher', 'is_certified_teacher', 'is_email_verified']


class QualificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualificationDocument
        fields = ['id', 'document', 'uploaded_at']


class TeacherProfileAdminSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.EmailField(source='user.email')
    is_certified_teacher = serializers.BooleanField(source='user.is_certified_teacher')
    documents = QualificationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = TeacherProfile
        fields = ['user_id', 'username', 'email', 'is_certified_teacher', 'documents']


class TeacherDetailSerializer(serializers.ModelSerializer):
    documents = QualificationDocumentSerializer(source='teacher_profile.documents', many=True)
    teacher_profile_created = serializers.DateTimeField(source='teacher_profile.created_at', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'is_teacher', 'is_certified_teacher', 'is_email_verified',
            'teacher_profile_created', 'documents'
        ]


# ===== Teacher Applications =====

class TeacherApplicationSerializer(serializers.ModelSerializer):
    """
    Серіалізатор заявки на підтвердження.
    Поля user/status/created_at/updated_at — read-only.
    """
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TeacherApplication
        fields = [
            'id',
            'user',
            'status',
            'note',
            'selfie_photo',
            'id_photo',
            'diploma_photo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at']

    def get_user(self, obj):
        u = obj.user
        return {
            'id': u.id,
            'username': u.username,
            'email': getattr(u, 'email', None),
        }

    def validate(self, attrs):
        """
        Забороняємо створювати другу заявку.
        """
        request = self.context.get('request')
        if request and request.method == 'POST':
            if TeacherApplication.objects.filter(user=request.user).exists():
                raise serializers.ValidationError('Заявка вже існує.')
        return attrs

    def update(self, instance, validated_data):
        """
        Учитель не може змінювати статус; дозволяємо оновлювати файли/примітку, якщо статус pending.
        """
        request = self.context.get('request')
        if request and not request.user.is_staff:
            # захищаємо статус
            validated_data.pop('status', None)
            # якщо заявка вже розглянута — забороняємо правки
            if instance.status != 'pending':
                raise serializers.ValidationError('Заявку вже розглянуто, редагування недоступне.')
        return super().update(instance, validated_data)
