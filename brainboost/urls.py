"""
URL configuration for brainboost project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('courses/', include('course.urls')),
    #path('api/courses/', include('course.urls')),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('courses/all/', include('courses_list.urls')),
    path('api/lesson/', include('lesson.urls')),
    path('lesson/', include('lesson.urls')),
    path('api/ai/', include('ai.urls')),
    path('api/payments/', include('payments.urls')),
    path('admin_panel/api/', include('admin_panel.urls')),
    path('api/tests/', include('tests.urls')),

    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/social/', include('allauth.socialaccount.urls')),
    path('api/contacts/', include('contacts.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('api/', include('stories.urls')),

    path("api/tips/", include("tips.urls")),

    path('api/chat/', include('chat.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
