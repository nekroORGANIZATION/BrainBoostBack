from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.hashers import make_password
from .serializers import UserProfileSerializer
from rest_framework import parsers

from django.conf import settings
import random
import string
from django.core.mail import send_mail
from .models import CustomUser
from rest_framework import permissions


from .serializers import TeacherRegisterSerializer, RegisterSerializer

from rest_framework_simplejwt.tokens import RefreshToken

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.apps import apps

from course.models import Course
from lesson.models import Lesson, LessonProgress
from accounts.models import Certificate
from accounts.services.certificates import issue_or_resend_certificate


# ---------- Helpers ----------

def _get_coursesdone_model():
    """
    Пытаемся найти модель в app `course`:
    - CoursesDone
    - CourseDone
    - PurchasedCourse (fallback)
    """
    for name in ("CoursesDone", "CourseDone", "PurchasedCourse"):
        try:
            return apps.get_model("course", name)
        except Exception:
            continue
    return None


def _coursesdone_completed_filter():
    return Q(completed_at__isnull=False)


def _coursesdone_user_filter(user):
    uid = getattr(user, "id", None)
    return Q(user=user) | Q(user_id=uid)


def _coursesdone_course_filter(course):
    cid = getattr(course, "id", None)
    return Q(course=course) | Q(course_id=cid)


def _extract_score(obj):
    """
    Достаём итоговый балл/процент из наиболее вероятных полей.
    Возвращаем int или None.
    """
    for field in ("final_score", "score", "result_percent", "grade"):
        if hasattr(obj, field):
            val = getattr(obj, field)
            if val is None:
                return None
            try:
                return int(val)
            except Exception:
                try:
                    return round(float(val))
                except Exception:
                    return None
    return None


def _is_course_completed_for_user(user, course) -> bool:
    """
    1) Основной источник — таблица CoursesDone (app course).
    2) Фолбек — все опубликованные уроки завершены (LessonProgress).
    """
    CD = _get_coursesdone_model()
    if CD is not None:
        q = CD.objects.filter(_coursesdone_user_filter(user) & _coursesdone_course_filter(course))
        q = q.filter(_coursesdone_completed_filter())
        if q.exists():
            return True

    # --- fallback через LessonProgress ---
    lessons_qs = Lesson.objects.filter(
        status=Lesson.Status.PUBLISHED
    ).filter(
        Q(module__course_id=course.id) | Q(module__isnull=True, course_id=course.id)
    )
    total = lessons_qs.count()
    if total == 0:
        return False
    done = LessonProgress.objects.filter(
        user=user, lesson__in=lessons_qs, state=LessonProgress.State.COMPLETED
    ).count()
    return done == total


def _get_completed_courses_for_user(user):
    """
    Возвращает список словарей {course: Course, score: int|None}
    из CoursesDone. Если таблицы нет — пусто.
    """
    CD = _get_coursesdone_model()
    if CD is None:
        return []

    rows = CD.objects.filter(_coursesdone_user_filter(user)).filter(_coursesdone_completed_filter())
    out = []
    for row in rows.select_related("course"):
        course = getattr(row, "course", None)
        if course is None:
            cid = getattr(row, "course_id", None)
            if cid:
                try:
                    course = Course.objects.get(pk=cid)
                except Course.DoesNotExist:
                    course = None
        if course is None:
            continue
        out.append({"course": course, "score": _extract_score(row)})
    return out


# ---------- Views ----------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_completed_courses(request):
    """
    Возвращает завершённые курсы для текущего пользователя на основе CoursesDone,
    плюс признак и серийник сертификата, если он уже создан.
    """
    items = []
    completed = _get_completed_courses_for_user(request.user)

    # Если CoursesDone отсутствует — можно опционально сделать fallback по LessonProgress,
    # но чтобы не нагружать, оставим пусто, когда таблицы нет.
    for row in completed:
        course = row["course"]
        cert = Certificate.objects.filter(user=request.user, course=course, is_revoked=False).first()
        items.append({
            "id": course.id,
            "title": getattr(course, 'title', str(course)),
            "certificate_exists": bool(cert and cert.pdf),
            "certificate_serial": cert.serial if cert else None,
        })
    return Response({"results": items}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def issue_certificate_for_course(request, course_id: int):
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return Response({"detail": "Курс не знайдено."}, status=404)

    # Проверяем завершённость и вытягиваем возможный финальный балл
    completed_rows = _get_completed_courses_for_user(request.user)
    row = next((r for r in completed_rows if getattr(r["course"], "id", None) == course.id), None)

    if row is None:
        # На всякий случай доп.проверка через _is_course_completed_for_user (fallback)
        if not _is_course_completed_for_user(request.user, course):
            return Response({"detail": "Курс ще не завершено."}, status=400)

    final_score = None if row is None else row.get("score")

    cert = issue_or_resend_certificate(request.user, course)
    return Response({
        "ok": True,
        "serial": cert.serial,
        "exists": bool(cert.pdf),
    }, status=200)




class GoogleLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({'error': 'Email не передан.'}, status=status.HTTP_400_BAD_REQUEST)

        user, created = CustomUser.objects.get_or_create(email=email, defaults={
            'username': email.split('@')[0],
            'is_active': True,
        })

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "Користувача з такою поштою не існує."}, status=status.HTTP_404_NOT_FOUND)

        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        user.set_password(new_password)
        user.save()

        send_mail(
            subject='Скидання пароля | BrainBoost',
            message=(
                f"Вітаємо!\n\n"
                f"Ми отримали запит на скидання пароля для вашого акаунта BrainBoost.\n"
                f"Не хвилюйтеся — з ким не буває 🙂\n\n"
                f"Ваш новий тимчасовий пароль: {new_password}\n\n"
                f"Радимо змінити цей пароль одразу після входу в систему для забезпечення безпеки.\n\n"
                f"З повагою,\n"
                f"Команда BrainBoost 🧠"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"message": "Новий пароль надіслано на пошту."}, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]  # <-- добавлено

    def post(self, request):
        role = request.data.get('role')

        if role == 'teacher':
            serializer = TeacherRegisterSerializer(data=request.data)
        else:
            serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"message": "Logged out successfully."})


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TeacherRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TeacherRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Teacher registered. Awaiting verification.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    