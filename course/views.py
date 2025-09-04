from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg
from rest_framework import generics, permissions, status, filters, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from django.db import IntegrityError

from .models import Course, Category, PurchasedCourse, Comment, Wishlist, Language
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, CourseCreateUpdateSerializer,
    CategorySerializer, PurchasedCourseSerializer, CommentSerializer, WishlistSerializer, 
    LanguageSerializer, CategoryAdminSerializer
)
from .permissions import IsCourseAuthorOrStaff


####    =======================================================================

class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all().annotate(courses_count=Count("courses"))
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]

# --- ПУБЛИЧНЫЙ список языков (только GET) ---
class LanguageListAPIView(generics.ListAPIView):
    queryset = Language.objects.all().order_by("name")
    serializer_class = LanguageSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]

# --- АДМИН: категории CRUD ---
class CategoryAdminListCreateAPIView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategoryAdminSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]

class CategoryAdminDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryAdminSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"

# --- АДМИН: языки CRUD ---
class LanguageAdminListCreateAPIView(generics.ListCreateAPIView):
    queryset = Language.objects.all().order_by("name")
    serializer_class = LanguageSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]

class LanguageAdminDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"

####    =======================================================================





class WishlistListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WishlistSerializer

    def get_queryset(self):
        return (
            Wishlist.objects
            .filter(user=self.request.user)
            .filter(course__isnull=False)
            .select_related("course")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            pass

class WishlistDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, course_id: int):
        Wishlist.objects.filter(user=request.user, course_id=course_id).delete()
        return Response({"ok": True}, status=status.HTTP_200_OK)


class WishlistToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        course_id = request.data.get("course") or request.data.get("course_id")
        if not course_id:
            return Response({"detail": "course is required"}, status=400)
        try:
            Course.objects.only("id").get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Курс не знайдено."}, status=404)

        obj, created = Wishlist.objects.get_or_create(user=request.user, course_id=course_id)
        if not created:
            obj.delete()
            return Response({"in_wishlist": False}, status=200)
        return Response({"in_wishlist": True}, status=200)





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
    lookup_field = "pk"
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CourseDetailSerializer  # детальний серіалізатор для перегляду
        return CourseCreateUpdateSerializer  # для оновлення


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
