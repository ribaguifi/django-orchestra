from django.db import models

from orchestra.contrib.bills.models import BillContact


class SyncedModel(models.Model):
    class Status:
        SYNCED = "synced"
        ERROR = "error"
        PENDING = "pending"
        WARNING = "warning"

    remote_id = models.BigIntegerField(null=True)
    first_synced_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default=Status.SYNCED)
    message = models.TextField(blank=True, default="")

    class Meta:
        abstract = True


class B2BContact(SyncedModel):
    orchestra_contact = models.OneToOneField(
        BillContact,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    def __str__(self):
        return f"Contact({self.orchestra_contact} - {self.remote_id})"

    class Meta:
        unique_together = (("orchestra_contact", "remote_id"),)


class B2BInvoice(SyncedModel):
    orchestra_bill = models.OneToOneField(
        "bills.Bill",
        on_delete=models.CASCADE,
        primary_key=True,
    )

    def __str__(self):
        return f"Invoice({self.orchestra_bill} - {self.remote_id})"

    class Meta:
        unique_together = (("orchestra_bill", "remote_id"),)
