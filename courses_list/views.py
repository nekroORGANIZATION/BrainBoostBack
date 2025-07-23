from rest_framework.views import APIView
from rest_framework.response import Response
from course.models import Course
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from .serializers import CourseSerializer

class CourseListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        courses = Course.objects.all()
        data = [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "price": float(course.price),
                "author": course.author,
                "language": course.language,
                "topic": course.topic,
                "image": request.build_absolute_uri(course.image.url) if course.image else None,
                "rating": float(course.rating),
            }
            for course in courses
        ]
        return Response(data, status=status.HTTP_200_OK)


class CourseDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        serializer = CourseSerializer(course, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
