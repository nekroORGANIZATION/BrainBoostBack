from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCourseAuthorOrStaff(BasePermission):
    message = "Потрібні права автора курсу або staff."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True

        course = obj if getattr(obj, "author_id", None) else getattr(obj, "course", None)
        if not course:
            return False
        return getattr(course, "author_id", None) == user.id


class IsAuthorOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return user and (user.is_staff or obj.author_id == getattr(user, 'id', None))
