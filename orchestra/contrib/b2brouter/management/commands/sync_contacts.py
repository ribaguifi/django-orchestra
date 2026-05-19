import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Q

from orchestra.contrib.b2brouter.api import (
    fetch_remote_contacts,
    get_api_client,
    sync_remote_contact,
    vat_key_for_contact,
)
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.b2brouter.models import B2BContact, B2BContactBinding
from orchestra.contrib.bills.models import BillContact


def taxcode(contact):
    """
    Generate a tax code with country prefix and zero-padded numeric part.
    Handles formats with letters both before and after the numeric sequence.
    """
    normalized_vat = contact.vat.strip().upper().replace("-", "")
    normalized_vat = re.sub(r"[\s\-.]", "", normalized_vat)

    # Extract parts: optional leading letters, digits, optional trailing letters
    match = re.match(r"([A-Z]*)(\d+)([A-Z]*)", normalized_vat)
    if not match:
        # raise ValueError(f"Invalid VAT format: {contact.vat}")
        return normalized_vat

    prefix, numeric, suffix = match.groups()
    tax_code = f"{contact.country.upper()}{prefix}{numeric}{suffix}"

    return tax_code


class Command(BaseCommand):
    help = "Sync contacts (push local info to remote)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Sync all contacts, including those already synced successfully.",
        )

    def set_options(self, **options):
        self.verbosity = options.get("verbosity", 1)
        self.sync_all = options.get("all", False)

    def handle(self, *args, **options):
        self.set_options(**options)
        self.api = get_api_client()

        response = fetch_remote_contacts(self.api, limit=500)
        self.remote_contacts = {c.tin_value: c for c in response if c.tin_value}

        qs = self.retrieve_local_contacts().select_related("account")
        all_contacts = list(qs)
        inconsistent_duplicates = self.find_inconsistent_duplicate_vats(all_contacts)
        self.mark_inconsistent_duplicates(inconsistent_duplicates)

        if not self.sync_all:
            qs = qs.filter(
                Q(
                    b2b_binding__b2b_contact__status__in=[
                        B2BContact.Status.PENDING,
                        B2BContact.Status.ERROR,
                    ]
                )
                | Q(b2b_binding__isnull=True)
            ).distinct()

        updated_count = 0
        created_count = 0
        failed_count = 0
        skipped_inconsistent_count = 0
        skipped_duplicate_count = 0
        synced_vat_keys = set()

        for contact in qs:
            vat_key = vat_key_for_contact(contact)

            if vat_key in inconsistent_duplicates:
                skipped_inconsistent_count += 1
                if self.verbosity >= 1:
                    self.stderr.write(
                        f"  Skipping contact {contact.vat}: duplicated VAT has inconsistent billing data."
                    )
                continue

            if vat_key in synced_vat_keys:
                self.get_or_create_canonical_contact(contact)
                skipped_duplicate_count += 1
                if self.verbosity >= 2:
                    self.stdout.write(
                        f"Skipping contact {contact.vat}: already synced another BillContact with same VAT."
                    )
                continue

            b2bcontact = self.get_or_create_canonical_contact(contact)
            update = b2bcontact.remote_id is not None

            # Sync the contact
            try:
                if self.verbosity >= 1:
                    self.stdout.write(
                        f"Syncing contact {contact.vat}...{b2bcontact.remote_id or ''}: {'update' if update else 'create'}"
                    )
                sync_remote_contact(contact, update=update, client=self.api)
                updated_count += int(update)
                created_count += int(not update)
                synced_vat_keys.add(vat_key)
            except B2BSyncError as e:
                failed_count += 1
                message = str(e)
                if self.verbosity >= 1:
                    self.stderr.write(
                        f"  Failed to sync contact {contact.vat}: {message}"
                    )

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS("Contacts sync completed."))
            self.stdout.write(f"Updated contacts: {updated_count}")
            self.stdout.write(f"Created contacts: {created_count}")
            self.stdout.write(f"Failed contacts: {failed_count}")
            self.stdout.write(
                f"Skipped contacts (inconsistent duplicate VAT): {skipped_inconsistent_count}"
            )
            self.stdout.write(
                f"Skipped contacts (already synced duplicate VAT): {skipped_duplicate_count}"
            )
            self.stdout.write(
                f"Total processed contacts: {updated_count + created_count + failed_count + skipped_inconsistent_count + skipped_duplicate_count}"
            )

    def retrieve_local_contacts(self):
        # Exclude FRIENDS because they are neither billed
        # also Pangea uses this accounts for internal purposes
        qs = BillContact.objects.filter(account__is_active=True).exclude(
            account__type="FRIEND"
        )
        return qs

    def get_or_create_canonical_contact(self, contact):
        vat_key = vat_key_for_contact(contact)
        b2bcontact, _ = B2BContact.objects.get_or_create(vat_key=vat_key)

        contact_taxcode = taxcode(contact)
        if not b2bcontact.remote_id and contact_taxcode in self.remote_contacts:
            b2bcontact.remote_id = self.remote_contacts[contact_taxcode].id
            b2bcontact.save(update_fields=["remote_id"])

        binding, _ = B2BContactBinding.objects.get_or_create(
            bill_contact=contact,
            defaults={"b2b_contact": b2bcontact},
        )
        if binding.b2b_contact_id != b2bcontact.id:
            binding.b2b_contact = b2bcontact
            binding.save(update_fields=["b2b_contact"])

        return b2bcontact

    @staticmethod
    def billing_data_signature(contact):
        return (
            (contact.address or "").strip(),
            (contact.city or "").strip(),
            (contact.zipcode or "").strip(),
            (contact.country or "").strip().upper(),
        )

    def find_inconsistent_duplicate_vats(self, contacts):
        contacts_by_vat = defaultdict(list)
        for contact in contacts:
            contacts_by_vat[vat_key_for_contact(contact)].append(contact)

        inconsistent = {}
        for vat_key, vat_contacts in contacts_by_vat.items():
            if len(vat_contacts) < 2:
                continue

            signatures = {
                self.billing_data_signature(contact) for contact in vat_contacts
            }
            if len(signatures) > 1:
                inconsistent[vat_key] = vat_contacts

        return inconsistent

    def mark_inconsistent_duplicates(self, inconsistent_duplicates):
        for vat_key, contacts in inconsistent_duplicates.items():
            b2bcontact, _ = B2BContact.objects.get_or_create(vat_key=vat_key)
            contact_ids = sorted(contact.pk for contact in contacts)
            b2bcontact.status = B2BContact.Status.WARNING
            b2bcontact.message = (
                "Inconsistent billing data for duplicated VAT. "
                f"Review BillContact IDs: {contact_ids}."
            )
            b2bcontact.save(update_fields=["status", "message", "last_synced_at"])

            for contact in contacts:
                B2BContactBinding.objects.update_or_create(
                    bill_contact=contact,
                    defaults={"b2b_contact": b2bcontact},
                )
