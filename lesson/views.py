from typing import Any, Dict, List
from typing import Optional
from django.db.models import QuerySet
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models

from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import api_view

from course.models import Course
from .models import Module, Lesson, LessonContent, LessonProgress
from .serializers import (
    ModuleSerializer, ModuleReorderSerializer,
    LessonSerializer, LessonContentSerializer,
    LessonProgressSerializer
)
from .permissions import HasCourseAccess, IsCourseAuthorOrStaff

from .serializers import LessonListSerializer
from .pagination import TenByDefaultPagination
from .permissions import IsTeacherOrAdmin

from django.db.models import Exists, OuterRef, Subquery
from .serializers import LessonPublicListWithProgressSerializer


# ---------- Helpers ----------

SAFE_ORDERING = {'id', '-id', 'title', '-title', 'created_at', '-created_at', 'updated_at', '-updated_at'}

def _get_course_from_obj(obj) -> Course:
    if isinstance(obj, Module):
        return obj.course
    if isinstance(obj, Lesson):
        return obj.course
    return None


# ---------- Modules (teacher) ----------

class ModuleListCreateView(generics.ListCreateAPIView):
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_queryset(self):
        course_id = self.request.query_params.get('course')
        qs = Module.objects.select_related('course').all()
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def get_course(self, obj):
        return _get_course_from_obj(obj)


class ModuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Module.objects.select_related('course').all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)


class ModuleReorderView(APIView):
    """
    PATCH: { "items": [ {"id": <int>, "order": <int>}, ... ] }
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    @transaction.atomic
    def patch(self, request):
        ser = ModuleReorderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        items = ser.validated_data['items']
        ids = [i['id'] for i in items]
        modules = list(Module.objects.filter(id__in=ids).select_related('course'))
        # Перевіримо права по першому курсу
        if not modules:
            return Response(status=204)
        course = modules[0].course
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, modules[0]):
            return Response({"detail": "Немає прав."}, status=403)
        m_map = {m.id: m for m in modules}
        for it in items:
            m = m_map.get(it['id'])
            if m:
                m.order = it['order']
        Module.objects.bulk_update(modules, ['order'])
        return Response({"updated": len(modules)}, status=200)


# ---------- Lessons (teacher) ----------

class LessonListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_queryset(self):
        course_id = self.request.query_params.get('course')
        module_id = self.request.query_params.get('module')
        qs = Lesson.objects.select_related('course', 'module').prefetch_related('contents').all()
        if course_id:
            qs = qs.filter(course_id=course_id)
        if module_id:
            qs = qs.filter(module_id=module_id)
        return qs

    def get_course(self, obj):
        return _get_course_from_obj(obj)


class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.select_related('course', 'module').prefetch_related('contents').all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)


class LessonReorderView(APIView):
    """
    PATCH: { "items": [ {"id": <int>, "order": <int>}, ... ] }
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    @transaction.atomic
    def patch(self, request):
        items = request.data.get('items', [])
        if not items:
            return Response(status=204)
        lessons = list(Lesson.objects.filter(id__in=[i['id'] for i in items]).select_related('course'))
        if not lessons:
            return Response(status=204)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lessons[0]):
            return Response({"detail": "Немає прав."}, status=403)
        lmap = {l.id: l for l in lessons}
        for it in items:
            l = lmap.get(it['id'])
            if l:
                l.order = it['order']
        Lesson.objects.bulk_update(lessons, ['order'])
        return Response({"updated": len(lessons)}, status=200)


class LessonContentReorderView(APIView):
    """
    PATCH: { "items": [ {"id": <int>, "order": <int>}, ... ] }
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    @transaction.atomic
    def patch(self, request, lesson_id: int):
        items = request.data.get('items', [])
        if not items:
            return Response(status=204)
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail": "Немає прав."}, status=403)
        blocks = list(LessonContent.objects.filter(id__in=[i['id'] for i in items], lesson=lesson))
        bmap = {b.id: b for b in blocks}
        for it in items:
            b = bmap.get(it['id'])
            if b:
                b.order = it['order']
        LessonContent.objects.bulk_update(blocks, ['order'])
        return Response({"updated": len(blocks)}, status=200)


class LessonPublishView(APIView):
    """
    PATCH: {"status": "draft|scheduled|published|archived", "scheduled_at": "...", "published_at": "..."}
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def patch(self, request, pk: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=pk)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail": "Немає прав."}, status=403)

        status_val = request.data.get('status', lesson.status)
        scheduled_at = request.data.get('scheduled_at', None)
        published_at = request.data.get('published_at', None)

        lesson.status = status_val
        if scheduled_at is not None:
            lesson.scheduled_at = scheduled_at
        if published_at is not None:
            lesson.published_at = published_at
        if status_val == Lesson.Status.PUBLISHED and not lesson.published_at:
            lesson.published_at = timezone.now()
        lesson.save(update_fields=['status', 'scheduled_at', 'published_at', 'updated_at'])

        return Response(LessonSerializer(lesson).data, status=200)


