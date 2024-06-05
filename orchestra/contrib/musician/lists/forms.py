from django import forms
from django.utils.translation import gettext_lazy as _

from orchestra.contrib.lists.models import List
from orchestra.contrib.domains.models import Domain

class MailingUpdateForm(forms.ModelForm):
    class Meta:
        model = List
        fields = ("is_active", "name", "address_name", "address_domain")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        qs = Domain.objects.filter(account=self.user)
        self.fields['address_domain'].queryset = qs
        self.fields['address_name'].help_text = _("Additional address besides the default <name>@grups.pangea.org")
        self.fields['name'].widget.attrs['readonly'] = True


class MailingCreateForm(forms.ModelForm):
    class Meta:
        model = List
        fields = ("name", "address_name", "address_domain", "admin_email")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        qs = Domain.objects.filter(account=self.user)
        self.fields['address_domain'].queryset = qs
        self.fields['address_name'].help_text = _("Additional address besides the default <name>@grups.pangea.org")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.account = self.user
        if commit:
            super().save(commit=True)
        return instance