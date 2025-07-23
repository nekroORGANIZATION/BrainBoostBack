import re
from django.db.models import Q
from course.models import Course


def find_courses_by_keywords(recommended_titles: list[str]) -> list[Course]:
    query = Q()

    for title in recommended_titles:
        keywords = re.findall(r'\b\w+\b', title.lower())

        for keyword in keywords:
            if len(keyword) >= 3:
                query |= Q(title__icontains=keyword)

    matching_courses = Course.objects.filter(query).distinct()

    return list(matching_courses)