# ---------- Lesson for student (public with access) ----------

class LessonPublicDetailView(APIView):
    """
    GET — повертає урок з блоками (без прихованих), якщо користувач має доступ і урок опублікований.
    """
    permission_classes = [IsAuthenticatedOrReadOnly, HasCourseAccess]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def get(self, request, id: int):
        lesson = get_object_or_404(
            Lesson.objects.select_related('course', 'module').prefetch_related('contents'),
            id=id,
            status=Lesson.Status.PUBLISHED
        )
        # Приховуємо приховані блоки
        data = LessonSerializer(lesson).data
        data['contents'] = [c for c in data.get('contents', []) if not c.get('is_hidden')]
        return Response(data, status=200)


# ---------- Progress ----------

class LessonProgressUpsertView(APIView):
    """
    POST /api/lesson/progress/<lesson_id>/
    body: {"state": "started|completed"}
    """
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def post(self, request, lesson_id: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        state = request.data.get('state')
        if state not in (LessonProgress.State.STARTED, LessonProgress.State.COMPLETED):
            return Response({"detail": "Невірний state."}, status=400)

        lp, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        lp.state = state
        now = timezone.now()
        if state == LessonProgress.State.STARTED and not lp.started_at:
            lp.started_at = now
        if state == LessonProgress.State.COMPLETED:
            lp.completed_at = now
        lp.save()
        return Response(LessonProgressSerializer(lp).data, status=200)



from rest_framework.views import APIView
from rest_framework import status, parsers
from rest_framework.response import Response
from .models import Lesson, LessonContent, Module
from .permissions import IsCourseAuthorOrStaff

class SimpleLessonCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]
    parser_classes = [parsers.JSONParser, parsers.FormParser, parsers.MultiPartParser]

    def post(self, request):
        data = request.data
        # required
        course_id = data.get('course')
        title = data.get('title', '').strip()
        order = data.get('order') or 0
        ltype = (data.get('type') or '').upper()
        status_value = data.get('status', 'draft').lower()

        if not course_id or not title or ltype not in ('VIDEO','TEXT','LINK'):
            return Response({'detail': 'Invalid payload. Required: course, title, type [VIDEO|TEXT|LINK].'}, status=400)

        # create lesson
        from django.utils.text import slugify
        base_slug = slugify(title)[:180] or 'lesson'
        slug = base_slug
        i = 2
        while Lesson.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{i}"
            i += 1

        lesson = Lesson.objects.create(
            course_id=course_id,
            module=None,
            title=title,
            slug=slug,
            summary=data.get('content_text','')[:300],
            order=order,
            status=status_value,
            duration_min=data.get('duration_min') or None,
        )

        # map content
        if ltype == 'TEXT':
            LessonContent.objects.create(lesson=lesson, type='text', data={'text': data.get('content_text','')})
        elif ltype == 'VIDEO':
            LessonContent.objects.create(lesson=lesson, type='video', data={'url': data.get('content_url','')})
        elif ltype == 'LINK':
            LessonContent.objects.create(lesson=lesson, type='link', data={'url': data.get('content_url','')})

        return Response({'id': lesson.id, 'slug': lesson.slug, 'title': lesson.title}, status=201)


class MyLessonsListView(generics.ListAPIView):
    serializer_class = LessonListSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]
    pagination_class = TenByDefaultPagination

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        qs = Lesson.objects.all()

        # Фильтр "мои": либо Lesson.author, либо Course.author
        if hasattr(Lesson, 'author'):
            qs = qs.filter(author=user)
        else:
            try:
                qs = qs.filter(course__author=user)
            except Exception:
                qs = qs.none()

        # Поиск
        search = self.request.query_params.get('search') or ''
        if search:
            # если есть описание — фильтруем и по нему
            if 'description' in [f.name for f in Lesson._meta.get_fields() if hasattr(f, 'name')]:
                qs = qs.filter(title__icontains=search) | qs.filter(description__icontains=search)
            else:
                qs = qs.filter(title__icontains=search)

        # Статус
        status_param: Optional[str] = self.request.query_params.get('status')
        if status_param in ('published', 'draft') and hasattr(Lesson, 'is_published'):
            qs = qs.filter(is_published=(status_param == 'published'))

        # Безопасная сортировка
        ordering = self.request.query_params.get('ordering') or '-id'
        if ordering not in SAFE_ORDERING:
            ordering = '-id'
        try:
            qs = qs.order_by(ordering)
        except Exception:
            qs = qs.order_by('-id')

        return qs.select_related('course')
    


class LessonTheoryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        theories = lesson.contents.filter(type='text')
        data = [{"id": t.id, "theory_text": t.data.get('text', '')} for t in theories]
        return Response(data)

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        text = request.data.get("theory_text", "")
        if not text:
            return Response({"detail": "Empty theory"}, status=400)
        theory = LessonContent.objects.create(
            lesson=lesson, type="text", data={"text": text}
        )
        return Response({"id": theory.id, "theory_text": text}, status=201)

    def put(self, request, lesson_id, theory_id):
        theory = get_object_or_404(LessonContent, pk=theory_id, lesson_id=lesson_id)
        theory_text = request.data.get("theory_text", "")
        theory.data["text"] = theory_text
        theory.save(update_fields=["data"])
        return Response({"id": theory.id, "theory_text": theory_text})
    

from django.db.models import Q
from rest_framework.permissions import AllowAny

class LessonsByCourseView(ListAPIView):
    """
    Повертає список уроків по курсу, тільки опубліковані.
    Для авторизованого користувача додає completed/result_percent з LessonProgress.
    Доступ без авторизації (анонім побачить completed=False, result_percent=null).
    """
    serializer_class = LessonPublicListWithProgressSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        course_id = self.kwargs["course_id"]

        qs = Lesson.objects.filter(
            status=Lesson.Status.PUBLISHED
        ).filter(
            Q(module__course_id=course_id) | Q(module__isnull=True, course_id=course_id)
        ).order_by('order', 'id')

        # 👉 аннотируем прогрессом текущего пользователя
        return annotate_with_user_progress(qs, self.request.user)


class LessonProgressUpsertView(APIView):
    """
    POST /api/lesson/progress/<lesson_id>/
    body: {"state": "started|completed", "result_percent": 0..100?}
    """
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def post(self, request, lesson_id: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        state = request.data.get('state')
        if state not in (LessonProgress.State.STARTED, LessonProgress.State.COMPLETED):
            return Response({"detail": "Невірний state."}, status=400)

        # безопасно вытягиваем процент
        result_percent = request.data.get('result_percent', None)
        if result_percent is not None:
            try:
                result_percent = int(result_percent)
                if result_percent < 0 or result_percent > 100:
                    raise ValueError
            except Exception:
                return Response({"detail": "result_percent має бути integer 0..100."}, status=400)

        lp, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        lp.state = state
        now = timezone.now()
        if state == LessonProgress.State.STARTED and not lp.started_at:
            lp.started_at = now
        if state == LessonProgress.State.COMPLETED:
            lp.completed_at = now
        if result_percent is not None:
            lp.result_percent = result_percent
        lp.save()

        return Response(LessonProgressSerializer(lp).data, status=200)
    
    
class LessonPublicDetailViewById(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get(self, request, lesson_id: int):
        lesson = get_object_or_404(
            Lesson.objects.select_related('course', 'module').prefetch_related('contents'),
            pk=lesson_id,
            status=Lesson.Status.PUBLISHED
        )
        # Приховуємо приховані блоки
        data = LessonSerializer(lesson).data
        data['contents'] = [c for c in data.get('contents', []) if not c.get('is_hidden')]
        return Response(data, status=200)
    
@api_view(['GET'])
def lesson_theory(request, lesson_id):
    try:
        lesson = Lesson.objects.get(pk=lesson_id)

        # Вибираємо всі блоки контенту уроку
        theory_content = []
        for c in lesson.contents.all():
            if not c.is_hidden and c.type in ['text', 'html']:
                # Беремо текст з data
                text = c.data.get('text', '')
                if text:
                    theory_content.append(text)

        # Якщо блоків немає, можна повернути повідомлення
        if not theory_content:
            theory_content = ["Теорія поки що відсутня."]

        return Response({
            'id': lesson.id,
            'title': lesson.title,
            'duration_min': lesson.duration_min,
            'theory': theory_content
        })

    except Lesson.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


def annotate_with_user_progress(qs, user):
    """
    Добавляет к queryset'у полям:
      - completed: bool (есть LessonProgress со state=COMPLETED для user+lesson)
      - result_percent: последний result_percent пользователя для урока
    """
    if not user or not user.is_authenticated:
        # для анонима: флаг False и пустой процент
        return qs.annotate(
            completed=models.Value(False, output_field=models.BooleanField()),
            result_percent=Subquery(LessonProgress.objects.none().values('result_percent')[:1]),
        )

    user_progress = LessonProgress.objects.filter(user=user, lesson=OuterRef('pk'))

    return qs.annotate(
        completed=Exists(user_progress.filter(state=LessonProgress.State.COMPLETED)),
        result_percent=Subquery(user_progress.order_by('-updated_at').values('result_percent')[:1]),
    )