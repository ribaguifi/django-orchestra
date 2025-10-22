import re
import swagger_client
from django.core.management.base import BaseCommand
from orchestra.contrib.b2brouter import settings
from orchestra.contrib.b2brouter.models import B2BContact
from orchestra.contrib.bills.models import BillContact
from orchestra.contrib.contacts.models import Contact
from swagger_client.rest import ApiException


def taxcode(contact):
    """
    Generate a tax code with country prefix and zero-padded numeric part.
    Handles formats with letters both before and after the numeric sequence.
    """
    normalized_vat = contact.vat.strip().upper().replace("-", "")
    normalized_vat = re.sub(r"[\s\-.]", "", normalized_vat)

    # Extract parts: optional leading letters, digits, optional trailing letters
    match = re.match(r'([A-Z]*)(\d+)([A-Z]*)', normalized_vat)
    if not match:
        raise ValueError(f"Invalid VAT format: {contact.vat}")
        # return normalized_vat

    prefix, numeric, suffix = match.groups()
    padded_numeric = numeric.zfill(8)
    tax_code = f"{contact.country.upper()}{prefix}{padded_numeric}{suffix}"

    return tax_code

class Command(BaseCommand):
    help = "Sync contacts (push local info to remote)."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self.init_api()
        self.remote_contacts = self.fetch_remote_contacts()

        qs = self.retrieve_local_contacts()
        qs = qs.select_related("b2bcontact")

        updated_count = 0
        created_count = 0
        failed_count = 0

        for contact in qs:
            status = B2BContact.Status.SYNCED
            message = ""
            # Check if the contact is already synced
            try:
                update = contact.b2bcontact is not None
                remote_id = contact.b2bcontact.remote_id
                if remote_id is None:
                    raise B2BContact.DoesNotExist()
            except B2BContact.DoesNotExist:
                if taxcode(contact) in self.remote_contacts:
                    remote_id = self.remote_contacts[taxcode(contact)].id
                    update = True
                else:
                    update = False
                    remote_id = None

            # Sync the contact
            try:
                self.stdout.write(f"Syncing contact {contact}...{remote_id or ''}: {'update' if update else 'create'}")
                remote_id = self.sync_remote_contact(contact, remote_id=remote_id, update=update)
                updated_count += int(update)
                created_count += int(not update)
                # TODO(@slamora): handle warning --> multiple contacts
            except ApiException as e:
                self.stdout.write(f"  Failed to sync contact {contact}: {e}")
                failed_count += 1
                status = B2BContact.Status.ERROR
                message = e.body if hasattr(e, "body") else str(e)

            # Link local contact to remote contact
            # TODO(@slamora): refactor, create or retrieve B2BContact first to allow storing sync errors or warnings
            try:
                B2BContact.objects.update_or_create(orchestra_contact=contact, defaults={
                    "remote_id": remote_id,
                    "status": status,
                    "message": message
                })
            except Exception as e:
                self.stdout.write(f"  Failed to link contact {contact} to remote ID {remote_id}: {e}")
                continue

        self.stdout.write(self.style.SUCCESS("Contacts sync completed."))
        self.stdout.write(f"Updated contacts: {updated_count}")
        self.stdout.write(f"Created contacts: {created_count}")
        self.stdout.write(f"Failed contacts: {failed_count}")
        self.stdout.write(f"Total processed contacts: {updated_count + created_count + failed_count}")

    def retrieve_local_contacts(self):
        # TODO(@slamora): filter only active accounts???
        qs = BillContact.objects.filter(account__is_active=True)
        return qs

    def init_api(self):
        # Configure API key authorization: api_key
        configuration = swagger_client.Configuration()
        configuration.api_key["X-B2B-API-Key"] = settings.B2BROUTER_API_KEY
        configuration.host = settings.B2BROUTER_API_URL

        # create an instance of the API class
        api_instance = swagger_client.ContactsApi(swagger_client.ApiClient(configuration))

        self.api = api_instance

    def sync_remote_contact(self, contact, remote_id, update=False):
        try:
            contact_info = contact.account.contacts.get(email_usages=["BILLING"])
        except Contact.DoesNotExist:
            raise ApiException(f"No billing contact found for account {contact.account}. Skipping.")
        except Contact.MultipleObjectsReturned:
            self.stdout.write(f"Multiple billing contacts found for account {contact.account}. Using the first one.")
            contact_info = contact.account.contacts.filter(email_usages=["BILLING"]).first()

        billing_email = contact_info.email
        billing_phone = contact_info.phone or contact_info.phone2

        body = {
            "client": {
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

        if update:
            try:
                api_response = self.api.put_contact(id=remote_id, format="json", body=body)
                return remote_id
            except ApiException as e:
                # print("Exception when calling ContactsApi->update_contact: %s\n" % e)
                raise
        else:
            try:
                api_response = self.api.create_contact(account=settings.B2BROUTER_ACCOUNT_ID, format="json", body=body)
                return api_response.id
            except ApiException as e:
                # print("Exception when calling ContactsApi->create_contact: %s\n" % e)
                # # TODO(@slamora): handle specific errors (e.g., duplicated TIN)
                # # {"errors":["Tax Identifier Number Duplicated"]}
                # if e.status == 422 and "Tax Identifier Number Duplicated" in str(e.body):
                #     print(f"  Contact with TIN {contact.vat} already exists remotely. Skipping.")
                #     # TODO(@slamora): fetch the remote contact ID and link it?
                raise

    def fetch_remote_contacts(self):
        response = []
        offset = 0
        limit = 25
        while True:
            try:
                api_response = self.api.get_contacts(
                    account=settings.B2BROUTER_ACCOUNT_ID,
                    format="json",
                    limit=limit,
                    offset=offset,
                )
                response.extend(api_response.clients)
                total_count = api_response.total_count
                offset += limit
                if offset >= total_count:
                    break
            except ApiException as e:
                print("Exception when calling ContactsApi->get_contacts: %s\n" % e)
                raise

        return {c.taxcode: c for c in response if c.taxcode}
