from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg
from rest_framework import generics, permissions, status, filters, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny

from .models import Course, Category, PurchasedCourse, Comment
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, CourseCreateUpdateSerializer,
    CategorySerializer, PurchasedCourseSerializer, CommentSerializer
)
from .permissions import IsCourseAuthorOrStaff


# -------- Категорії (публічні) --------

class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all().annotate(courses_count=Count("courses"))
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


# -------- Курси: CRUD для автора/стадда --------

class CourseListCreateAPIView(generics.ListCreateAPIView):
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    queryset = Course.objects.select_related("category", "author").all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        "category": ["exact"],
        "price": ["lte", "gte"],
        "rating": ["gte"],
        "language": ["exact"],
        "topic": ["icontains"],
        "status": ["exact"],
    }
    search_fields = ["title", "description", "topic"]
    ordering_fields = ["price", "rating", "title", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CourseCreateUpdateSerializer
        return CourseListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx

    def perform_create(self, serializer):
        serializer.save()  # author виставляється в serializer.create


class CourseDetailAPIView(generics.RetrieveAPIView):
    queryset = Course.objects.select_related("category", "author").all()
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx


class CourseUpdateAPIView(generics.UpdateAPIView):
    queryset = Course.objects.select_related("category", "author").all()
    serializer_class = CourseCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]
    lookup_field = "slug"


from rest_framework import parsers

class CourseRetrieveUpdateByIDAPIView(generics.RetrieveUpdateAPIView):
    queryset = Course.objects.select_related("category", "author").all()
    # чтение при GET нам не критично — фронт этим эндпоинтом пользуется для PATCH
    serializer_class = CourseCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]
    lookup_field = "pk"
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]



class CourseDeleteAPIView(generics.DestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]
    lookup_field = "slug"


# -------- Покупки / Доступ --------

class UserPurchasedCoursesView(generics.ListAPIView):
    serializer_class = PurchasedCourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PurchasedCourse.objects.filter(user=self.request.user, is_active=True).select_related("course")


class EnrollCourseView(APIView):
    """
    Спрощена "покупка"/запис на курс (dev-режим).
    У проді це має робити платіжний вебхук.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug: str):
        course = get_object_or_404(Course, slug=slug, status=Course.Status.PUBLISHED)
        obj, created = PurchasedCourse.objects.get_or_create(user=request.user, course=course, defaults={"is_active": True})
        if not created and not obj.is_active:
            obj.is_active = True
            obj.save(update_fields=["is_active"])
        return Response(PurchasedCourseSerializer(obj).data, status=201 if created else 200)


# -------- Коментарі --------

class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        course = get_object_or_404(Course, slug=slug)
        return Comment.objects.filter(course=course).select_related("author")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx

    def perform_create(self, serializer):
        slug = self.kwargs.get("slug")
        course = get_object_or_404(Course, slug=slug)
        serializer.save(course=course)


class CommentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        course = get_object_or_404(Course, slug=slug)
        return Comment.objects.filter(course=course).select_related("author")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx
