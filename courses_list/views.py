from rest_framework import generics, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from course.models import Course, Category
from .serializers import CourseSerializer, UserSerializer, CategorySerializer


class CourseListAPIView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter] 
    filterset_fields = {
        'category__name': ['exact'],
        'price': ['lte', 'gte'],
        'rating': ['gte'],
        'language': ['exact'],
        'topic': ['icontains'],
    }
    search_fields = ['title']
    ordering_fields = ['price', 'rating', 'title']
    ordering = ['id']
    permission_classes = [permissions.AllowAny]


    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({'request': self.request})
        return ctx


class CourseDetailAPIView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_field = 'pk'
    lookup_url_kwarg = 'course_id'
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({'request': self.request})
        return ctx


class CourseUpdateAPIView(generics.UpdateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_field = 'pk'
    lookup_url_kwarg = 'course_id'
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        course = self.get_object()
        user = self.request.user
        if not (user == course.author or user.is_staff or user.is_superuser):
            raise PermissionDenied("Ви не маєте прав редагувати цей курс.")
        serializer.save()


class CourseDeleteAPIView(generics.DestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_field = 'pk'
    lookup_url_kwarg = 'course_id'
    permission_classes = [permissions.IsAdminUser]

    def perform_destroy(self, instance):
        instance.delete()


class UserMeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
