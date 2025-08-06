import paypalrestsdk
from django.conf import settings

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})


class PayPalService:
    @staticmethod
    def create_payment(total, currency, description, return_url, cancel_url):
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "amount": {
                    "total": f"{total:.2f}",
                    "currency": currency
                },
                "description": description
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return {
                        'id': payment.id,  # возвращаем ключ 'id', чтобы фронт его ждал
                        'approval_url': link.href
                    }
        else:
            raise Exception(payment.error)
