from typing import Any, Dict, List
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Test, Question, Choice, TestAttempt, AnswerAttempt
from .serializers import TestSerializer, QuestionSerializer, TestAttemptSerializer
from .permissions import HasCourseAccess


# ---------- ХЕЛПЕРИ ----------

def _is_course_author_or_staff(user, course) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or course.author_id == user.id))


def _sanitize_test_for_student(test: Test, data: Dict[str, Any], *, shuffle_q: bool, shuffle_o: bool) -> Dict[str, Any]:
    """
    Прибираємо службову інформацію (is_correct), опційно перемішуємо питання/варіанти.
    """
    # Не віддаємо is_correct студенту
    for q in data.get('questions', []):
        for c in q.get('choices', []) or []:
            c.pop('is_correct', None)
            c.pop('feedback', None)

    # Перемішування (тільки в payload, не у БД)
    if shuffle_q and test.shuffle_questions:
        import random
        random.shuffle(data['questions'])
    if shuffle_o and test.shuffle_options:
        import random
        for q in data.get('questions', []):
            if q.get('choices'):
                random.shuffle(q['choices'])

    return data


def _respect_feedback_mode(test: Test, attempt: TestAttempt) -> Dict[str, Any]:
    """
    Формуємо відповідь після сабміту з урахуванням режиму показу фідбеку.
    show_feedback_mode: none | immediate | after_close
    """
    payload = TestAttemptSerializer(attempt).data
    mode = (test.show_feedback_mode or 'after_close').lower()

    def _build_breakdown():
        out = []
        for aa in attempt.answers.select_related('question').prefetch_related('selected_options'):
            item = {
                "question": aa.question_id,
                "type": aa.question.type,
                "awarded": float(aa.score_awarded or 0),
                "max": float(aa.question.points),
                "is_correct": aa.is_correct,
            }
            # Що саме показувати? Без розкриття правильних варіантів — лише обрана відповідь
            if aa.selected_options.exists():
                item["selected_option_ids"] = list(aa.selected_options.values_list('id', flat=True))
            if aa.free_text:
                item["free_text"] = aa.free_text
            if aa.free_json:
                item["free_json"] = aa.free_json
            out.append(item)
        return out

    now = timezone.now()
    is_closed = bool(test.closes_at and now > test.closes_at)

    if mode == 'none':
        # показуємо лише агрегати
        return payload

    if mode == 'immediate':
        payload["breakdown"] = _build_breakdown()
        return payload

    # after_close
    if is_closed:
        payload["breakdown"] = _build_breakdown()
    return payload


# ---------- CRUD для тестів (для викладача) ----------

class TestListCreateView(generics.ListCreateAPIView):
    """
    GET: cписки тестів (можна фільтрувати по lesson_id)
    POST: створити тест (лише автор курсу або staff)
    """
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Test.objects.select_related('lesson__course').all().order_by('-created_at')
        lesson_id = self.request.query_params.get('lesson_id')
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        return qs

    def perform_create(self, serializer):
        test = serializer.save()
        course = test.lesson.course
        if not _is_course_author_or_staff(self.request.user, course):
            # відкочуємо і забороняємо
            raise permissions.PermissionDenied("Немає прав створювати тести в цьому курсі.")


class TestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE тесту — лише автор курсу/стадд.
    """
    queryset = Test.objects.select_related('lesson__course').all()
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        test = self.get_object()
        if not _is_course_author_or_staff(self.request.user, test.lesson.course):
            raise permissions.PermissionDenied("Немає прав редагувати цей тест.")
        serializer.save()

    def perform_destroy(self, instance):
        if not _is_course_author_or_staff(self.request.user, instance.lesson.course):
            raise permissions.PermissionDenied("Немає прав видаляти цей тест.")
        instance.delete()


# ---------- Публічний перегляд тесту студентом ----------

class TestPublicDetailView(APIView):
    """
    Повертає структуру тесту для проходження студентом (без прапорів правильності).
    """
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj: Test):
        return obj.lesson.course

    def get(self, request, pk: int):
        test = get_object_or_404(Test.objects.select_related('lesson__course'), pk=pk, status=Test.Status.PUBLISHED)

        # Розклад доступу
        now = timezone.now()
        if (test.opens_at and now < test.opens_at) or (test.closes_at and now > test.closes_at):
            return Response({"detail": "Тест недоступний за розкладом."}, status=403)

        data = TestSerializer(test).data
        data = _sanitize_test_for_student(test, data, shuffle_q=True, shuffle_o=True)
        return Response(data, status=200)


# ---------- Старт спроби ----------

class StartAttemptView(APIView):
    """
    Старт спроби. Перевіряє доступ, вікно доступу, ліміт спроб.
    """
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj: Test):
        return obj.lesson.course

    def post(self, request, pk: int):
        user = request.user
        test = get_object_or_404(Test.objects.select_related('lesson__course'), pk=pk, status=Test.Status.PUBLISHED)

        # Розклад доступу
        now = timezone.now()
        if (test.opens_at and now < test.opens_at) or (test.closes_at and now > test.closes_at):
            return Response({"detail": "Тест недоступний за розкладом."}, status=403)

        # Ліміт спроб
        last_no = TestAttempt.objects.filter(test=test, user=user).aggregate(Max('attempt_no'))['attempt_no__max'] or 0
        next_no = last_no + 1
        if test.attempts_allowed and next_no > test.attempts_allowed:
            return Response({"detail": "Вичерпано кількість спроб."}, status=403)

        attempt = TestAttempt.objects.create(
            test=test, user=user, attempt_no=next_no, pass_mark=float(test.pass_mark)
        )
        return Response(TestAttemptSerializer(attempt).data, status=201)


# ---------- Сабміт відповідей ----------

class SubmitAttemptView(APIView):
    """
    Приймає відповіді, автогрейдить, завершує спробу.
    payload:
    {
      "answers": [
        # single / true_false:
        {"question": <id>, "selected": <choice_id>},

        # multiple:
        {"question": <id>, "selected": [<choice_id>, ...]},

        # short/long/code:
        {"question": <id>, "text": "..."},

        # match/order:
        {"question": <id>, "data": {...}}
      ]
    }
    """
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj: Test):
        return obj.lesson.course

    @transaction.atomic
    def post(self, request, pk: int, attempt_id: int):
        user = request.user
        test = get_object_or_404(Test.objects.select_related('lesson__course'), pk=pk)
        attempt = get_object_or_404(TestAttempt.objects.select_related('test__lesson__course'), pk=attempt_id, test=test, user=user)

        if attempt.status != TestAttempt.Status.STARTED:
            return Response({"detail": "Спроба вже завершена."}, status=400)

        now = timezone.now()

        # Контроль часу (таймер)
        if test.time_limit_sec and attempt.started_at:
            elapsed = (now - attempt.started_at).total_seconds()
            if elapsed > test.time_limit_sec + 1:  # невеликий буфер
                # Можемо прийняти з нульовим балом або обмежити (обираємо строгий варіант — 0 балів)
                attempt.finished_at = now
                attempt.duration_sec = int(elapsed)
                attempt.status = TestAttempt.Status.SUBMITTED
                attempt.score = 0
                attempt.max_score = sum(float(q.points) for q in test.questions.all())
                attempt.save()
                return Response({"detail": "Час вичерпано. Спробу зафіксовано без балів.", **TestAttemptSerializer(attempt).data}, status=200)

        payload = request.data or {}
        answers: List[Dict[str, Any]] = payload.get('answers', [])

        # Обнуляємо попередні авто-відповіді (на випадок ре-сабміту тієї ж спроби)
        attempt.answers.all().delete()

        total_points = 0.0
        gained_points = 0.0

        # Підтягнемо питання з choices у памʼять
        qmap: Dict[int, Question] = {q.id: q for q in test.questions.all()}
        choices_by_q: Dict[int, Dict[int, Choice]] = {}
        for q in qmap.values():
            choices_by_q[q.id] = {c.id: c for c in q.choices.all()}

        for item in answers:
            qid = int(item.get('question'))
            q = qmap.get(qid)
            if not q:
                continue

            total_points += float(q.points)
            aa = AnswerAttempt.objects.create(attempt=attempt, question=q)

            if q.type in ['single', 'true_false']:
                selected_id = item.get('selected')
                if selected_id:
                    ch = choices_by_q[q.id].get(int(selected_id))
                    if ch:
                        aa.selected_options.add(ch)
                        aa.is_correct = bool(ch.is_correct)
                        aa.score_awarded = q.points if ch.is_correct else 0

            elif q.type == 'multiple':
                selected_ids = [int(x) for x in (item.get('selected') or [])]
                correct_ids = {cid for cid, ch in choices_by_q[q.id].items() if ch.is_correct}
                picked_ids = {cid for cid in selected_ids if cid in choices_by_q[q.id]}

                if picked_ids:
                    aa.selected_options.add(*[choices_by_q[q.id][cid] for cid in picked_ids])

                # часткове нарахування: (правильні обрані - помилкові обрані) / число правильних
                if correct_ids:
                    good = len(picked_ids & correct_ids)
                    bad = len(picked_ids - correct_ids)
                    raw = max(good - bad, 0) / len(correct_ids)
                    aa.score_awarded = round(float(q.points) * raw, 2)
                    aa.is_correct = (good == len(correct_ids) and bad == 0)

            elif q.type in ['short', 'long', 'code']:
                text = (item.get('text') or '').strip()
                aa.free_text = text
                if q.type == 'short':
                    etalons = [str(s).strip().lower() for s in (q.spec.get('answers') or [])]
                    if etalons:
                        aa.is_correct = (text.lower() in etalons)
                        aa.score_awarded = q.points if aa.is_correct else 0
                        aa.needs_manual = False
                    else:
                        aa.needs_manual = True
                else:
                    aa.needs_manual = True

            elif q.type in ['match', 'order']:
                aa.free_json = item.get('data') or {}
                solution = q.spec.get('solution')
                if solution is not None:
                    aa.is_correct = (aa.free_json == solution)
                    aa.score_awarded = q.points if aa.is_correct else 0
                else:
                    aa.needs_manual = True

            aa.save()
            gained_points += float(aa.score_awarded or 0)

        # Завершення спроби
        attempt.max_score = total_points
        attempt.score = gained_points
        attempt.status = TestAttempt.Status.SUBMITTED
        attempt.finished_at = now
        if attempt.started_at:
            attempt.duration_sec = int((attempt.finished_at - attempt.started_at).total_seconds())
        attempt.save()

        # Відповідь з урахуванням режиму показу фідбеку
        return Response(_respect_feedback_mode(test, attempt), status=200)
