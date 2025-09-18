from typing import Any, Dict, List
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view

from lesson.models import Lesson
from .models import Test, Question, Choice, TestAttempt, AnswerAttempt
from .serializers import (
    TestSerializer, QuestionSerializer,
    TestAttemptSerializer, TestAttemptDetailSerializer
)
from .permissions import HasCourseAccess


# ---------- Helpers ----------

def _is_course_author_or_staff(user, course) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or getattr(course, 'author_id', None) == user.id))


def _sanitize_test_for_student(test: Test, data: Dict[str, Any], *, shuffle_q: bool, shuffle_o: bool) -> Dict[str, Any]:
    """Remove is_correct/feedback; optionally shuffle questions/options (payload only)."""
    # hide correctness
    for q in data.get('questions', []):
        for c in q.get('choices', []) or []:
            c.pop('is_correct', None)
            c.pop('feedback', None)

    # shuffle (do not change DB)
    if shuffle_q and test.shuffle_questions:
        import random
        random.shuffle(data['questions'])
    if shuffle_o and test.shuffle_options:
        import random
        for q in data.get('questions', []):
            if q.get('choices'):
                random.shuffle(q['choices'])
    return data


def _build_breakdown_payload(attempt: TestAttempt) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for aa in attempt.answers.select_related('question').prefetch_related('selected_options', 'question__choices'):
        q = aa.question
        item: Dict[str, Any] = {
            "question": q.id,
            "type": q.type,
            "awarded": float(aa.score_awarded or 0),
            "max": float(q.points),
            "is_correct": aa.is_correct,
            "needs_manual": aa.needs_manual,
        }
        # selected ids for choice-based
        item["selected_option_ids"] = list(aa.selected_options.values_list('id', flat=True)) if aa.selected_options.exists() else []

        # correct ids for highlighting
        if q.type in ['single', 'multiple', 'true_false']:
            item["correct_option_ids"] = list(q.choices.filter(is_correct=True).values_list('id', flat=True))

        # free payloads
        if aa.free_text:
            item["free_text"] = aa.free_text
        if aa.free_json:
            item["free_json"] = aa.free_json

        out.append(item)
    return out


def _respect_feedback_mode(test: Test, attempt: TestAttempt) -> Dict[str, Any]:
    """Return attempt payload according to show_feedback_mode (none|immediate|after_close)."""
    payload = TestAttemptSerializer(attempt).data
    mode = (test.show_feedback_mode or 'after_close').lower()
    now = timezone.now()
    is_closed = bool(test.closes_at and now > test.closes_at)

    if mode == 'none':
        return payload
    if mode == 'immediate':
        payload["breakdown"] = _build_breakdown_payload(attempt)
        return payload
    # after_close
    if is_closed:
        payload["breakdown"] = _build_breakdown_payload(attempt)
    return payload


# ---------- Teacher: CRUD ----------

