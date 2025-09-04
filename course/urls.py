from django.urls import path
from .views import (
    CategoryListAPIView,
    CourseListCreateAPIView, CourseDetailAPIView, CourseUpdateAPIView, CourseDeleteAPIView, CourseRetrieveUpdateByIDAPIView,
    LanguageAdminListCreateAPIView,
    UserPurchasedCoursesView, EnrollCourseView,
    CommentListCreateView, CommentRetrieveUpdateDestroyView,
    WishlistListCreateView, WishlistDeleteView, WishlistToggleView, LanguageListAPIView,
    CategoryAdminDetailAPIView, CategoryAdminListCreateAPIView, LanguageAdminDetailAPIView
)

urlpatterns = [
    # Categories
    path("categories/", CategoryListAPIView.as_view(), name="course-categories"),
    path("languages/", LanguageListAPIView.as_view(), name="course-languages"),

    # Админ-панель (только для IsAdminUser)
    path("admin/categories/", CategoryAdminListCreateAPIView.as_view(), name="admin-categories"),
    path("admin/categories/<int:pk>/", CategoryAdminDetailAPIView.as_view(), name="admin-category-detail"),

    path("admin/languages/", LanguageAdminListCreateAPIView.as_view(), name="admin-languages"),
    path("admin/languages/<int:pk>/", LanguageAdminDetailAPIView.as_view(), name="admin-language-detail"),

    # Courses list / by id
    path("", CourseListCreateAPIView.as_view(), name="course-list"),
    path("<int:pk>/", CourseRetrieveUpdateByIDAPIView.as_view(), name="course-detail-id"),

    # ✅ Wishlist (ставим выше, чтобы не съелось <slug:slug>/)
    path("wishlist/", WishlistListCreateView.as_view(), name="wishlist-list-create"),
    path("me/wishlist/", WishlistListCreateView.as_view(), name="wishlist-list-create"),
    path("me/wishlist/<int:course_id>/", WishlistDeleteView.as_view(), name="wishlist-delete"),
    path("wishlist/toggle/", WishlistToggleView.as_view(), name="wishlist-toggle"),
    path("wishlist/<int:course_id>/", WishlistDeleteView.as_view(), name="wishlist-delete"),

    # Purchase / access
    path("me/purchased/", UserPurchasedCoursesView.as_view(), name="course-purchased"),
    path("<slug:slug>/enroll/", EnrollCourseView.as_view(), name="course-enroll-dev"),

    # Comments
    path("<slug:slug>/comments/", CommentListCreateView.as_view(), name="course-comments"),
    path("<slug:slug>/comments/<int:pk>/", CommentRetrieveUpdateDestroyView.as_view(), name="course-comment-detail"),

    # Detail / edit / delete by slug (в самом конце)
    path("<slug:slug>/", CourseDetailAPIView.as_view(), name="course-detail"),
    path("<slug:slug>/edit/", CourseUpdateAPIView.as_view(), name="course-update"),
    path("<slug:slug>/delete/", CourseDeleteAPIView.as_view(), name="course-delete"),
]
