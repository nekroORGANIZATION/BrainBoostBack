from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .paypal_service import PayPalService

from .coinbase_service import create_coinbase_charge


class PayPalCreatePaymentView(APIView):
    def post(self, request):
        total = request.data.get('amount', 10.00)
        currency = request.data.get('currency', 'USD')
        description = request.data.get('description', 'Оплата курсу')

        try:
            result = PayPalService.create_payment(
                total=total,
                currency=currency,
                description=description,
                return_url='https://your.site/payment/success/',
                cancel_url='https://your.site/payment/cancel/'
            )

            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CoinbasePaymentView(APIView):
    def post(self, request):
        try:
            data = request.data
            charge = create_coinbase_charge(
                name=data.get('name', 'Order Payment'),
                description=data.get('description', 'Crypto payment for order'),
                amount=data.get('amount', 10)
            )
            return Response({'hosted_url': charge['data']['hosted_url']}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        