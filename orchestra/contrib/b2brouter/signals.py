import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from orchestra.contrib.b2brouter.api import sync_remote_contact, sync_to_remote_invoice
from orchestra.contrib.b2brouter.exceptions import B2BSyncError

logger = logging.getLogger(__name__)


@receiver(post_save, sender="bills.BillContact")
def bill_contact_saved(sender, instance, **kwargs):
    """Sync contact changes to remote B2BRouter when BillContact is saved."""
    try:
        sync_remote_contact(instance)
    except B2BSyncError as e:
        logger.error(
            "Failed to sync contact %s to remote: %s",
            instance,
            str(e),
        )
    except Exception as e:
        logger.exception(
            "Unexpected error syncing contact %s to remote: %s",
            instance,
            str(e),
        )
