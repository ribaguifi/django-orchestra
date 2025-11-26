from django.db.models.signals import post_save
from django.dispatch import receiver
from orchestra.contrib.b2brouter import settings
from orchestra.contrib.b2brouter.api import get_invoice_api_instance
from orchestra.contrib.b2brouter.management.commands.sync_contacts import (
    Command as SyncCommand,
)
from orchestra.contrib.b2brouter.models import B2BContact, B2BInvoice
from orchestra.contrib.b2brouter.serializers import BillSerializer


@receiver(post_save, sender="bills.BillContact")
def bill_contact_saved(sender, instance, **kwargs):
    created = kwargs.get("created", False)
    if created:
        b2bcontact = B2BContact(orchestra_contact=instance)
        update = False
    else:
        try:
            b2bcontact = instance.b2bcontact
            update = b2bcontact.remote_id is not None
        except B2BContact.DoesNotExist:
            b2bcontact = B2BContact(orchestra_contact=instance)
            update = False

    cmd = SyncCommand()
    cmd.init_api()
    cmd.sync_remote_contact(b2bcontact, update=update)


# TODO(@slamora):
# Bill type mapping
# - Handle bill.number (to match remote system format if needed)
# - Serialize line items
# - Taxes handling
# - Status changes??? Or it will be managed only remotely?


@receiver(post_save, sender="bills.Bill")
def bill_saved(sender, instance, **kwargs):
    print(f"Bill saved: {instance}")
    # Implement any necessary synchronization logic for Bill here
    try:
        remote = instance.b2binvoice
        update = remote.remote_id is not None
    except B2BInvoice.DoesNotExist:
        remote = B2BInvoice(orchestra_bill=instance)
        update = False

    # TODO(@slamora): post_save Bill is triggered before lines are saved
    sync_remote_invoice(instance, remote, update)


def sync_remote_invoice(instance, remote_invoice, update):

    print(f"Syncing remote invoice for Bill ID {instance.id}, update={update}")

    invoice_data = BillSerializer(instance).data
    payload = {
        "send_after_import": False,
        "ack": False,
        "invoice": invoice_data,
    }

    api_instance = get_invoice_api_instance()
    if update:
        response = api_instance.put_invoice(
            format="json", id=remote_invoice.remote_id, body=payload
        )
    else:
        response = api_instance.create_invoice(
            account=settings.B2BROUTER_ACCOUNT_ID, format="json", body=payload
        )
        remote_invoice.remote_id = response.id

    remote_invoice.save()
