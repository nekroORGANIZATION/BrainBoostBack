# lesson/views.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from django.db import transaction, models
from django.db.models import Exists, OuterRef, Subquery, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify

from rest_framework import generics, permissions, parsers, status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.decorators import api_view

from course.models import Course
from .models import Module, Lesson, LessonContent, LessonProgress
from .serializers import (
    ModuleSerializer, ModuleReorderSerializer,
    LessonSerializer, LessonBlockSerializer,
    LessonProgressSerializer, LessonPublicListWithProgressSerializer,
    LessonListSerializer
)
from .pagination import TenByDefaultPagination
from .permissions import HasCourseAccess, IsCourseAuthorOrStaff, IsTeacherOrAdmin


# -------- helper for object-level permission --------
def _get_course_from_obj(obj) -> Optional[Course]:
    if isinstance(obj, Module):
        return obj.course
    if isinstance(obj, Lesson):
        return obj.course
    if isinstance(obj, LessonContent):
        return obj.lesson.course
    return None


# ============================ MODULES (teacher) ============================
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
        if not modules:
            return Response(status=204)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, modules[0]):
            return Response({"detail":"Немає прав."}, status=403)
        m_map = {m.id: m for m in modules}
        for it in items:
            m = m_map.get(it['id'])
            if m:
                m.order = it['order']
        Module.objects.bulk_update(modules, ['order'])
        return Response({"updated": len(modules)}, status=200)


# ============================ LESSONS (teacher) ============================
class LessonListCreateView(generics.ListCreateAPIView):
    """
    GET:   ?course=&module=&ordering=
    POST:  створення уроку (як з contents[], так і у старому форматі type/content_*)
    """
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]
    parser_classes = [parsers.JSONParser, parsers.FormParser, parsers.MultiPartParser]

    def get_queryset(self):
        course_id = self.request.query_params.get('course')
        module_id = self.request.query_params.get('module')
        ordering = self.request.query_params.get('ordering') or 'order,id'
        qs = Lesson.objects.select_related('course', 'module').prefetch_related('contents').all()
        if course_id:
            qs = qs.filter(course_id=course_id)
        if module_id:
            qs = qs.filter(module_id=module_id)
        try:
            qs = qs.order_by(*[o.strip() for o in ordering.split(',') if o.strip()])
        except Exception:
            qs = qs.order_by('order', 'id')
        return qs

    def get_course(self, obj):
        return _get_course_from_obj(obj)


