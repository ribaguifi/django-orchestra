from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from orchestra.contrib.domains.helpers import domain_for_validation
from orchestra.contrib.domains.models import Record
from orchestra.contrib.domains.validators import validate_zone


class ValidateZoneMixin:
    # NOTE: adapted code of orchestra.contrib.domains.forms.ValidateZoneMixin
    # but only for one form (instead a admin inline formset)
    def clean(self):
        """ Checks if everything is consistent """
        super(ValidateZoneMixin, self).clean()
        if any(self.errors):
            return

        is_host = self.cleaned_data.get('type') in (Record.TXT, Record.SRV, Record.CNAME)

        domain_names = []
        if self.domain.name:
            domain_names.append(self.domain.name)
        domain_names.extend(getattr(self.domain, 'extra_names', []))
        errors = []
        for name in domain_names:
            if '_' in name and is_host:
                errors.append(ValidationError(
                    _("%s: Hosts can not have underscore character '_', consider providing a SRV, CNAME or TXT record.") % name
                ))

            records = [self.cleaned_data]
            domain = domain_for_validation(self.domain, records)

            try:
                validate_zone(domain.render_zone())
            except ValidationError as error:
                for msg in error:
                    errors.append(
                        ValidationError("%s: %s" % (name, msg))
                    )
        if errors:
            raise ValidationError(errors)
