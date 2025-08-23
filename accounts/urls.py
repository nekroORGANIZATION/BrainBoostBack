from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, LogoutView, UserProfileView, ResetPasswordView, GoogleLoginView

from .views import TeacherRegisterView


urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/profile/', UserProfileView.as_view(), name='user-profile'),

    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    path('api/google-login/', GoogleLoginView.as_view(), name='google-login'),

    path('logout/', LogoutView.as_view(), name='logout'),
]
