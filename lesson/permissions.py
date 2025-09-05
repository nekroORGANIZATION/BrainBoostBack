from rest_framework.permissions import BasePermission
from course.models import PurchasedCourse


class HasCourseAccess(BasePermission):
    """
    Доступ до уроку/модуля лише тим, хто купив курс (is_active=True), або staff.
    Очікує у view метод get_course(obj) -> Course.
    """
    message = "Немає доступу до курсу."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        course = view.get_course(obj)
        return PurchasedCourse.objects.filter(user=user, course=course, is_active=True).exists()


class IsCourseAuthorOrStaff(BasePermission):
    """
    Тільки автор курсу (course.author) або staff.
    Очікує у view метод get_course(obj) -> Course.
    """
    message = "Потрібні права викладача курсу."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        course = view.get_course(obj)
        return getattr(course, 'author_id', None) == user.id

    def has_permission(self, request, view):
        # для create-ендпоїнтів: візьмемо course_id з даних
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            user = request.user
            if user.is_staff or user.is_superuser:
                return True
            course_id = request.data.get('course') or request.data.get('course_id')
            if course_id:
                from course.models import Course
                try:
                    course = Course.objects.get(pk=course_id)
                    return course.author_id == user.id
                except Course.DoesNotExist:
                    return False
        return True


class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (getattr(u, 'is_superuser', False) or getattr(u, 'is_teacher', False)))
    