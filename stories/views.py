# views.py
from rest_framework import generics
from .models import Story
from .serializers import StoryListSerializer, StoryDetailSerializer


class StoryListView(generics.ListAPIView):
    """
    Список сторісів (поки що без додаткових фільтрів).
    Віддає обкладинки як коректні /media/... або абсолютні URL.
    """
    serializer_class = StoryListSerializer

    def get_queryset(self):
        # Якщо потім додаси фільтр «тільки опубліковані» — зроби тут .filter(...)
        return Story.objects.all().order_by("-published_at")


class StoryDetailView(generics.RetrieveAPIView):
    """
    Детальна сторінка історії.
    """
    queryset = Story.objects.all()
    serializer_class = StoryDetailSerializer
