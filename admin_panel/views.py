from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from accounts.models import TeacherProfile
from .serializers import TeacherProfileAdminSerializer, UserListSerializer, TeacherDetailSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class AllUsersView(APIView):
    permission_classes = [AllowAny] 

    def get(self, request):
        users = User.objects.all()
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)


class UnverifiedTeachersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        profiles = TeacherProfile.objects.filter(user__is_teacher=True, user__is_certified_teacher=False)
        serializer = TeacherProfileAdminSerializer(profiles, many=True)
        return Response(serializer.data)


class VerifyTeacherView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, is_teacher=True)
            user.is_certified_teacher = True
            user.save()
            return Response({'message': 'Teacher verified successfully.'})
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class TeacherDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, is_teacher=True)
            serializer = TeacherDetailSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)
