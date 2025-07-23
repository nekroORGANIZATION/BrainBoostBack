from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Course, Comment
from .serializers import CourseSerializer, CommentSerializer

class CourseListCreateView(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.username)


class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]


class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        return Comment.objects.filter(course_id=course_id).order_by('-created_at')

    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_pk')
        course = get_object_or_404(Course, pk=course_id)
        serializer.save(course=course, author=self.request.user)


class CommentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        return Comment.objects.filter(course_id=course_id)
    
    def perform_update(self, serializer):
        serializer.save(author=self.request.user)



class CourseUpdateView(generics.UpdateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        course = self.get_object()
        user = self.request.user
        if user.username != course.author and not user.is_staff:
            raise PermissionDenied("У Вас немає доступа до редагування курсу.")
        serializer.save()


class CourseDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        user = request.user
        if user.username != course.author and not user.is_staff:
            raise PermissionDenied("Нет прав на удаление курса.")
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
