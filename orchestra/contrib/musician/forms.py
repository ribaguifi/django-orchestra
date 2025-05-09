from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from orchestra.utils.python import random_ascii
from django.forms.widgets import HiddenInput

from django.contrib.auth.hashers import make_password

from orchestra.forms.widgets import SpanWidget
from orchestra.forms import widgets
from django.utils.safestring import mark_safe

from orchestra.contrib.domains.models import Domain, Record
from orchestra.contrib.mailboxes.models import Address, Mailbox
from orchestra.contrib.systemusers.models import WebappUsers, SystemUser
from orchestra.contrib.saas.models import SaaS
from orchestra.contrib.musician.validators import ValidateZoneMixin

from . import api


class LoginForm(AuthenticationForm):

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            orchestra = api.Orchestra(self.request, username=username, password=password)

            if orchestra.user is None:
                raise self.get_invalid_login_error()
            else:
                self.username = username
                self.user = orchestra.user

        return self.cleaned_data

class ChangePasswordForm(forms.ModelForm):
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

    class Meta:
        fields = ("password",)
        model = WebappUsers

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        cleaned_data['password'] = make_password(password)
        return cleaned_data
    

class MailForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ("name", "domain", "mailboxes", "forward")
        help_texts = {
            'mailboxes': _('Hold down "Control" or "Command" on a Mac to select more than one or to deselect.'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['domain'].queryset = Domain.objects.filter(account=self.user)
        self.fields['mailboxes'].queryset = Mailbox.objects.filter(account=self.user)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('mailboxes') and not cleaned_data.get('forward'):
            raise ValidationError("A mailbox or forward address should be provided.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.account = self.user
        if commit:
            super().save(commit=True)
        return instance


class MailboxChangePasswordForm(ChangePasswordForm):
 
    class Meta:
        fields = ("password",)
        model = Mailbox

 
class MailboxCreateForm(forms.ModelForm):
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
    addresses = forms.ModelMultipleChoiceField(queryset=Address.objects.none(), required=False,  help_text=_('Hold down "Control" or "Command" on a Mac to select more than one or to deselect.'))

    class Meta:
        fields = ("name", "password", "password2", "addresses")
        model = Mailbox

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['addresses'].queryset = Address.objects.filter(account=user)
        self.user = user

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return  password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        cleaned_data['password'] = make_password(password)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.account = self.user
        if commit:
            super().save(commit=True)
        return instance


class MailboxUpdateForm(forms.ModelForm):
    addresses = forms.MultipleChoiceField(required=False, help_text=_('Hold down "Control" or "Command" on a Mac to select more than one or to deselect.'))

    class Meta:
        fields = ('addresses',)
        model = Mailbox


class MailboxSearchForm(forms.Form):
    name = forms.CharField(required=False)
    address = forms.CharField(required=False)

class RecordCreateForm(ValidateZoneMixin, forms.ModelForm):

    class Meta:
        model = Record
        fields = ("ttl", "type", "value")

    def __init__(self, *args, **kwargs):
        self.domain = kwargs.pop('domain')
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.domain = self.domain
        if commit:
            super().save(commit=True)
        return instance


class RecordUpdateForm(ValidateZoneMixin, forms.ModelForm):

    class Meta:
        model = Record
        fields = ("ttl", "type", "value")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.domain = self.instance.domain


class WebappUsersChangePasswordForm(ChangePasswordForm):
    class Meta:
        fields = ("password",)
        model = WebappUsers

class SystemUsersChangePasswordForm(ChangePasswordForm):
    class Meta:
        fields = ("password",)
        model = SystemUser



class BannedForm(forms.Form):
    ip = forms.GenericIPAddressField(label=_("Public IP"), protocol='IPv4')