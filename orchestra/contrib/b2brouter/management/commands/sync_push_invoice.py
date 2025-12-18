from django.core.management.base import BaseCommand, CommandError

from orchestra.contrib.b2brouter.api import sync_remote_invoice
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.bills.models import Bill


class Command(BaseCommand):
    help = "Sync and push invoice to B2BRouter by invoice PK"

    def add_arguments(self, parser):
        parser.add_argument(
            "invoice_pk", type=int, help="Primary key of the invoice to sync"
        )

    def handle(self, *args, **options):
        invoice_pk = options["invoice_pk"]

        try:
            bill = Bill.objects.get(pk=invoice_pk)
        except Bill.DoesNotExist:
            raise CommandError(f'Invoice with PK "{invoice_pk}" does not exist.')

        try:
            self.stdout.write(f"Syncing invoice PK {invoice_pk} ({bill.number})...")
            sync_remote_invoice(bill)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully synced invoice PK {invoice_pk}")
            )
        except B2BSyncError as e:
            raise CommandError(f"Failed to sync invoice PK {invoice_pk}: {e}")
