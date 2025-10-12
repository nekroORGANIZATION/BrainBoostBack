# serializers.py
from django.utils.encoding import iri_to_uri
from rest_framework import serializers
from .models import Story


def build_cover_url(request, raw_value: str | None) -> str | None:
    """
    Приймає те, що зберігається у моделі (наприклад: 'media/stories/covers/x.png',
    '/media/stories/covers/x.png' або вже 'https://...').
    Повертає абсолютний URL (якщо є request) або нормалізований шлях, що починається з /media/.
    """
    if not raw_value:
        return None

    v = str(raw_value).strip()
    if not v:
        return None

    # Якщо вже абсолютний URL — повертаємо як є
    if v.lower().startswith("http://") or v.lower().startswith("https://"):
        return v

    # Нормалізуємо до /media/... (покриває 'media/...', '/media/...', інші варіанти не чіпаємо)
    if v.startswith("/media/"):
        url_path = v
    elif v.startswith("media/"):
        url_path = "/" + v
    else:
        # Якщо у вас в полі інколи лежать інші абсолютні шляхи (типу /static/...),
        # залишимо як є, щоб нічого не зламати.
        url_path = v if v.startswith("/") else "/" + v

    url_path = iri_to_uri(url_path)  # захист від пробілів/юнікоду

    # Якщо у serializer є request — віддамо абсолютний URL, інакше лишимо шлях
    if request is not None:
        return request.build_absolute_uri(url_path)
    return url_path


class StoryListSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ["id", "title", "cover", "published_at", "author_name"]

    def get_cover(self, obj):
        request = self.context.get("request")
        return build_cover_url(request, getattr(obj, "cover", None))


class StoryDetailSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ["id", "title", "content", "cover", "published_at", "author_name"]

    def get_cover(self, obj):
        request = self.context.get("request")
        return build_cover_url(request, getattr(obj, "cover", None))
