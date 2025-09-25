# apps/course/views.py

from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status, filters, parsers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Course, Category, PurchasedCourse, Comment, Wishlist, Language
)
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, CourseCreateUpdateSerializer,
    CategorySerializer, PurchasedCourseSerializer, CommentSerializer,
    WishlistSerializer, LanguageSerializer, CategoryAdminSerializer,
    CommentListSerializer,
)
from .permissions import IsCourseAuthorOrStaff, IsAuthorOrAdmin


# =========================
#   CATEGORIES / LANGUAGES
# =========================

class CategoryListAPIView(generics.ListAPIView):
    """
    GET /courses/categories/
    """
    queryset = Category.objects.all().annotate(courses_count=Count("courses"))
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]


class LanguageListAPIView(generics.ListAPIView):
    """
    GET /courses/languages/
    """
    queryset = Language.objects.all().order_by("name")
    serializer_class = LanguageSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]


# ------- ADMIN: categories -------
class CategoryAdminListCreateAPIView(generics.ListCreateAPIView):
    """
    GET/POST /courses/admin/categories/
    """
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategoryAdminSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]


class CategoryAdminDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /courses/admin/categories/<id>/
    """
    queryset = Category.objects.all()
    serializer_class = CategoryAdminSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"


# ------- ADMIN: languages -------
class LanguageAdminListCreateAPIView(generics.ListCreateAPIView):
    """
    GET/POST /courses/admin/languages/
    """
    queryset = Language.objects.all().order_by("name")
    serializer_class = LanguageSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]


class LanguageAdminDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /courses/admin/languages/<id>/
    """
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"


# ==========
#   WISHLIST
# ==========

class WishlistListCreateView(generics.ListCreateAPIView):
    """
    GET/POST /courses/wishlist/    (або /courses/me/wishlist/)
    """
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
            # якщо вже є — мовчки ігноруємо
            pass


class WishlistDeleteView(APIView):
    """
    DELETE /courses/wishlist/<course_id>/  або  /courses/me/wishlist/<course_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, course_id: int):
        Wishlist.objects.filter(user=request.user, course_id=course_id).delete()
        return Response({"ok": True}, status=status.HTTP_200_OK)


class WishlistToggleView(APIView):
    """
    POST /courses/wishlist/toggle/ { "course": <id> }
    """
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


# =========
#   COURSES
# =========

class CourseListCreateAPIView(generics.ListCreateAPIView):
    """
    GET /courses/?author=me|<id>&page_size=...
    POST /courses/
    """
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    queryset = Course.objects.select_related("category", "author").all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        "category": ["exact", "in"],
        "language": ["exact", "in"],
        "price": ["lte", "gte"],
        "rating": ["gte"],
        "topic": ["icontains"],
        "status": ["exact"],
    }
    search_fields = ["title", "description", "topic"]
    ordering_fields = ["price", "rating", "title", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        author_q = self.request.query_params.get("author")
        if author_q:
            if author_q == "me" and self.request.user.is_authenticated:
                qs = qs.filter(author=self.request.user)
            else:
                try:
                    qs = qs.filter(author_id=int(author_q))
                except (TypeError, ValueError):
                    pass
        return qs

    def get_serializer_class(self):
        return CourseCreateUpdateSerializer if self.request.method == "POST" else CourseListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx

    def perform_create(self, serializer):
        # автор — поточний користувач
        serializer.save()


class MyCoursesListAPIView(generics.ListAPIView):
    """
    GET /courses/my/  (дзеркало можна підвісити і на /api/courses/my/)
    """
    serializer_class = CourseListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Course.objects
            .select_related("category", "author")
            .filter(author=self.request.user)
            .order_by("-created_at", "-id")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx


class CourseDetailAPIView(generics.RetrieveAPIView):
    """
    GET /courses/<slug:slug>/   (деталі по slug — публічні)
    """
    queryset = Course.objects.select_related("category", "author").all()
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx


class CourseUpdateAPIView(generics.UpdateAPIView):
    """
    PATCH/PUT /courses/<slug:slug>/  (оновлення по slug, лише автор/стад)
    """
    queryset = Course.objects.select_related("category", "author").all()
    serializer_class = CourseCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]
    lookup_field = "slug"


class CourseRetrieveUpdateDestroyByIDAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /courses/<int:pk>/      — публічний перегляд по ID
    PATCH  /courses/<int:pk>/      — оновлення (автор/стад)
    DELETE /courses/<int:pk>/      — видалення (автор/стад)
    """
    queryset = Course.objects.select_related("category", "author").all()
    lookup_field = "pk"
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_permissions(self):
        if self.request.method in ("GET",):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsCourseAuthorOrStaff()]

    def get_serializer_class(self):
        return CourseDetailSerializer if self.request.method == "GET" else CourseCreateUpdateSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx


# ======================
#   PURCHASES / ACCESS
# ======================

class UserPurchasedCoursesView(generics.ListAPIView):
    """
    GET /courses/me/purchased/
    """
    serializer_class = PurchasedCourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            PurchasedCourse.objects
            .filter(user=self.request.user, is_active=True)
            .select_related("course")
            .order_by("-purchased_at", "-id")
        )


class EnrollCourseView(APIView):
    """
    POST /courses/<int:pk>/enroll/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        course = get_object_or_404(Course, pk=pk, status=Course.Status.PUBLISHED)
        obj, created = PurchasedCourse.objects.get_or_create(
            user=request.user, course=course, defaults={"is_active": True}
        )
        if not created and not obj.is_active:
            obj.is_active = True
            obj.save(update_fields=["is_active"])
        ser = PurchasedCourseSerializer(obj, context={"request": request})
        return Response(ser.data, status=201 if created else 200)


# ==========
#  COMMENTS
# ==========

class CommentListCreateView(generics.ListCreateAPIView):
    """
    GET/POST /courses/<slug:slug>/comments/
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        course = get_object_or_404(Course, slug=slug)
        # список — легший серіалізатор
        return Comment.objects.filter(course=course).select_related("author").order_by("created_at", "id")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx

    def perform_create(self, serializer):
        slug = self.kwargs.get("slug")
        course = get_object_or_404(Course, slug=slug)
        serializer.save(course=course)


class CommentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /courses/<slug:slug>/comments/<int:pk>/
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrAdmin]

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        course = get_object_or_404(Course, slug=slug)
        return Comment.objects.filter(course=course).select_related("author")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx
