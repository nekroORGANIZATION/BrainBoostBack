from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from .paypal_service import PayPalService
from .coinbase_service import create_coinbase_charge
import json


def _extract_paypal_error(e):
    try:
        if hasattr(e, 'response') and getattr(e, 'response', None) is not None:
            resp = e.response
            try:
                return resp.json()
            except Exception:
                return {"text": getattr(resp, "text", str(e))}
        s = str(e)
        try:
            return json.loads(s)
        except Exception:
            return {"message": s}
    except Exception:
        return {"message": str(e)}


class PayPalCreatePaymentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        total = request.data.get('amount', 10.00)
        currency = request.data.get('currency', 'USD')
        description = request.data.get('description', 'Оплата курсу')
        try:
            result = PayPalService.create_payment(
                total=total,
                currency=currency,
                description=description,
                return_url=getattr(settings, "FRONTEND_BASE", "http://localhost:3000") + "/checkout/success",
                cancel_url=getattr(settings, "FRONTEND_BASE", "http://localhost:3000") + "/checkout/cancel",
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            details = _extract_paypal_error(e)
            return Response(
                {"detail": "PayPal create error", "paypal_error": details},
                status=status.HTTP_400_BAD_REQUEST
            )


class CoinbasePaymentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            data = request.data
            charge = create_coinbase_charge(
                name=data.get('name', 'Order Payment'),
                description=data.get('description', 'Crypto payment for order'),
                amount=data.get('amount', 10),
                currency=data.get('currency', 'USD'),
            )
            return Response({'hosted_url': charge['data']['hosted_url']}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.permissions import IsAdminUser
from .paypal_debug import try_fetch_access_token

class PayPalDebugView(APIView):
    permission_classes = [IsAdminUser]  # не отдаём случайным пользователям

    def get(self, request):
        data = try_fetch_access_token()
        return Response(data, status=200 if data["ok"] else 400)
    