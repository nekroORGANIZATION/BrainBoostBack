from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, LogoutView, UserProfileView

from .views import TeacherRegisterView


urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/profile/', UserProfileView.as_view(), name='user-profile'),

    path('register-teacher/', TeacherRegisterView.as_view(), name='register-teacher'),

    path('logout/', LogoutView.as_view(), name='logout'),
    #path('profile/', ProfileView.as_view(), name='profile'),
]
