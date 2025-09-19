# payments/urls.py
from django.urls import path
from .views import PayPalCreatePaymentView, CoinbasePaymentView, PayPalDebugView

urlpatterns = [
    path('paypal/create/', PayPalCreatePaymentView.as_view()),
    path('create-crypto-payment/', CoinbasePaymentView.as_view(), name='create-crypto-payment'),
    path('paypal/debug/', PayPalDebugView.as_view(), name='paypal-debug'),  # <- новый
]
