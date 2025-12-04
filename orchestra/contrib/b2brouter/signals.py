from django.db.models.signals import post_save
from django.dispatch import receiver

from orchestra.contrib.b2brouter.api import sync_remote_invoice
from orchestra.contrib.b2brouter.management.commands.sync_contacts import (
    Command as SyncCommand,
)
from orchestra.contrib.b2brouter.models import B2BContact


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
    # TODO(@slamora): post_save Bill is triggered before lines are saved
    sync_remote_invoice(instance)
