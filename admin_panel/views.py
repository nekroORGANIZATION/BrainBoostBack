from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import permissions, generics, status
from django.shortcuts import get_object_or_404

from accounts.models import TeacherProfile
from .serializers import TeacherProfileAdminSerializer, UserListSerializer, TeacherDetailSerializer
from django.contrib.auth import get_user_model

from .models import TeacherApplication
from .serializers import TeacherApplicationSerializer

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


class TeacherApplicationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = TeacherApplicationSerializer

    def get_queryset(self):
        qs = TeacherApplication.objects.select_related('user').all()
        status_param = self.request.query_params.get('status')
        if status_param in ('pending','approved','rejected'):
            qs = qs.filter(status=status_param)
        return qs

class TeacherApplicationApproveView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        app = get_object_or_404(TeacherApplication, pk=pk)
        app.status = 'approved'
        app.save(update_fields=['status', 'updated_at'])
        # поднимаем флаг у пользователя
        u = app.user
        u.is_certified_teacher = True
        u.is_teacher = True
        u.save(update_fields=['is_certified_teacher', 'is_teacher'])
        return Response({'status': 'approved'}, status=200)

class TeacherApplicationRejectView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        reason = (request.data.get('reason') or '').strip()
        app = get_object_or_404(TeacherApplication, pk=pk)
        app.status = 'rejected'
        if reason:
            app.note = reason
        app.save(update_fields=['status', 'note', 'updated_at'])
        # на всякий случай уберём флаг подтверждения
        u = app.user
        u.is_certified_teacher = False
        u.save(update_fields=['is_certified_teacher'])
        return Response({'status': 'rejected'}, status=200)
