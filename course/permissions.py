from rest_framework.permissions import BasePermission


class IsCourseAuthorOrStaff(BasePermission):
    message = "Потрібні права автора курсу або staff."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        # obj може бути Course або Comment (через obj.course)
        course = obj if getattr(obj, "author_id", None) else getattr(obj, "course", None)
        if not course:
            return False
        return getattr(course, "author_id", None) == user.id
