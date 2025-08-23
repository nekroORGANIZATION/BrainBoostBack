from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

# Оставляем один корректный импорт из своих моделей
from .models import TeacherProfile, QualificationDocument
from admin_panel.models import TeacherApplication

# КЛЮЧЕВАЯ строка: берем кастомного пользователя через settings.AUTH_USER_MODEL
User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        # Если у твоего кастомного User есть manager с create_user — ОК
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        user.is_active = True
        user.save(update_fields=['is_active'])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'is_email_verified',   # readonly
            'is_teacher',          # readonly
            'is_certified_teacher',
            'is_superuser',        # readonly
            'profile_picture',
            'first_name',
            'last_name',
        ]
        read_only_fields = ['is_email_verified', 'is_teacher', 'is_superuser']

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.is_certified_teacher = validated_data.get(
            'is_certified_teacher', instance.is_certified_teacher
        )
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)

        profile_picture = validated_data.get('profile_picture', None)
        if profile_picture is not None:
            instance.profile_picture = profile_picture

        instance.save()
        return instance


class QualificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualificationDocument
        fields = ['document']


class TeacherRegisterSerializer(serializers.ModelSerializer):
    # принимаем фото + заметку
    selfie_photo = serializers.ImageField(required=False, allow_null=True)
    id_photo = serializers.ImageField(required=False, allow_null=True)
    diploma_photo = serializers.ImageField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password',
            'selfie_photo', 'id_photo', 'diploma_photo', 'note'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        selfie = validated_data.pop('selfie_photo', None)
        idph  = validated_data.pop('id_photo', None)
        dipl  = validated_data.pop('diploma_photo', None)
        note  = validated_data.pop('note', '')

        # можно использовать create_user, но твой подход с make_password тоже ок
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            password=make_password(validated_data['password']),
            is_teacher=True,
            is_certified_teacher=False,
            is_email_verified=True,
        )

        TeacherProfile.objects.create(user=user)

        TeacherApplication.objects.create(
            user=user,
            selfie_photo=selfie,
            id_photo=idph,
            diploma_photo=dipl,
            note=note,
            status='pending',
        )
        return user
