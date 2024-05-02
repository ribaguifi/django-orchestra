from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from orchestra.forms.widgets import DynamicHelpTextSelect

from django.contrib.auth.hashers import make_password

from orchestra.contrib.domains.models import Domain, Record
from orchestra.contrib.mailboxes.models import Address, Mailbox
from orchestra.contrib.systemusers.models import WebappUsers, SystemUser
from orchestra.contrib.musician.validators import ValidateZoneMixin
from orchestra.contrib.webapps.models import WebApp, WebAppOption
from orchestra.contrib.webapps.options import AppOption
from orchestra.contrib.webapps.types import AppType

from . import api
from .settings import MUSICIAN_EDIT_ENABLE_PHP_OPTIONS


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
    addresses = forms.ModelMultipleChoiceField(queryset=Address.objects.none(), required=False)

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
    addresses = forms.MultipleChoiceField(required=False)

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


class WebappOptionForm(forms.ModelForm):

    OPTIONS_HELP_TEXT = {
        op.name: force_str(op.help_text) for op in AppOption.get_plugins()
    }

    class Meta:
        model = WebAppOption
        fields = ("name", "value")

    def __init__(self, *args, **kwargs):
        try:
            self.webapp = kwargs.pop('webapp')
            super().__init__(*args, **kwargs)
        except:
            super().__init__(*args, **kwargs)
            self.webapp = self.instance.webapp
    

        target = 'this.id.replace("name", "value")'
        self.fields['name'].widget.attrs = DynamicHelpTextSelect(target, self.OPTIONS_HELP_TEXT).attrs


class WebappOptionCreateForm(WebappOptionForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        plugin = AppType.get(self.webapp.type)
        choices = list(plugin.get_group_options_choices())
        for grupo, opciones in enumerate(choices):
            if isinstance(opciones[1], list): 
                nueva_lista = [opc for opc in opciones[1] if opc[0] in MUSICIAN_EDIT_ENABLE_PHP_OPTIONS]
                choices[grupo] = (opciones[0], nueva_lista)
        self.fields['name'].widget.choices = choices

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.webapp = self.webapp
        if commit:
            super().save(commit=True)
        return instance

    def clean(self):
        cleaned_data = super().clean()
        name = self.cleaned_data.get("name")
        if WebAppOption.objects.filter(webapp=self.webapp, name=name).exists():
            raise ValidationError(_("This option already exist."))
        return cleaned_data   

class WebappOptionUpdateForm(WebappOptionForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.choices = [(self.initial['name'], self.initial['name'])]

        

    

