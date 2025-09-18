from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework import permissions, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import TeacherProfile
from .models import TeacherApplication
from .serializers import (
    TeacherProfileAdminSerializer,
    UserListSerializer,
    TeacherDetailSerializer,
    TeacherApplicationSerializer,
)

User = get_user_model()


# ===== Permissions =====

class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Дозволяє доступ адміну або вчителю (is_teacher=True).
    - Учителю: create/retrieve/list тільки своєї заявки; оновлення тільки у статусі 'pending'.
    - Адміну: повний доступ.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        # учителю дозволяємо базові дії в рамках його заявки
        if getattr(user, 'is_teacher', False):
            # для ViewSet дії задаються в view.action
            if getattr(view, 'action', None) in [None, 'list', 'retrieve', 'create', 'update', 'partial_update', 'destroy', 'me']:
                return True
            return True
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        # учитель має доступ тільки до своєї заявки
        if isinstance(obj, TeacherApplication):
            if view.action in ['retrieve', 'destroy', 'update', 'partial_update']:
                if obj.user_id != user.id:
                    return False
                # оновлювати/видаляти — тільки коли pending
                if view.action in ['update', 'partial_update', 'destroy']:
                    return obj.status == 'pending'
                return True
        return False


# ===== Admin helpers / dashboards =====

class AllUsersView(APIView):
    # Безпеково краще обмежити для адмінів
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        users = User.objects.all()
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)


class UnverifiedTeachersView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        profiles = TeacherProfile.objects.filter(user__is_teacher=True, user__is_certified_teacher=False)
        serializer = TeacherProfileAdminSerializer(profiles, many=True)
        return Response(serializer.data)


class VerifyTeacherView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, is_teacher=True)
            user.is_certified_teacher = True
            user.save(update_fields=['is_certified_teacher'])
            return Response({'message': 'Teacher verified successfully.'})
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class TeacherDetailView(APIView):
    # Якщо цю сторінку показуємо публічно — залишимо AllowAny
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, is_teacher=True)
            serializer = TeacherDetailSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)


# ===== Applications (admin list / approve / reject) =====

class TeacherApplicationListView(generics.ListAPIView):
    """
    Старий адмінський ендпойнт: список заявок з фільтром по статусу.
    Можна продовжити використовувати для адмін-панелі.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = TeacherApplicationSerializer

    def get_queryset(self):
        qs = TeacherApplication.objects.select_related('user').all()
        status_param = self.request.query_params.get('status')
        if status_param in ('pending', 'approved', 'rejected'):
            qs = qs.filter(status=status_param)
        return qs.order_by('-created_at')


class TeacherApplicationApproveView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        app = get_object_or_404(TeacherApplication, pk=pk)
        app.status = 'approved'
        app.save(update_fields=['status', 'updated_at'])
        # піднімаємо прапорець у користувача
        u = app.user
        u.is_certified_teacher = True
        u.is_teacher = True
        u.save(update_fields=['is_certified_teacher', 'is_teacher'])
        return Response({'status': 'approved'}, status=200)


class TeacherApplicationRejectView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        reason = (request.data.get('reason') or '').strip()
        app = get_object_or_404(TeacherApplication, pk=pk)
        app.status = 'rejected'
        if reason:
            app.note = reason
        app.save(update_fields=['status', 'note', 'updated_at'])
        # страховка: прибираємо прапорець підтвердження
        u = app.user
        u.is_certified_teacher = False
        u.save(update_fields=['is_certified_teacher'])
        return Response({'status': 'rejected'}, status=200)


# ===== New: ViewSet + /me/ for teachers =====

class TeacherApplicationViewSet(viewsets.ModelViewSet):
    """
    Повноцінний ViewSet для заявок.
    - Адмін: бачить усі, може змінювати статус/все інше.
    - Учитель: бачить ТІЛЬКИ свою, може створити одну (pending), оновлювати власні файли поки pending.
    """
    queryset = TeacherApplication.objects.select_related('user').all()
    serializer_class = TeacherApplicationSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset().order_by('-created_at')
        # учителю показуємо тільки його власні
        return TeacherApplication.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        # Фіксуємо власника та стартовий статус
        serializer.save(user=self.request.user, status='pending')

    def update(self, request, *args, **kwargs):
        """
        Учителю не дозволяємо міняти статус; адміну — можна.
        """
        if not request.user.is_staff and 'status' in request.data:
            data = request.data.copy()
            data.pop('status', None)
            request._full_data = data
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get', 'post', 'patch'], url_path='me')
    def me(self, request):
        """
        Зручний спец-роут:
        GET  /teacher-applications/me/    -> існує/дані
        POST /teacher-applications/me/    -> створити (якщо ще немає)
        PATCH/PUT /teacher-applications/me/ -> оновити свою pending-заявку (файли/note)
        """
        user = request.user
        if not (user.is_staff or getattr(user, 'is_teacher', False)):
            return Response({'detail': 'Not a teacher'}, status=status.HTTP_403_FORBIDDEN)

        app = TeacherApplication.objects.filter(user=user).first()

        if request.method == 'GET':
            if not app:
                return Response({'exists': False}, status=200)
            ser = self.get_serializer(app)
            return Response({'exists': True, 'data': ser.data}, status=200)

        if request.method == 'POST':
            if app:
                return Response({'detail': 'Заявка вже існує.'}, status=status.HTTP_400_BAD_REQUEST)
            ser = self.get_serializer(data=request.data, context={'request': request})
            ser.is_valid(raise_exception=True)
            ser.save(user=user, status='pending')
            return Response(ser.data, status=status.HTTP_201_CREATED)

        # PATCH / PUT
        if not app:
            return Response({'detail': 'Заявки ще немає.'}, status=status.HTTP_404_NOT_FOUND)
        if app.status != 'pending' and not user.is_staff:
            return Response({'detail': 'Заявку вже розглянуто.'}, status=status.HTTP_403_FORBIDDEN)

        partial = request.method.lower() == 'patch'
        ser = self.get_serializer(app, data=request.data, partial=partial, context={'request': request})
        ser.is_valid(raise_exception=True)
        # захист від зміни статусу
        ser.validated_data.pop('status', None)
        ser.save()
        return Response(ser.data, status=200)


class TeacherApplicationCreateView(generics.CreateAPIView):
    """
    Создать заявку на подтверждение квалификации.
    Доступно только авторизованному пользователю с is_teacher=True.
    """
    serializer_class = TeacherApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if not getattr(user, "is_teacher", False):
            raise PermissionError("Только учителя могут подавать заявки.")
        # Проверка на уникальность заявки
        if TeacherApplication.objects.filter(user=user).exists():
            raise ValueError("Заявка уже существует.")
        serializer.save(user=user, status="pending")
