from django.urls import path
from .views import PayPalCreatePaymentView, CoinbasePaymentView

urlpatterns = [
    path('paypal/create/', PayPalCreatePaymentView.as_view()),
    path('create-crypto-payment/', CoinbasePaymentView.as_view(), name='create-crypto-payment'),
]
