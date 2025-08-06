from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ai.services.recommendation import get_recommendations
from course.models import Course
from .utils import find_courses_by_keywords 

from lesson.models import Lesson
from ai.services.helper_bot import explain_concept


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_ai(request):
    try:
        lesson_id = request.data.get("lesson_id")
        question = request.data.get("question")

        if not lesson_id or not question:
            return Response({"error": "Lesson_id or question not passed."}, status=400)

        lesson = get_object_or_404(Lesson, id=lesson_id)

        theories = lesson.theories.all()

        if not theories.exists():
            return Response({"error": "There is no theory for this lesson."}, status=404)

        theory_text = "\n\n".join([theory.theory_text for theory in theories])

        answer = explain_concept(theory_text, question)

        return Response({"answer": answer})

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
