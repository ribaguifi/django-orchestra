import swagger_client
from django.core.management.base import BaseCommand
from orchestra.contrib.b2brouter import settings
from orchestra.contrib.bills.models import BillContact
from swagger_client.rest import ApiException


class Command(BaseCommand):
    help = "Sync contacts (push local info to remote)."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self.init_api()
        qs = self.retrieve_local_contacts()
        for contact in qs[:1]:
            self.create_remote_contact(contact)

    def retrieve_local_contacts(self):
        # TODO(@slamora): filter only active accounts???
        qs = BillContact.objects.filter(account__is_active=True)
        return qs

    def init_api(self):
        # Configure API key authorization: api_key
        configuration = swagger_client.Configuration()
        configuration.api_key['X-B2B-API-Key'] = settings.B2BROUTER_API_KEY
        configuration.host = settings.B2BROUTER_API_URL

        # create an instance of the API class
        api_instance = swagger_client.ContactsApi(
            swagger_client.ApiClient(configuration))

        self.api = api_instance

    def create_remote_contact(self, contact):
        contact_info = contact.account.contacts.get(email_usages=["BILLING"])
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
                # "province": contact.province  # TODO(@slamora): map provinces???
                # "terms": "custom",    # TODO(@slamora): defaults to custom, which is the desired value?
            }
        }

        try:
            api_response = self.api.create_contact(
                account=settings.B2BROUTER_ACCOUNT_ID, format="json", body=body)
            return api_response
        except ApiException as e:
            print("Exception when calling ContactsApi->create_contact: %s\n" % e)
            return None
