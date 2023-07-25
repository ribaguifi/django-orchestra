import os

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from rest_framework import serializers

from orchestra.core import validators
from orchestra.plugins.forms import PluginDataForm
from orchestra.utils.python import random_ascii

from ..options import AppOption
from ..settings import WEBAPP_NEW_SERVERS

from . import AppType
from .php import PHPApp, PHPAppForm, PHPAppSerializer


class StaticForm(PluginDataForm):
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
        super(StaticForm, self).__init__(*args, **kwargs)
        self.fields['sftpuser'].widget = forms.HiddenInput()
        if self.instance.id is not None:
            self.fields['username'].widget = forms.HiddenInput()
            self.fields['password1'].widget = forms.HiddenInput()
            self.fields['password2'].widget = forms.HiddenInput()

    def clean(self):
        if not self.instance.id:
            webapp_server = self.cleaned_data.get("target_server")
            username = self.cleaned_data.get('username')
            if webapp_server is None:
                self.add_error("target_server", _("choice some target_server"))
            else:
                if webapp_server.name in WEBAPP_NEW_SERVERS and username == '':
                    self.add_error("username", _("SFTP user is required by new webservers"))

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            msg = _("The two password fields didn't match.")
            raise ValidationError(msg)
        return password2


class StaticApp(AppType):
    name = 'static'
    verbose_name = "Static"
    help_text = _("This creates a Static application under ~/webapps/&lt;app_name&gt;<br>"
                  "Apache2 will be used to serve static content and execute CGI files.")
    icon = 'orchestra/icons/apps/Static.png'
    option_groups = (AppOption.FILESYSTEM,)
    form = StaticForm

    def get_directive(self):
        return ('static', self.instance.get_path())


class WebalizerApp(AppType):
    name = 'webalizer'
    verbose_name = "Webalizer"
    directive = ('static', '%(app_path)s%(site_name)s')
    help_text = _(
        "This creates a Webalizer application under ~/webapps/&lt;app_name&gt;-&lt;site_name&gt;<br>"
        "Statistics will be collected once this app is mounted into one or more Websites.")
    icon = 'orchestra/icons/apps/Stats.png'
    option_groups = ()
    
    def get_directive(self):
        webalizer_path = os.path.join(self.instance.get_path(), '%(site_name)s')
        webalizer_path = os.path.normpath(webalizer_path)
        return ('static', webalizer_path)


class SymbolicLinkForm(PHPAppForm):
    path = forms.CharField(label=_("Path"), widget=forms.TextInput(attrs={'size':'100'}),
        help_text=_("Path for the origin of the symbolic link."))


class SymbolicLinkSerializer(PHPAppSerializer):
    path = serializers.CharField(label=_("Path"))


class SymbolicLinkApp(PHPApp):
    name = 'symbolic-link'
    verbose_name = "Symbolic link"
    form = SymbolicLinkForm
    serializer = SymbolicLinkSerializer
    icon = 'orchestra/icons/apps/SymbolicLink.png'
    change_readonly_fields = ('path',)