class TestListCreateView(generics.ListCreateAPIView):
    """
    GET: list tests (filter by ?lesson_id=)
    POST: create test (author/staff only)
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
            # rollback by raising
            raise permissions.PermissionDenied("Немає прав створювати тести в цьому курсі.")


class TestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE for a test — author/staff only.
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


# ---------- Teacher: “create/” endpoint used by current FE ----------

class CreateTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        lesson_id = request.data.get("lesson")
        lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)

        if not _is_course_author_or_staff(request.user, lesson.course):
            return Response({"detail": "Немає прав."}, status=status.HTTP_403_FORBIDDEN)

        if Test.objects.filter(lesson=lesson).exists():
            return Response({"detail": "Тест уже існує."}, status=status.HTTP_400_BAD_REQUEST)

        ser = TestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        test = ser.save()
        return Response(TestSerializer(test).data, status=status.HTTP_201_CREATED)


# ---------- Student: public test payload ----------

class TestPublicDetailView(APIView):
    """
    Returns sanitized test for taking (no correctness flags, with optional shuffles).
    """
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj: Test):
        return obj.lesson.course

    def get(self, request, pk: int):
        test = get_object_or_404(
            Test.objects.select_related('lesson__course'),
            pk=pk, status=Test.Status.PUBLISHED
        )

        now = timezone.now()
        if (test.opens_at and now < test.opens_at) or (test.closes_at and now > test.closes_at):
            return Response({"detail": "Тест недоступний за розкладом."}, status=403)

        data = TestSerializer(test).data
        data = _sanitize_test_for_student(test, data, shuffle_q=True, shuffle_o=True)
        return Response(data, status=200)


# ---------- Student: start attempt ----------

class StartAttemptView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCourseAccess]

    def get_course(self, obj: Test):
        return obj.lesson.course

    def post(self, request, pk: int):
        user = request.user
        test = get_object_or_404(
            Test.objects.select_related('lesson__course'),
            pk=pk, status=Test.Status.PUBLISHED
        )

        now = timezone.now()
        if (test.opens_at and now < test.opens_at) or (test.closes_at and now > test.closes_at):
            return Response({"detail": "Тест недоступний за розкладом."}, status=403)

        # attempts limit (None = unlimited on BE; FE can still restrict)
        last_no = TestAttempt.objects.filter(test=test, user=user).aggregate(Max('attempt_no'))['attempt_no__max'] or 0
        next_no = last_no + 1
        if (test.attempts_allowed or 0) > 0 and next_no > int(test.attempts_allowed):
            return Response({"detail": "Вичерпано кількість спроб."}, status=403)

        try:
            attempt = TestAttempt.objects.create(
                test=test, user=user, attempt_no=next_no, pass_mark=float(test.pass_mark or 0)
            )
        except IntegrityError:
            attempt = TestAttempt.objects.filter(test=test, user=user, attempt_no=next_no).first()
            if not attempt:
                return Response({"detail": "Не вдалося створити спробу."}, status=500)

        return Response(TestAttemptSerializer(attempt).data, status=201)


# ---------- Student: submit attempt ----------

class SubmitAttemptView(APIView):
    """
    Accepts payload:
    {
      "answers": [
        {"question": <id>, "selected": <choice_id>},          # single/true_false
        {"question": <id>, "selected": [<choice_id>, ...]},   # multiple
        {"question": <id>, "text": "..."},                    # short/long/code
        {"question": <id>, "data": {...}}                     # match/order
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
        attempt = get_object_or_404(
            TestAttempt.objects.select_related('test__lesson__course'),
            pk=attempt_id, test=test, user=user
        )

        if attempt.status != TestAttempt.Status.STARTED:
            return Response({"detail": "Спроба вже завершена."}, status=400)

        now = timezone.now()

        # timer
        if test.time_limit_sec and attempt.started_at:
            elapsed = (now - attempt.started_at).total_seconds()
            if elapsed > test.time_limit_sec + 1:
                attempt.finished_at = now
                attempt.duration_sec = int(elapsed)
                attempt.status = TestAttempt.Status.SUBMITTED
                attempt.score = 0
                attempt.max_score = sum(float(q.points) for q in test.questions.all())
                attempt.save()
                payload = TestAttemptSerializer(attempt).data
                payload["detail"] = "Час вичерпано. Спробу зафіксовано без балів."
                return Response(payload, status=200)

        payload = request.data or {}
        answers: List[Dict[str, Any]] = payload.get('answers', [])

        # reset (if re-submit same attempt)
        attempt.answers.all().delete()

        total_points = 0.0
        gained_points = 0.0

        # Cache questions & choices
        qmap: Dict[int, Question] = {q.id: q for q in test.questions.all()}
        choices_by_q: Dict[int, Dict[int, Choice]] = {qid: {c.id: c for c in q.choices.all()} for qid, q in qmap.items()}

        for item in answers:
            qid = int(item.get('question'))
            q = qmap.get(qid)
            if not q:
                continue

            total_points += float(q.points)
            aa = AnswerAttempt.objects.create(attempt=attempt, question=q)

            if q.type in ['single', 'true_false']:
                selected_id = item.get('selected')
                ch = choices_by_q[q.id].get(int(selected_id)) if selected_id else None
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

                # partial: (good - bad) / #correct, clipped to [0..1]
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
                    # allow synonyms from spec.answers (lowercased trimmed)
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

        # finalize attempt
        attempt.max_score = total_points
        attempt.score = gained_points
        attempt.status = TestAttempt.Status.SUBMITTED
        attempt.finished_at = now
        if attempt.started_at:
            attempt.duration_sec = int((attempt.finished_at - attempt.started_at).total_seconds())
        attempt.save()

        return Response(_respect_feedback_mode(test, attempt), status=200)


# ---------- “Lesson → first published test” & “check” endpoints used by FE ----------

@api_view(['GET'])
def lesson_test_by_lesson(request, lesson_id: int):
    """Return first published test of a lesson (sanitized) for student."""
    try:
        lesson = Lesson.objects.select_related('course').get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return Response({'detail': 'Lesson not found.'}, status=404)

    test = lesson.tests.filter(status=Test.Status.PUBLISHED).first()
    if not test:
        return Response({'detail': 'Test not found or not published.'}, status=404)

    data = TestSerializer(test).data
    data = _sanitize_test_for_student(test, data, shuffle_q=True, shuffle_o=True)
    return Response(data, status=200)


@api_view(['GET'])
def check_lesson_test(request, lesson_id: int):
    """Lightweight “does test exist for lesson?” endpoint (used by builder UI)."""
    exists = Test.objects.filter(lesson_id=lesson_id).exists()
    return Response({"exists": exists}, status=200)
