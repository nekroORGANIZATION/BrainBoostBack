from rest_framework import generics
from .models import Story
from .serializers import StoryListSerializer, StoryDetailSerializer


class StoryListView(generics.ListAPIView):
    """
    Список сторісів (тільки опубліковані).
    Використовується для головної сторінки.
    """
    serializer_class = StoryListSerializer

    def get_queryset(self):
        return Story.objects.all().order_by("-published_at")


class StoryDetailView(generics.RetrieveAPIView):
    """
    Детальна сторінка історії (на майбутнє).
    """
    queryset = Story.objects.all()
    serializer_class = StoryDetailSerializer
