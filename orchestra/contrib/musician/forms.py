
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from . import api

class LoginForm(AuthenticationForm):

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            orchestra = api.Orchestra(username=username, password=password)

            if orchestra.auth_token is None:
                raise self.get_invalid_login_error()
            else:
                self.username = username
                self.token = orchestra.auth_token
                self.user = orchestra.retrieve_profile()

        return self.cleaned_data


class MailForm(forms.Form):
    name = forms.CharField()
    domain = forms.ChoiceField()
    mailboxes = forms.MultipleChoiceField(required=False)
    forward = forms.EmailField(required=False)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        if self.instance is not None:
            kwargs['initial'] = self.instance.deserialize()

        domains = kwargs.pop('domains')
        mailboxes = kwargs.pop('mailboxes')

        super().__init__(*args, **kwargs)
        self.fields['domain'].choices = [(d.url, d.name) for d in domains]
        self.fields['mailboxes'].choices = [(m.url, m.name) for m in mailboxes]

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('mailboxes') and not cleaned_data.get('forward'):
            raise ValidationError("A mailbox or forward address should be provided.")
        return cleaned_data

    def serialize(self):
        assert hasattr(self, 'cleaned_data')
        serialized_data = {
            "name": self.cleaned_data["name"],
            "domain": {"url": self.cleaned_data["domain"]},
            "mailboxes": [{"url": mbox} for mbox in self.cleaned_data["mailboxes"]],
            "forward": self.cleaned_data["forward"],
        }
        return serialized_data


class MailboxChangePasswordForm(forms.Form):
    error_messages = {
        'password_mismatch': _('The two password fields didn’t match.'),
    }
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def serialize(self):
        assert self.is_valid()
        serialized_data = {
            "password": self.cleaned_data["password2"],
        }
        return serialized_data


class MailboxCreateForm(forms.Form):
    error_messages = {
        'password_mismatch': _('The two password fields didn’t match.'),
    }
    name = forms.CharField()
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )
    addresses = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        addresses = kwargs.pop('addresses')
        super().__init__(*args, **kwargs)
        self.fields['addresses'].choices = [(addr.url, addr.full_address_name) for addr in addresses]

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def serialize(self):
        assert self.is_valid()
        serialized_data = {
            "name": self.cleaned_data["name"],
            "password": self.cleaned_data["password2"],
            "addresses": self.cleaned_data["addresses"],
        }
        return serialized_data


class MailboxUpdateForm(forms.Form):
    addresses = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        if self.instance is not None:
            kwargs['initial'] = self.instance.deserialize()

        addresses = kwargs.pop('addresses')
        super().__init__(*args, **kwargs)
        self.fields['addresses'].choices = [(addr.url, addr.full_address_name) for addr in addresses]

    def serialize(self):
        assert self.is_valid()
        serialized_data = {
            "addresses": self.cleaned_data["addresses"],
        }
        return serialized_data
