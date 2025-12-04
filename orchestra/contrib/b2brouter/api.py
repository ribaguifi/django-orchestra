from b2brouter_client import ApiErrorException, B2BRouterClient

from orchestra.contrib.b2brouter import settings
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.b2brouter.models import B2BContact, B2BInvoice
from orchestra.contrib.b2brouter.serializers import BillSerializer
from orchestra.contrib.contacts.models import Contact

# Payment methods mapping Orchestra <-> B2BRouter
PAYMENT_METHODS = {
    "SEPADirectDebit": 59,
}


def get_api_client():
    client = B2BRouterClient(
        api_key=settings.B2BROUTER_API_KEY,
        api_base=settings.B2BROUTER_API_URL,
    )
    return client


def sync_remote_contact(bill_contact, update=False):
    #    bill_contact = b2bcontact.orchestra_contact
    try:
        b2bcontact = bill_contact.b2bcontact
        b2bcontact.status = B2BContact.Status.SYNCED
        b2bcontact.message = ""
    except B2BContact.DoesNotExist:
        b2bcontact = B2BContact(orchestra_contact=bill_contact)

    # TODO(@slamora): parameter "update" deprecated?
    update = b2bcontact.remote_id is not None

    try:
        contact_info = bill_contact.account.contacts.get(email_usages=["BILLING"])
    except Contact.DoesNotExist:
        b2bcontact.status = B2BContact.Status.ERROR
        b2bcontact.message = (
            f"No billing contact found for account '{bill_contact.account}'."
        )
        raise B2BSyncError(b2bcontact.message)
    except Contact.MultipleObjectsReturned:
        contact_info = bill_contact.account.contacts.filter(
            email_usages=["BILLING"]
        ).first()
        b2bcontact.status = B2BContact.Status.WARNING
        b2bcontact.message = f"Multiple billing contacts found; using the first one: {contact_info.email}"

    billing_email = contact_info.email
    billing_phone = contact_info.phone or contact_info.phone2

    body = {
        "client": {
            "language": bill_contact.account.language,
            "is_client": True,
            "is_provider": False,
            "tin_value": bill_contact.vat,
            "name": bill_contact.get_name(),
            "address": bill_contact.address,
            "city": bill_contact.city,
            "postalcode": bill_contact.zipcode,
            "country": bill_contact.country,
            "email": billing_email,
            "phone": billing_phone,
            "terms": "60",
        }
    }

    # Include payment info if available
    # TODO(@slamora): optimize query
    paymentsource = (
        bill_contact.account.paymentsources.filter(
            method__in=PAYMENT_METHODS.keys(), is_active=True
        )
        .order_by("-pk")
        .first()
    )
    if paymentsource:
        body["client"]["bank_account_number"] = paymentsource.data.get("iban")
        body["client"]["payment_method"] = PAYMENT_METHODS.get(paymentsource.method)

    client = get_api_client()
    try:
        if update:
            api_response = client.contacts.update(id=b2bcontact.remote_id, body=body)
        else:
            api_response = client.contacts.create(
                account=settings.B2BROUTER_ACCOUNT_ID, body=body
            )
            b2bcontact.remote_id = api_response.id
    except ApiErrorException as e:
        message = e.body if hasattr(e, "body") else str(e)
        b2bcontact.status = B2BContact.Status.ERROR
        b2bcontact.message = message
        raise B2BSyncError(
            f"Failed to {'update' if update else 'create'} contact {bill_contact}: {message}"
        )

    b2bcontact.save()
    return b2bcontact.remote_id


def sync_remote_invoice(instance):
    try:
        remote_invoice = instance.b2binvoice
        update = remote_invoice.remote_id is not None
    except B2BInvoice.DoesNotExist:
        remote_invoice = B2BInvoice(orchestra_bill=instance)
        update = False

    # print(f"Syncing remote invoice for Bill ID {instance.id}, update={update}")
    invoice_data = BillSerializer(instance).data
    payload = {
        "send_after_import": False,
        "ack": False,
        "invoice": invoice_data,
    }

    client = get_api_client()
    if update:
        response = client.invoices.update(id=remote_invoice.remote_id, body=payload)
    else:
        response = client.invoices.create(
            account=settings.B2BROUTER_ACCOUNT_ID, body=payload
        )
        remote_invoice.remote_id = response.id

    remote_invoice.save()


def pull_from_remote_invoice(instance):
    b2binvoice = instance.b2binvoice
    client = get_api_client()
    try:
        response = client.invoices.retrieve(id=b2binvoice.remote_id)
    except ApiErrorException as e:
        message = e.body if hasattr(e, "body") else str(e)
        raise B2BSyncError(f"Failed to pull invoice {b2binvoice.remote_id}: {message}")

    # TODO(@slamora): update the local Bill instance based on the response data
    # For example:
    # bill = b2binvoice.orchestra_bill
    # bill.status = response.status
    # bill.total_amount = response.total_amount
    # bill.save()

    print(f"Pulled remote invoice data for Bill ID {instance.id}: {response}")
