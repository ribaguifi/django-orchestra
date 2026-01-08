from django.core.management.base import BaseCommand, CommandError

from orchestra.contrib.b2brouter.api import sync_remote_invoice
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.bills.models import Bill


class Command(BaseCommand):
    help = "Sync and push invoice to B2BRouter by invoice PK or number"

    def add_arguments(self, parser):
        parser.add_argument(
            "invoice_identifier",
            help="Primary key (integer) or number (string) of the invoice to sync",
        )

    def handle(self, *args, **options):
        invoice_identifier = options["invoice_identifier"]

        bill = self.get_invoice(invoice_identifier)

        identifier_desc = f"PK {bill.pk} ({bill.number})"
        try:
            self.stdout.write(f"Syncing invoice {identifier_desc}...")
            sync_remote_invoice(bill)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully synced invoice {identifier_desc}")
            )
        except B2BSyncError as e:
            raise CommandError(f"Failed to sync invoice {identifier_desc}: {e}")

    def get_invoice(self, invoice_identifier):
        """Retrieve invoice by PK (integer) or number (string).

        Returns:
            Bill object
        """
        # determine if it's a PK (integer) or number (string)
        try:
            invoice_pk = int(invoice_identifier)
            bill = Bill.objects.get(pk=invoice_pk)
        except ValueError:
            try:
                bill = Bill.objects.get(number=invoice_identifier)
            except Bill.DoesNotExist:
                raise CommandError(
                    f'Invoice with number "{invoice_identifier}" does not exist.'
                )
        except Bill.DoesNotExist:
            raise CommandError(
                f'Invoice with PK "{invoice_identifier}" does not exist.'
            )

        return bill
