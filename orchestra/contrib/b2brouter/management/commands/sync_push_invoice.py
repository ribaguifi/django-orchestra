from django.core.management.base import BaseCommand, CommandError

from orchestra.contrib.b2brouter.api import sync_to_remote_invoice
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.b2brouter.utils import get_invoice_by_identifier
from orchestra.contrib.bills.models import Bill


class Command(BaseCommand):
    help = "Sync to remote (push) invoice to B2BRouter by invoice PK or number"

    def add_arguments(self, parser):
        parser.add_argument(
            "invoice_identifier",
            help="Primary key (integer) or number (string) of the invoice to sync",
        )

    def handle(self, *args, **options):
        invoice_identifier = options["invoice_identifier"]

        try:
            bill = get_invoice_by_identifier(invoice_identifier)
        except Bill.DoesNotExist:
            raise CommandError(
                f'Invoice with number "{invoice_identifier}" does not exist.'
            )

        identifier_desc = f"PK {bill.pk} ({bill.number})"
        try:
            self.stdout.write(f"Syncing invoice {identifier_desc}...")
            sync_to_remote_invoice(bill)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully synced invoice {identifier_desc}")
            )
        except B2BSyncError as e:
            raise CommandError(f"Failed to sync invoice {identifier_desc}: {e}")
