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
    