class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /admin/lessons/<pk>/
    PATCH приймає як плоскі поля (title, summary, ...) так і contents[] для повної заміни блоків.
    """
    queryset = Lesson.objects.select_related('course', 'module').prefetch_related('contents').all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]
    parser_classes = [parsers.JSONParser, parsers.FormParser, parsers.MultiPartParser]

    def get_course(self, obj):
        return _get_course_from_obj(obj)


class LessonReorderView(APIView):
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
            return Response({"detail":"Немає прав."}, status=403)
        lmap = {l.id: l for l in lessons}
        for it in items:
            l = lmap.get(it['id'])
            if l:
                l.order = it['order']
        Lesson.objects.bulk_update(lessons, ['order'])
        return Response({"updated": len(lessons)}, status=200)


# ----- BLOCKS (зручно для редактора) -----
class LessonBlockListCreateView(APIView):
    """
    GET  /admin/lessons/<lesson_id>/blocks/
    POST /admin/lessons/<lesson_id>/blocks/
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def get(self, request, lesson_id: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail":"Немає прав."}, status=403)
        blocks = lesson.contents.all()
        return Response(LessonBlockSerializer(blocks, many=True).data)

    @transaction.atomic
    def post(self, request, lesson_id: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail":"Немає прав."}, status=403)
        ser = LessonBlockSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        block = LessonContent.objects.create(lesson=lesson, **ser.validated_data)
        return Response(LessonBlockSerializer(block).data, status=201)


class LessonBlockDetailView(APIView):
    """
    PUT/PATCH/DELETE /admin/lessons/<lesson_id>/blocks/<block_id>/
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def put(self, request, lesson_id: int, block_id: int):
        return self._update(request, lesson_id, block_id, partial=False)

    def patch(self, request, lesson_id: int, block_id: int):
        return self._update(request, lesson_id, block_id, partial=True)

    @transaction.atomic
    def _update(self, request, lesson_id: int, block_id: int, partial: bool):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail":"Немає прав."}, status=403)
        block = get_object_or_404(LessonContent, pk=block_id, lesson=lesson)
        ser = LessonBlockSerializer(block, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    @transaction.atomic
    def delete(self, request, lesson_id: int, block_id: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail":"Немає прав."}, status=403)
        block = get_object_or_404(LessonContent, pk=block_id, lesson=lesson)
        block.delete()
        return Response(status=204)


class LessonBlockReorderView(APIView):
    """
    PATCH /admin/lessons/<lesson_id>/blocks/reorder/
    body: { "items": [ {"id":<int>, "order":<int>}, ... ] }
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    @transaction.atomic
    def patch(self, request, lesson_id: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail":"Немає прав."}, status=403)
        items = request.data.get('items', [])
        if not items:
            return Response(status=204)
        blocks = list(LessonContent.objects.filter(id__in=[i['id'] for i in items], lesson=lesson))
        bmap = {b.id: b for b in blocks}
        for it in items:
            b = bmap.get(it['id'])
            if b:
                b.order = it['order']
        LessonContent.objects.bulk_update(blocks, ['order'])
        return Response({"updated": len(blocks)}, status=200)


# ============================ PUBLISH / PROGRESS (teacher/student) ============================
class LessonPublishView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    @transaction.atomic
    def patch(self, request, pk: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=pk)
        if not IsCourseAuthorOrStaff().has_object_permission(request, self, lesson):
            return Response({"detail":"Немає прав."}, status=403)

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


class LessonProgressUpsertView(APIView):
    """
    POST /progress/<lesson_id>/
    body: {"state": "started|completed", "result_percent": 0..100?}
    """
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    @transaction.atomic
    def post(self, request, lesson_id: int):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
        state = request.data.get('state')
        if state not in (LessonProgress.State.STARTED, LessonProgress.State.COMPLETED):
            return Response({"detail": "Невірний state."}, status=400)

        rp = request.data.get('result_percent', None)
        if rp is not None:
            try:
                rp = int(rp)
                if not (0 <= rp <= 100):
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
        if rp is not None:
            lp.result_percent = rp
        lp.save()
        return Response(LessonProgressSerializer(lp).data, status=200)


# ============================ PUBLIC (student) ============================
class LessonPublicDetailView(APIView):
    """GET /public/lessons/<id>/ — тільки PUBLISHED + без прихованих блоків."""
    permission_classes = [IsAuthenticatedOrReadOnly, HasCourseAccess]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def get(self, request, id: int):
        lesson = get_object_or_404(
            Lesson.objects.select_related('course', 'module').prefetch_related('contents'),
            id=id, status=Lesson.Status.PUBLISHED
        )
        data = LessonSerializer(lesson).data
        data['contents'] = [c for c in data.get('contents', []) if not c.get('is_hidden')]
        return Response(data, status=200)


class LessonPublicDetailViewById(APIView):
    """GET /public/lessons/id/<lesson_id>/ — той самий доступ, просто інший шлях."""
    permission_classes = [IsAuthenticatedOrReadOnly, HasCourseAccess]

    def get_course(self, obj):
        return _get_course_from_obj(obj)

    def get(self, request, lesson_id: int):
        lesson = get_object_or_404(
            Lesson.objects.select_related('course', 'module').prefetch_related('contents'),
            pk=lesson_id, status=Lesson.Status.PUBLISHED
        )
        data = LessonSerializer(lesson).data
        data['contents'] = [c for c in data.get('contents', []) if not c.get('is_hidden')]
        return Response(data, status=200)


class LessonsByCourseView(ListAPIView):
    """Список опублікованих уроків курсу + прогрес користувача (якщо є)."""
    serializer_class = LessonPublicListWithProgressSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        qs = Lesson.objects.filter(
            status=Lesson.Status.PUBLISHED
        ).filter(
            Q(module__course_id=course_id) | Q(module__isnull=True, course_id=course_id)
        ).order_by('order', 'id')
        return annotate_with_user_progress(qs, self.request.user)


def annotate_with_user_progress(qs, user):
    if not user or not user.is_authenticated:
        return qs.annotate(
            completed=models.Value(False, output_field=models.BooleanField()),
            result_percent=Subquery(LessonProgress.objects.none().values('result_percent')[:1]),
        )
    user_progress = LessonProgress.objects.filter(user=user, lesson=OuterRef('pk'))
    return qs.annotate(
        completed=Exists(user_progress.filter(state=LessonProgress.State.COMPLETED)),
        result_percent=Subquery(user_progress.order_by('-updated_at').values('result_percent')[:1]),
    )


# ============================ COMPAT: «theories» ============================
class LessonTheoryView(APIView):
    """
    Сумісні ендпоінти для «теорій»:
    GET  /lesson/theories/<lesson_id>/                → [{"id", "text"}]
    POST /lesson/theories/<lesson_id>/                → {"id","text"}
    PUT  /lesson/theories/<lesson_id>/<theory_id>/    → {"id","text"}
    Реально зберігає/читає з LessonContent(type='text' або 'html').
    """
    permission_classes = [permissions.IsAuthenticated, IsCourseAuthorOrStaff]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        blocks = lesson.contents.filter(type__in=['text', 'html']).order_by('order', 'id')
        out = []
        for b in blocks:
            text = b.data.get('html') or b.data.get('text') or ''
            out.append({"id": b.id, "text": text})
        return Response(out)

    @transaction.atomic
    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        txt = request.data.get("text") or request.data.get("theory_text") or ""
        if not txt:
            return Response({"detail": "Empty theory"}, status=400)
        block = LessonContent.objects.create(lesson=lesson, type='text', data={"html": txt}, order=lesson.contents.count())
        return Response({"id": block.id, "text": txt}, status=201)

    @transaction.atomic
    def put(self, request, lesson_id, theory_id):
        block = get_object_or_404(LessonContent, pk=theory_id, lesson_id=lesson_id, type__in=['text', 'html'])
        txt = request.data.get("text") or request.data.get("theory_text") or ""
        block.data['html'] = txt
        block.save(update_fields=['data'])
        return Response({"id": block.id, "text": txt})


@api_view(['GET'])
def lesson_theory(request, lesson_id):
    """
    GET /lessons/<lesson_id>/theory/ — ще один сумісний гет, що склеює всі text|html блоки.
    """
    try:
        lesson = Lesson.objects.get(pk=lesson_id)
        theory_content = []
        for c in lesson.contents.all():
            if not c.is_hidden and c.type in ['text', 'html']:
                text = c.data.get('html') or c.data.get('text') or ''
                if text:
                    theory_content.append(text)
        if not theory_content:
            theory_content = ["Теорія поки що відсутня."]
        return Response({'id': lesson.id, 'title': lesson.title, 'duration_min': lesson.duration_min, 'theory': theory_content})
    except Lesson.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
