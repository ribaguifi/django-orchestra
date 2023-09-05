from django import forms
from django.utils.encoding import force_str

from orchestra.admin.utils import admin_link
from orchestra.forms.widgets import SpanWidget

from django.core.exceptions import ValidationError
from orchestra.core import validators
from orchestra.utils.python import random_ascii
from orchestra.settings import NEW_SERVERS, WEB_SERVERS
from django.utils.translation import gettext_lazy as _

import textwrap
from orchestra.contrib.orchestration.models import Server

class PluginForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.plugin_field in self.fields:
            value = self.plugin.get_name()
            display = '%s <a href=".">change</a>' % force_str(self.plugin.verbose_name)
            self.fields[self.plugin_field].widget = SpanWidget(original=value, display=display)
            help_text = self.fields[self.plugin_field].help_text
            self.fields[self.plugin_field].help_text = getattr(self.plugin, 'help_text', help_text)

class PluginDataForm(PluginForm):
    data = forms.CharField(widget=forms.HiddenInput, required=False)
    target_server = forms.ModelChoiceField(queryset=Server.objects.filter(name__in=WEB_SERVERS),)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            for field in self.declared_fields:
                initial = self.fields[field].initial
                self.fields[field].initial = self.instance.data.get(field, initial)
            if self.instance.pk:
                # Admin Readonly fields are not availeble in self.fields, so we use Meta
                plugin = getattr(self.instance, '%s_class' % self.plugin_field)
                plugin_help_text = getattr(plugin, 'help_text', '')
                model_help_text = self.instance._meta.get_field(self.plugin_field).help_text
                self._meta.help_texts = {
                    self.plugin_field: plugin_help_text or model_help_text
                }
                for field in self.plugin.get_change_readonly_fields():
                    value = getattr(self.instance, field, None) or self.instance.data.get(field)
                    display = value
                    foo_display = getattr(self.instance, 'get_%s_display' % field, None)
                    if foo_display:
                        display = foo_display()
                    self.fields[field].required = False
                    self.fields[field].widget = SpanWidget(original=value, display=display)
    
    def clean(self):
        super().clean()
        data = {}
        # Update data fields
        for field in self.declared_fields:
            try:
                data[field] = self.cleaned_data[field]
            except KeyError:
                data[field] = self.data[field]
        # Keep old data fields
        for field, value in self.instance.data.items():
            if field not in data:
                try:
                    data[field] = self.cleaned_data[field]
                except KeyError:
                    data[field] = value
        self.cleaned_data['data'] = data


class PluginModelAdapterForm(PluginForm):
    def __init__(self, *args, **kwargs):
        super(PluginForm, self).__init__(*args, **kwargs)
        if self.plugin_field in self.fields:
            # Provide a link to the related DB object change view
            value = self.plugin.related_instance.pk
            link = admin_link()(self.plugin.related_instance)
            display = '%s <a href=".">change</a>' % link
            self.fields[self.plugin_field].widget = SpanWidget(original=value, display=display)
            help_text = self.fields[self.plugin_field].help_text


# --------------------------------------------------

class ExtendedPluginDataForm(PluginDataForm):
    # añade campos de username para creacion de sftpuser en servidores nuevos
    username = forms.CharField(label=_("Username"), max_length=16,
        required=False, validators=[validators.validate_name],
        help_text=_("Required. 16 characters or fewer. Letters, digits and "
                    "@/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain 16 characters or fewer, only letters, numbers and "
                         "@/./+/-/_ characters.")})
    password1 = forms.CharField(label=_("Password"), required=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'off'}),
        validators=[validators.validate_password],
        help_text=_("Suggestion: %s") % random_ascii(15))
    password2 = forms.CharField(label=_("Password confirmation"), required=False,
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."))

    def __init__(self, *args, **kwargs):
        super(ExtendedPluginDataForm, self).__init__(*args, **kwargs)
        self.fields['sftpuser'].widget = forms.HiddenInput()
        if self.instance.id is not None:
            self.fields['username'].widget = forms.HiddenInput()
            self.fields['password1'].widget = forms.HiddenInput()
            self.fields['password2'].widget = forms.HiddenInput()

        if not self.instance.pk:
            self.fields['target_server'].widget.attrs['onChange'] = textwrap.dedent("""\
                field = $(".field-username, .field-password1, .field-password2");
                input = $("#id_username, #id_password1, #id_password2");
                if (%s.includes(this.options[this.selectedIndex].text)) {
                    field.removeClass("hidden");
                } else {                                                                 
                    field.addClass("hidden");
                    input.val("");
                };"""  % list(NEW_SERVERS)
            )

    def clean_username(self):
        if not self.instance.id:
            webapp_server = self.cleaned_data.get("target_server")
            username = self.cleaned_data.get('username')
            if webapp_server is None:
                self.add_error("target_server", _("choice some server"))
            else:
                if webapp_server.name in NEW_SERVERS and not username:
                    self.add_error("username", _("SFTP user is required by new webservers"))
            return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            msg = _("The two password fields didn't match.")
            raise ValidationError(msg)
        return password2