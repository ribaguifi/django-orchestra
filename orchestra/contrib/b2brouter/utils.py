from django.core.management.base import CommandError

from orchestra.contrib.bills.models import Bill


def get_invoice_by_identifier(invoice_identifier):
    """Retrieve invoice by PK (integer) or number (string).

    Args:
        invoice_identifier: Primary key (integer) or number (string) of the invoice

    Returns:
        Bill object

    Raises:
        Bill.DoesNotExist: If the invoice is not found
    """
    try:
        invoice_pk = int(invoice_identifier)
        bill = Bill.objects.get(pk=invoice_pk)
    except ValueError:
        bill = Bill.objects.get(number=invoice_identifier)

    return bill
