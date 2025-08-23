import logging
from django.conf import settings
from django.core.mail import EmailMessage, get_connection, BadHeaderError
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import ContactMessageSerializer

logger = logging.getLogger("contact")


def _clean_header(s: str) -> str:
    # Защита от инъекций заголовков в subject/headers
    return (s or "").replace("\r", " ").replace("\n", " ").strip()


class ContactMessageView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info("POST /api/contacts/ — отримано дані", extra={"data": request.data})

        serializer = ContactMessageSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Валідація не пройшла", extra={"errors": serializer.errors})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        msg = serializer.save()
        logger.info("Повідомлення збережене в БД", extra={"id": msg.id})

        # Формируем заголовки письма
        subject = _clean_header(f"Нове повідомлення з форми: {msg.topic}")
        body_parts = [
            f"Ім'я: {msg.name or '-'}",
            f"Email: {msg.email or '-'}",
            f"Телефон: {msg.phone or '-'}",
            "",
            "Повідомлення:",
            (msg.message or "").strip(),
        ]
        body = "\n".join(body_parts)

        # Адреса 'от кого' и 'кому'
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
        to_email = getattr(settings, "CONTACT_RECEIVER_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

        if not from_email or not to_email:
            logger.error("Не налаштовано адреси EMAIL_HOST_USER/DEFAULT_FROM_EMAIL/CONTACT_RECEIVER_EMAIL")
            return Response(
                {"detail": "Email не налаштовано на сервері. Зверніться до адміністратора."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            logger.info("Спроба відправити лист", extra={"from": from_email, "to": to_email})

            # Явно создаём SMTP-соединение (уважаем EMAIL_* настройки)
            connection = get_connection(
                fail_silently=False,
                timeout=getattr(settings, "EMAIL_TIMEOUT", 30),
            )

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[to_email],
                reply_to=[_clean_header(msg.email)] if getattr(msg, "email", None) else None,
                headers={"X-Contact-Message-ID": str(msg.id)},
                connection=connection,
            )

            email.send()  # raise on error (fail_silently=False)
            logger.info("Лист успішно відправлено", extra={"msg_id": msg.id})

            return Response(
                {"success": "Ваше повідомлення успішно надіслано!", "email_status": "sent"},
                status=status.HTTP_201_CREATED,
            )

        except BadHeaderError as bhe:
            logger.error("BadHeaderError при відправці пошти", exc_info=bhe)
            return Response(
                {
                    "success": "Збережено, але лист не відправлено (некоректний заголовок).",
                    "email_status": "bad_header",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            # Не логируем пароли/секреты; просто факт ошибки
            logger.error("Помилка при відправці пошти", exc_info=e)
            return Response(
                {
                    "success": "Збережено, але лист не відправлено. Адмін перевірить налаштування пошти.",
                    "email_status": "error",
                },
                status=status.HTTP_201_CREATED,
            )
