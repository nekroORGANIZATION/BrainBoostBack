from django.urls import path
from .views import StoryListView, StoryDetailView

urlpatterns = [
    path("stories/", StoryListView.as_view(), name="stories-list"),
    path("stories/<int:pk>/", StoryDetailView.as_view(), name="story-detail"),
]
