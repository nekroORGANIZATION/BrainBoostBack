from django.db import models
from django.conf import settings

class Payment(models.Model):
    class Provider(models.TextChoices):
        PAYPAL = "paypal", "PayPal"
        COINBASE = "coinbase", "Coinbase"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELED = "canceled", "Canceled"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payments"
    )
    course_id = models.IntegerField(null=True, blank=True)  # если хочешь FK — замени на ForeignKey
    provider = models.CharField(max_length=20, choices=Provider.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    external_id = models.CharField(max_length=128, blank=True, default="")   # PayPal payment id / Coinbase charge id
    metadata = models.JSONField(default=dict, blank=True)  # любые доп. поля (название курса и т.д.)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_paid(self):
        self.status = self.Status.PAID
        self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return f"{self.provider} {self.amount} {self.currency} [{self.status}]"
