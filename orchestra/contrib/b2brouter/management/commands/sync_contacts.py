import swagger_client
from django.core.management.base import BaseCommand
from orchestra.contrib.b2brouter import settings
from orchestra.contrib.bills.models import BillContact
from orchestra.contrib.contacts.models import Contact
from swagger_client.rest import ApiException


class Command(BaseCommand):
    help = "Sync contacts (push local info to remote)."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self.init_api()
        self.remote_contacts = self.fetch_remote_contacts()

        qs = self.retrieve_local_contacts()
        for contact in qs:
            contact.taxcode = f"{contact.country}{contact.vat}"
            print(contact.taxcode)
            update = contact.taxcode in self.remote_contacts
            self.sync_remote_contact(contact, update=update)

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

    def sync_remote_contact(self, contact, update=False):
        try:
            contact_info = contact.account.contacts.get(email_usages=["BILLING"])
        except Contact.DoesNotExist:
            print(f"  No billing contact found for account {contact.account}. Skipping.")
            return None
        except Contact.MultipleObjectsReturned:
            print(f"  Multiple billing contacts found for account {contact.account}. Using the first one.")
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
                # "terms": "custom",    # TODO(@slamora): defaults to custom, which is the desired value?
            }
        }

        if update:
            contact_id = self.remote_contacts[contact.taxcode].id
            try:
                api_response = self.api.put_contact(id=contact_id, format="json", body=body)
                return api_response
            except ApiException as e:
                print("Exception when calling ContactsApi->update_contact: %s\n" % e)
                return None
        else:
            try:
                api_response = self.api.create_contact(account=settings.B2BROUTER_ACCOUNT_ID, format="json", body=body)
                return api_response
            except ApiException as e:
                print("Exception when calling ContactsApi->create_contact: %s\n" % e)
                return None

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
