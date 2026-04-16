import re

from django.core.management.base import BaseCommand

from b2brouter_client import ApiErrorException

from orchestra.contrib.b2brouter import settings
from orchestra.contrib.b2brouter.api import fetch_remote_contacts, get_api_client
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.b2brouter.models import B2BContact
from orchestra.contrib.bills.models import BillContact
from orchestra.contrib.contacts.models import Contact


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

    # Payment methods mapping Orchestra <-> B2BRouter
    PAYMENT_METHODS = {
        "SEPADirectDebit": 59,
    }

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

        qs = self.retrieve_local_contacts()
        qs = qs.select_related("b2bcontact")

        if not self.sync_all:
            qs = qs.filter(
                b2bcontact__status__in=[
                    B2BContact.Status.PENDING,
                    B2BContact.Status.ERROR,
                ]
            ) | qs.filter(b2bcontact__isnull=True)

        updated_count = 0
        created_count = 0
        failed_count = 0

        for contact in qs:
            update = False

            try:
                b2bcontact = contact.b2bcontact
                b2bcontact.status = B2BContact.Status.SYNCED
                b2bcontact.message = ""
            except B2BContact.DoesNotExist:
                b2bcontact = B2BContact(orchestra_contact=contact)

            # Check if the contact is already synced
            if b2bcontact.remote_id:
                # remote_id = b2bcontact.remote_id
                update = True
            else:
                contact_taxcode = taxcode(contact)
                if contact_taxcode in self.remote_contacts:
                    b2bcontact.remote_id = self.remote_contacts[contact_taxcode].id
                    update = True

            # Sync the contact
            try:
                if self.verbosity >= 1:
                    self.stdout.write(
                        f"Syncing contact {contact}...{b2bcontact.remote_id or ''}: {'update' if update else 'create'}"
                    )
                self.sync_remote_contact(b2bcontact, update=update)
                updated_count += int(update)
                created_count += int(not update)
            except B2BSyncError as e:
                failed_count += 1
                message = str(e)
                if self.verbosity >= 1:
                    self.stderr.write(f"  Failed to sync contact {contact}: {message}")

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS("Contacts sync completed."))
            self.stdout.write(f"Updated contacts: {updated_count}")
            self.stdout.write(f"Created contacts: {created_count}")
            self.stdout.write(f"Failed contacts: {failed_count}")
            self.stdout.write(
                f"Total processed contacts: {updated_count + created_count + failed_count}"
            )

    def retrieve_local_contacts(self):
        # TODO(@slamora): filter only active accounts???
        qs = BillContact.objects.filter(account__is_active=True)
        return qs

    def sync_remote_contact(self, b2bcontact, update=False):
        contact = b2bcontact.orchestra_contact

        try:
            contact_info = contact.account.contacts.get(email_usages=["BILLING"])
        except Contact.DoesNotExist:
            b2bcontact.status = B2BContact.Status.ERROR
            b2bcontact.message = (
                f"No billing contact found for account '{contact.account}'."
            )
            raise B2BSyncError(b2bcontact.message)
        except Contact.MultipleObjectsReturned:
            contact_info = contact.account.contacts.filter(
                email_usages=["BILLING"]
            ).first()
            b2bcontact.status = B2BContact.Status.WARNING
            b2bcontact.message = f"Multiple billing contacts found; using the first one: {contact_info.email}"

        billing_email = contact_info.email
        billing_phone = contact_info.phone or contact_info.phone2

        body = {
            "contact": {
                "language": contact.account.language,
                "is_client": True,
                "is_provider": False,
                "tin_value": contact.vat,
                "name": contact.get_name(),
                "address": contact.address,
                "city": contact.city,
                "postalcode": contact.zipcode,
                "country": contact.country,
                "email": billing_email,
                "phone": billing_phone,
                "terms": "60",
            }
        }

        # Include payment info if available
        # TODO(@slamora): optimize query
        paymentsource = (
            contact.account.paymentsources.filter(
                method__in=self.PAYMENT_METHODS.keys(), is_active=True
            )
            .order_by("-pk")
            .first()
        )
        if paymentsource:
            body["contact"]["bank_account_number"] = paymentsource.data.get("iban")
            body["contact"]["payment_method"] = self.PAYMENT_METHODS.get(
                paymentsource.method
            )

        try:
            if update:
                api_response = self.api.contacts.update(
                    id=b2bcontact.remote_id, params=body
                )
            else:
                api_response = self.api.contacts.create(
                    account=settings.B2BROUTER_ACCOUNT_ID, params=body
                )
                b2bcontact.remote_id = api_response.id
        except ApiErrorException as e:
            message = e.body if hasattr(e, "body") else str(e)
            b2bcontact.status = B2BContact.Status.ERROR
            b2bcontact.message = message
            raise B2BSyncError(
                f"Failed to {'update' if update else 'create'} contact {contact}: {message}"
            )

        b2bcontact.save()
