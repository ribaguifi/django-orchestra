import re

from django.core.management.base import BaseCommand, CommandError

from orchestra.contrib.b2brouter.api import sync_remote_contact
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.bills.models import BillContact


class Command(BaseCommand):
    help = "Sync and push contact to B2BRouter by bill contact PK or VAT"

    @staticmethod
    def normalize_vat(value):
        return re.sub(r"[\s\-.]", "", value.strip().upper())

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--pk", type=int, help="Primary key of the bill contact to sync"
        )
        group.add_argument("--vat", help="VAT number of the bill contact to sync")

    def get_bill_contact(self, contact_pk=None, vat=None):
        if contact_pk is not None:
            try:
                return BillContact.objects.get(pk=contact_pk)
            except BillContact.DoesNotExist:
                raise CommandError(f'Contact with PK "{contact_pk}" does not exist.')

        normalized_vat = self.normalize_vat(vat)
        matches = [
            contact
            for contact in BillContact.objects.select_related("account")
            if self.normalize_vat(contact.vat) == normalized_vat
        ]
        if not matches:
            raise CommandError(f'Contact with VAT "{vat}" does not exist.')
        if len(matches) > 1:
            raise CommandError(
                f'Multiple contacts found with VAT "{vat}". Use --pk instead.'
            )
        return matches[0]

    def handle(self, *args, **options):
        contact_pk = options.get("pk")
        vat = options.get("vat")
        bill_contact = self.get_bill_contact(contact_pk=contact_pk, vat=vat)
        identifier_desc = (
            f"PK {bill_contact.pk}"
            if contact_pk is not None
            else f"VAT {bill_contact.vat}"
        )

        try:
            self.stdout.write(
                f"Syncing contact {identifier_desc} ({bill_contact.get_name()})..."
            )
            sync_remote_contact(bill_contact)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully synced contact {identifier_desc}")
            )
        except B2BSyncError as e:
            raise CommandError(f"Failed to sync contact {identifier_desc}: {e}")
