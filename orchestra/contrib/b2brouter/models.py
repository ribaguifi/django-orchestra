from django.db import models
from orchestra.contrib.bills.models import BillContact


class B2BContact(models.Model):
    class Status:
        SYNCED = "synced"
        ERROR = "error"
        PENDING = "pending"
        WARNING = "warning"

    remote_id = models.BigIntegerField(null=True)
    orchestra_contact = models.OneToOneField(
        BillContact,
        on_delete=models.CASCADE,
    )
    first_synced_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default=Status.SYNCED)
    message = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Contact({self.remote_id} <-> {self.orchestra_contact})"

    class Meta:
        unique_together = (("remote_id", "orchestra_contact"),)
