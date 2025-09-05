# chat/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatViewSet, StartChatView, MessageViewSet, ReadMarkerView

router = DefaultRouter()
router.register(r'chats', ChatViewSet, basename='chat')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'read', ReadMarkerView, basename='readmarker')

urlpatterns = [
    path('start/', StartChatView.as_view(), name='chat-start'),
    path('', include(router.urls)),
]
