from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Avg
from .models import Review
from .serializers import (
    ReviewSerializer,
    ReviewCreateSerializer,
    ReviewModerationSerializer,
    MyReviewSerializer,
    ReviewAdminSerializer
)

class ReviewListAPIView(generics.ListAPIView):
    """
    Публічний список СХВАЛЕНИХ відгуків.
    GET /api/reviews/?course=<id>
    """
    serializer_class = ReviewSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Review.objects.filter(status=Review.Status.APPROVED)
        course_id = self.request.query_params.get('course')
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs


class ReviewCreateAPIView(generics.CreateAPIView):
    """
    Створення нового відгуку (авторизований).
    POST /api/reviews/create/
    """
    serializer_class = ReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({'request': self.request})
        return ctx


class MyReviewsAPIView(generics.ListAPIView):
    """
    Список власних відгуків з їхнім статусом.
    GET /api/reviews/mine/
    """
    serializer_class = MyReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user)


class ReviewModerationAPIView(generics.UpdateAPIView):
    """
    Адмін змінює статус (approve/reject/pending).
    PATCH /api/reviews/<id>/moderate/
    body: {"status": "approved", "moderation_reason": "..."}
    """
    queryset = Review.objects.all()
    serializer_class = ReviewModerationSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({'request': self.request})
        return ctx


class ReviewSummaryAPIView(APIView):
    """
    Зведення для курсу: середній рейтинг + кількість по оцінках 1..5.
    GET /api/reviews/summary/?course=<id>
    """
    def get(self, request):
        course_id = request.query_params.get('course')
        if not course_id:
            return Response({"detail": "Параметр 'course' обов'язковий"}, status=400)

        qs = Review.objects.filter(course_id=course_id, status=Review.Status.APPROVED)
        avg = qs.aggregate(avg=Avg('rating'))['avg'] or 0
        distribution = qs.values('rating').annotate(count=Count('id')).order_by('-rating')
        return Response({
            'average': round(avg, 2),
            'distribution': {d['rating']: d['count'] for d in distribution},
            'total': qs.count()
        })
    

class IsAdmin(permissions.IsAdminUser):
    pass

class ReviewAdminListAPIView(generics.ListAPIView):
    """
    Адмінський список усіх відгуків (з фільтрами).
    GET /api/reviews/admin/?status=pending|approved|rejected|all&course=<id>
    """
    serializer_class = ReviewAdminSerializer
    permission_classes = [IsAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Review.objects.all()
        status_q = (self.request.query_params.get("status") or "all").lower()
        if status_q in {"pending", "approved", "rejected"}:
            qs = qs.filter(status=status_q)
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

class ReviewPendingListAPIView(generics.ListAPIView):
    """
    Резервний ендпоінт: тільки pending.
    GET /api/reviews/pending/?course=<id>
    """
    serializer_class = ReviewAdminSerializer
    permission_classes = [IsAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering = ["created_at"]

    def get_queryset(self):
        qs = Review.objects.filter(status=Review.Status.PENDING)
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: Review):
        return request.user and (request.user.is_staff or obj.user_id == request.user.id)



class ReviewRetrieveDestroyAPIView(generics.RetrieveDestroyAPIView):
    """
    GET /api/reviews/<id>/   — (наразі не обов’язково на фронті)
    DELETE /api/reviews/<id>/ — видалення (лише адмін)
    """
    queryset = Review.objects.all()
    serializer_class = ReviewAdminSerializer
    permission_classes = [IsOwnerOrAdmin]


