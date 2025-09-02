from rest_framework import serializers
from accounts.models import TeacherProfile, QualificationDocument
from django.contrib.auth import get_user_model
from .models import TeacherApplication

User = get_user_model()


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
            'teacher_profile_created',
            'documents'
        ]


class TeacherApplicationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = TeacherApplication
        fields = [
            'id', 'user', 'status', 'note',
            'selfie_photo', 'id_photo', 'diploma_photo',
            'created_at',
        ]

    def get_user(self, obj):
        u = obj.user
        return {'id': u.id, 'username': u.username, 'email': getattr(u, 'email', None)}
        