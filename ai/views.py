from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ai.services.recommendation import get_recommendations
from course.models import Course
from .utils import find_courses_by_keywords 
from rest_framework.permissions import AllowAny

from rest_framework import status
from lesson.models import Lesson, LessonContent
from ai.services.helper_bot import explain_concept


def _extract_theory_text_from_content(c: LessonContent) -> str:
    """Дістає текст з LessonContent залежно від типу."""
    try:
        if c.type == 'text':
            return (c.data or {}).get('text', '') or ''
        if c.type == 'html':
            return (c.data or {}).get('html', '') or ''
        if c.type == 'quote':
            return (c.data or {}).get('text', '') or ''
    except Exception:
        pass
    return ''

@api_view(['POST'])
@permission_classes([AllowAny])   # ← якщо треба закрити — заміни на [IsAuthenticated]
def ask_ai(request):
    lesson_id = request.data.get("lesson_id")
    question = (request.data.get("question") or "").strip()

    if not lesson_id or not question:
        return Response(
            {"error": "lesson_id та question є обовʼязковими."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Беремо неблоковані блоки теорії потрібних типів
    contents = (
        lesson.contents
        .filter(is_hidden=False, type__in=['text', 'html'])   # додай 'quote' за потреби
        .order_by('order', 'id')
    )

    parts = []
    for c in contents:
        txt = _extract_theory_text_from_content(c)
        if txt:
            parts.append(txt)

    if not parts:
        return Response(
            {"error": "Для цього уроку поки немає теорії."},
            status=status.HTTP_404_NOT_FOUND,
        )

    theory_text = "\n\n".join(parts)
    # за бажанням, можна трохи обрізати надто великий текст:
    # MAX = 12000
    # if len(theory_text) > MAX:
    #     theory_text = theory_text[:MAX]

    try:
        answer = explain_concept(theory_text, question)
    except Exception as e:
        return Response({"error": f"AI error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"answer": answer}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def course_recommendation_view(request):
    passed_tests_titles = request.data.get('passed_tests', [])
    if not isinstance(passed_tests_titles, list):
        return Response({"error": "passed_tests має бути списком."}, status=400)

    try:
        recommended_titles = get_recommendations(passed_tests_titles)
    except Exception as e:
        return Response({"error": f"Помилка при отриманні рекомендацій: {str(e)}"}, status=502)

    matching_courses = find_courses_by_keywords(recommended_titles)

    if not matching_courses:
        return Response({'recommended_courses': []})

    result = []
    for course in matching_courses:
        author = course.author
        author_data = {
            "id": getattr(author, "id", None),
            "username": getattr(author, "username", None),
            "email": getattr(author, "email", None),
        }
        result.append({
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "price": str(course.price),
            "author": author_data,
            "language": course.language,
            "topic": course.topic,
            "rating": str(course.rating),
        })

    return Response({'recommended_courses': result})
