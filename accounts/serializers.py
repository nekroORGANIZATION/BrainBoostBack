from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import CustomUser

from .models import TeacherProfile, QualificationDocument
from django.contrib.auth.hashers import make_password

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
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        user.is_active = False
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'is_email_verified',
            'is_teacher',
            'is_certified_teacher',
            'profile_picture',
        ]



#  --->
class QualificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualificationDocument
        fields = ['document']

class TeacherRegisterSerializer(serializers.ModelSerializer):
    documents = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'documents']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        documents = validated_data.pop('documents')

        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            password=make_password(validated_data['password']),
            is_teacher=True,
            is_certified_teacher=False,
            is_email_verified=False,
        )

        teacher_profile = TeacherProfile.objects.create(user=user)

        for doc in documents:
            QualificationDocument.objects.create(teacher_profile=teacher_profile, document=doc)

        return user
