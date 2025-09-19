from rest_framework.permissions import BasePermission, SAFE_METHODS

class HasCourseAccess(BasePermission):
    """
    Checks user access to a course inferred from a view's object via view.get_course(obj).
    Works with:
      - course author / staff / superuser
      - enrolled student (if your Course has enrollment relation, adapt check)
    """
    message = "Немає доступу до цього курсу."

    def has_object_permission(self, request, view, obj):
        get_course = getattr(view, 'get_course', None)
        if not callable(get_course):
            return False

        course = get_course(obj)
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        # Author of the course
        if getattr(course, 'author_id', None) == user.id:
            return True

        # If you have enrollments — add your rule here, e.g.:
        # return course.students.filter(id=user.id).exists()
        # By default — deny.
        return False
