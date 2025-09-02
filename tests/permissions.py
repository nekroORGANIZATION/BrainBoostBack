from rest_framework.permissions import BasePermission, SAFE_METHODS
from course.models import PurchasedCourse

class HasCourseAccess(BasePermission):
    """
    Дозволяє доступ до тесту/уроку лише тим, хто купив курс або staff.
    Очікує у view: self.get_course(obj) -> Course
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        course = view.get_course(obj)
        return PurchasedCourse.objects.filter(user=user, course=course, is_active=True).exists()
