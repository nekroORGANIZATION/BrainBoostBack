from django.urls import path
from .views import TipOfDayAPIView

urlpatterns = [
    path("daily/", TipOfDayAPIView.as_view(), name="tip-of-day"),
]
