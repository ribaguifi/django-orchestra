from orchestra.contrib.b2brouter import api
from orchestra.contrib.b2brouter.models import B2BContact


# TODO serialize Bill to b2brouter invoice format
class BillSerializer(object):
    # TODO(@slamora): complete series & vat_percent mapping
    SERIES_MAPPING = {
        "FEE": "S",
    }
    SERIES_MAPPING_DEFAULT = "F"

    SEPA_DIRECT_DEBIT_PAYMENT_METHOD = 59  # UBL: 59

    def __init__(self, bill):
        self.instance = bill

    @property
    def data(self):
        if not hasattr(self, "_data"):
            self._data = self.to_representation()
        return self._data

    def to_representation(self):
        instance = self.instance

        return {
            "type": "IssuedInvoice",
            "series_code": self.get_series(),
            "number": instance.get_number_without_series(),
            "contact_id": self.get_contact_id(),
            # TODO(@slamora): is this the desired date?
            "date": instance.created_on.isoformat(),
            "due_date": instance.get_due_date(),
            "payment_method": self.SEPA_DIRECT_DEBIT_PAYMENT_METHOD,
            "invoice_lines_attributes": self.get_lines_attributes(),
        }

    def get_contact_id(self):
        # TODO: Implement contact ID retrieval logic
        self.instance.buyer
        try:
            return self.instance.buyer.b2bcontact.remote_id
        except B2BContact.DoesNotExist:
            # TODO(@slamora): Handle missing B2BContact --> create or error?
            remote_id = api.sync_remote_contact(self.instance.buyer, update=False)
            return remote_id

    def get_series(self):
        return self.SERIES_MAPPING.get(self.instance.type, self.SERIES_MAPPING_DEFAULT)

    def get_vat_percent(self):
        if self.instance.type == "FEE":
            return 0
        return 21

    def get_lines_attributes(self):
        lines = []
        for index, item in enumerate(self.instance.lines.all()):
            line = {
                "position": index + 1,
                "quantity": str(item.quantity),
                "price": str(item.rate),
                "description": item.description,
                # "taxes_attributes": str(item.tax),
                "invoicing_period_start": item.order_billed_on.isoformat() if item.order_billed_on else None,
                "invoicing_period_end": item.order_billed_until.isoformat() if item.order_billed_until else None,
            }
            lines.append(line)
        return lines
        return lines
