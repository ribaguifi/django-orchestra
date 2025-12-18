from orchestra.contrib.b2brouter import api
from orchestra.contrib.b2brouter.models import B2BContact


class BillLineSerializer(object):
    def __init__(self, bill_line, position):
        self.instance = bill_line
        self.instance.position = position

    @property
    def data(self):
        if not hasattr(self, "_data"):
            self._data = self.to_representation()
        return self._data

    def to_representation(self):
        instance = self.instance
        data = {
            "position": instance.position,
            "quantity": str(instance.quantity),
            "price": str(instance.rate),
            "description": instance.description,
            # TODO(@slamora): serialize 'taxes_attributes'
            # "taxes_attributes": str(instance.tax),
            "invoicing_period_start": (
                instance.start_on.isoformat() if instance.start_on else None
            ),
            "invoicing_period_end": (
                instance.end_on.isoformat() if instance.end_on else None
            ),
        }

        # handle discount & charge information
        discount_charge_data = self.get_discount_and_charge()
        data.update(discount_charge_data)

        return data

    def get_discount_and_charge(self):
        discount_amount = 0
        discount_description = []
        charge_amount = 0
        charge_description = []

        for subline in self.instance.sublines.all():
            is_discount = subline.total < 0
            if is_discount:
                discount_amount += subline.total
                discount_description.append(
                    f"{subline.description} ({subline.get_type_display()})"
                )
            elif subline.total > 0:
                charge_amount += subline.total
                charge_description.append(f"{subline.description} ({subline.type})")

        data = {}
        if discount_amount != 0:
            # discount_amount is negative in orchestra but positive in B2BRouter API
            data["discount_amount"] = str(-discount_amount)
            data["discount_percent"] = None
            data["discount_text"] = ", ".join(discount_description)

        if charge_amount != 0:
            data["charge_amount"] = str(charge_amount)
            data["charge_percent"] = None
            data["charge_reason"] = ", ".join(charge_description)

        return data


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
            "date": instance.created_on.isoformat() if instance.created_on else None,
            "due_date": (
                instance.get_due_date().isoformat() if instance.get_due_date() else None
            ),
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
            line = BillLineSerializer(item, position=index + 1).data
            lines.append(line)
        return lines
