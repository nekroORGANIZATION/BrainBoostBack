from django.urls import path
from .views import (
    CategoryListAPIView,
    CourseListCreateAPIView, CourseDetailAPIView, CourseUpdateAPIView, CourseDeleteAPIView, CourseRetrieveUpdateByIDAPIView,
    UserPurchasedCoursesView, EnrollCourseView,
    CommentListCreateView, CommentRetrieveUpdateDestroyView,
)

urlpatterns = [
    # Categories
    path("categories/", CategoryListAPIView.as_view(), name="course-categories"),

    # Courses (author/staff CRUD + public detail)
    path("", CourseListCreateAPIView.as_view(), name="course-list"),
    path("<int:pk>/", CourseRetrieveUpdateByIDAPIView.as_view(), name="course-detail-id"),
    path("<slug:slug>/", CourseDetailAPIView.as_view(), name="course-detail"),
    path("<slug:slug>/edit/", CourseUpdateAPIView.as_view(), name="course-update"),
    path("<slug:slug>/delete/", CourseDeleteAPIView.as_view(), name="course-delete"),

    # Purchase / access
    path("me/purchased/", UserPurchasedCoursesView.as_view(), name="course-purchased"),
    path("<slug:slug>/enroll/", EnrollCourseView.as_view(), name="course-enroll-dev"),

    # Comments
    path("<slug:slug>/comments/", CommentListCreateView.as_view(), name="course-comments"),
    path("<slug:slug>/comments/<int:pk>/", CommentRetrieveUpdateDestroyView.as_view(), name="course-comment-detail"),
]
