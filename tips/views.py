import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

TIPS = [
    {"text": "Короткі відео + практичне завдання в кінці — краще за довгу лекцію."},
    {"text": "Додай чек-лист до уроку — підвищує завершення модуля."},
    {"text": "Використовуй квізи на 3–5 питань після кожного розділу."},
    {"text": "Попроси студентів дати зворотний зв’язок у середині курсу."},
    {"text": "Одна яскрава ілюстрація краще, ніж пів сторінки тексту."},
    {"text": "Дай приклад реального проєкту — мотивація росте."},
    {"text": "Короткі дедлайни з мʼякими нагадуваннями працюють краще."},
]

class TipOfDayAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        today = datetime.date.today()
        idx = today.toordinal() % len(TIPS)
        tip = TIPS[idx]
        return Response({
            "date": today.isoformat(),
            "id": idx,
            "text": tip["text"],
            "source": "BrainBoost tips"
        })
