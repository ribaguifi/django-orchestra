import logging
import re
from datetime import date, datetime

from b2brouter_client import ApiErrorException, B2BRouterClient
from b2brouter_client.exceptions import ResourceNotFoundException

from orchestra.contrib.b2brouter import settings
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.b2brouter.models import B2BContact, B2BContactBinding, B2BInvoice
from orchestra.contrib.b2brouter.serializers import BillSerializer
from orchestra.contrib.contacts.models import Contact

logger = logging.getLogger(__name__)

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


def fetch_remote_contacts(api=None, limit=100):
    if api is None:
        api = get_api_client()

    response = []
    offset = 0
    while True:
        try:
            api_response = api.contacts.list(
                account=settings.B2BROUTER_ACCOUNT_ID,
                params={"limit": limit, "offset": offset},
            )
            response.extend(api_response)
            total_count = api_response.meta["total_count"]
            offset += limit
            if offset >= total_count:
                break
        except ApiErrorException as e:
            logger.error("Exception when calling API Contacts->list: %s", e)
            raise

    return response


def vat_key_for_contact(bill_contact):
    normalized_vat = re.sub(r"[\s\-.]", "", bill_contact.vat.strip().upper())
    country = (bill_contact.country or "").strip().upper()
    return f"{country}:{normalized_vat}"


def sync_remote_contact(bill_contact, update=False, client=None):
    vat_key = vat_key_for_contact(bill_contact)
    b2bcontact, _ = B2BContact.objects.get_or_create(vat_key=vat_key)

    binding, _ = B2BContactBinding.objects.get_or_create(
        bill_contact=bill_contact,
        defaults={"b2b_contact": b2bcontact},
    )
    if binding.b2b_contact_id != b2bcontact.id:
        binding.b2b_contact = b2bcontact
        binding.save(update_fields=["b2b_contact"])

    b2bcontact.status = B2BContact.Status.SYNCED
    b2bcontact.message = ""

    # TODO(@slamora): parameter "update" deprecated?
    update = b2bcontact.remote_id is not None

    try:
        contact_info = bill_contact.account.contacts.get(email_usages=["BILLING"])
    except Contact.DoesNotExist:
        b2bcontact.status = B2BContact.Status.ERROR
        b2bcontact.message = (
            f"Missing email contact with usage 'BILLING' for account '{bill_contact.account}'."
            "Please add one or select an existing contact and sync again."
        )
        b2bcontact.save(update_fields=["status", "message", "last_synced_at"])
        raise B2BSyncError(b2bcontact.message)
    except Contact.MultipleObjectsReturned:
        contact_info = bill_contact.account.contacts.filter(
            email_usages=["BILLING"]
        ).first()
        b2bcontact.status = B2BContact.Status.WARNING
        b2bcontact.message = f"Multiple billing contacts found; using the first one: {contact_info.email}"

    billing_email = contact_info.email
    billing_phone = contact_info.phone or contact_info.phone2

    payload = {
        "contact": {
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
        payload["contact"]["bank_account_number"] = paymentsource.data.get("iban")
        payload["contact"]["payment_method"] = PAYMENT_METHODS.get(paymentsource.method)

    if client is None:
        client = get_api_client()
    try:
        if update:
            api_response = client.contacts.update(
                id=b2bcontact.remote_id, params=payload
            )
        else:
            api_response = client.contacts.create(
                account=settings.B2BROUTER_ACCOUNT_ID, params=payload
            )
            b2bcontact.remote_id = api_response.id
    except ApiErrorException as e:
        message = e.body if hasattr(e, "body") else str(e)
        b2bcontact.status = B2BContact.Status.ERROR
        b2bcontact.message = message
        b2bcontact.save(update_fields=["status", "message", "last_synced_at"])
        raise B2BSyncError(
            f"Failed to {'update' if update else 'create'} contact {bill_contact}: {message}"
        )

    b2bcontact.save()
    return b2bcontact.remote_id


def sync_to_remote_invoice(instance):
    """Sync Bill instance to remote B2BRouter as Invoice."""
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
        try:
            response = client.invoices.retrieve(
                id=remote_invoice.remote_id, params={"include": "detailed_lines"}
            )
        except ResourceNotFoundException:
            # Remote invoice was deleted; treat as a new creation
            update = False
            remote_invoice.remote_id = None
        else:
            # clean up current lines on update
            existing_lines = []
            for line in response.lines or []:
                existing_lines.append(
                    {
                        "id": line.id,
                        "_destroy": 1,
                    }
                )

            payload["invoice"]["invoice_lines_attributes"].extend(existing_lines)
            response = client.invoices.update(
                id=remote_invoice.remote_id, params=payload
            )

    # creation or update after detecting remote deletion
    if not update:
        response = client.invoices.create(
            account=settings.B2BROUTER_ACCOUNT_ID, params=payload
        )
        remote_invoice.remote_id = response.id

    remote_invoice.save()

    return remote_invoice.remote_id


def _invoice_delete_current_lines(remote_id):
    """Delete current invoice lines"""
    client = get_api_client()
    response = client.invoices.retrieve(
        id=remote_id, params={"include": "detailed_lines"}
    )
    new_payload = {
        "send_after_import": False,
        "ack": False,
        "invoice": {},
    }
    new_lines = []
    for line in response.lines or []:
        new_lines.append(
            {
                "id": line.id,
                "_destroy": 1,
            }
        )
    new_payload["invoice"]["invoice_lines_attributes"] = new_lines
    response = client.invoices.update(id=remote_id, params=new_payload)


def _normalize_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def sync_from_remote_invoice(instance):
    """Pull remote Invoice data into local Bill instance."""
    try:
        b2binvoice = instance.b2binvoice
    except B2BInvoice.DoesNotExist:
        bill_id = instance.number or instance.pk
        raise B2BSyncError(f"Bill {bill_id} has no linked B2BInvoice.")
    client = get_api_client()
    try:
        response = client.invoices.retrieve(id=b2binvoice.remote_id)
    except ApiErrorException as e:
        message = e.body if hasattr(e, "body") else str(e)
        raise B2BSyncError(f"Failed to pull invoice {b2binvoice.remote_id}: {message}")

    issue_date = _normalize_date(getattr(response, "issue_date", None))
    due_date = _normalize_date(getattr(response, "due_date", None))
    remote_status = getattr(response, "status", None)
    remote_state = getattr(response, "state", None)
    is_open, is_sent = instance.flags_from_remote_status(
        remote_status=remote_status,
        remote_state=remote_state,
    )

    instance.series_code = response.series_code
    instance.number = response.number
    instance.is_open = is_open
    instance.is_sent = is_sent
    # Keep Bill.date as the legal issued date from B2B. If remote omits it,
    # preserve local value and only initialize from created_on when still empty.
    instance.date = issue_date or instance.date or instance.created_on
    instance.due_on = due_date or instance.due_on
    instance.closed_on = issue_date if not is_open else None
    instance.state = remote_state
    instance.comments = getattr(response, "extra_info", "")
    instance.save()
