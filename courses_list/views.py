from django.db.models import Count, Avg
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from course.models import Course
from .serializers import PublicCourseCardSerializer


class PublicCourseListAPIView(generics.ListAPIView):
    """
    Публічний каталог курсів з фільтрами/сортуванням/пошуком.
    Видає лише опубліковані курси.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PublicCourseCardSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        "category": ["exact"],
        "price": ["lte", "gte"],
        "rating": ["gte"],
        "language": ["exact"],
        "topic": ["icontains"],
    }
    search_fields = ["title", "description", "topic"]
    ordering_fields = ["price", "rating", "title", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # select_related для продуктивності
        qs = Course.objects.select_related("category", "author").filter(status=Course.Status.PUBLISHED)
        return qs


class PublicCourseDetailAPIView(generics.RetrieveAPIView):
    """
    Публічна детальна сторінка по slug.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PublicCourseCardSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Course.objects.select_related("category", "author").filter(status=Course.Status.PUBLISHED)
