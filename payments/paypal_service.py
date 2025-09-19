import paypalrestsdk
from django.conf import settings

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # "sandbox" или "live"
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

class PayPalService:
    @staticmethod
    def create_payment(total, currency, description, return_url, cancel_url):
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "amount": {"total": f"{float(total):.2f}", "currency": currency},
                "description": description
            }]
        })

        if payment.create():
            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break
            return {"id": payment.id, "approval_url": approval_url}
        else:
            raise Exception(payment.error)

    @staticmethod
    def execute_payment(payment_id, payer_id):
        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            return payment
        else:
            raise Exception(payment.error)
