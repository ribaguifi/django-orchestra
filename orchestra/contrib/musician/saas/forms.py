from django import forms

from orchestra.forms.widgets import SpanWidget
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from orchestra.utils.python import random_ascii
from django.core.exceptions import ValidationError

from django.forms.widgets import HiddenInput

from orchestra.contrib.saas.models import SaaS
from orchestra.contrib.musician.forms import ChangePasswordForm



class SaasUpdateForm(forms.ModelForm):
    site_url = forms.CharField(label=_("Site URL"), widget=SpanWidget(), required=False)

    class Meta:
        model = SaaS
        fields = ("is_active", "service", "name", "data", "custom_url")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['readonly'] = True
        self.fields['site_url'].widget.attrs['readonly'] = True
        self.fields['service'].widget = HiddenInput()
        self.fields['data'].widget = HiddenInput()
  
        # asignar valor al field site_url
        site_domain = self.instance.get_site_domain()
        context = {
        'site_name': '&lt;site_name&gt;',
        'name': '&lt;site_name&gt;',
        }
        site_domain = site_domain % context
        if '&lt;site_name&gt;' in site_domain:
            site_link = site_domain
        else:
            site_link = '<a href="http://%s">%s</a>' % (site_domain, site_domain)
        self.fields['site_url'].widget.display = site_link

        if self.instance:
            if self.instance.pk:
                self.fields['data'].required = False


class SaasWordpressUpdateForm(SaasUpdateForm):
    blog_id = forms.IntegerField(label=("Blog ID"), widget=SpanWidget(), required=False,
        help_text=_("ID of this blog used by WordPress, the only attribute that doesn't change."))
    email = forms.EmailField(label=_("Email"),
            help_text=_("A new user will be created if the above email address is not in the database.<br>"
                        "The username and password will be mailed to this email address."))
    
    def __init__(self, *args, **kwargs):
        # self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['blog_id'].widget.attrs['readonly'] = True
    
        
        self.fields["is_active"].widget = HiddenInput()
        self.fields["custom_url"].widget.attrs['readonly'] = True

        admin_url = 'http://%s/wp-admin/' % self.instance.get_site_domain()
        help_text = 'Admin URL: <a href="{0}">{0}</a>'.format(admin_url)
        self.fields['site_url'].help_text = mark_safe(help_text)

        if self.instance:
            for field in self.declared_fields:
                initial = self.fields[field].initial
                self.fields[field].initial = self.instance.data.get(field, initial)


class SaasNextcloudUpdateForm(SaasUpdateForm):
    def __init__(self, *args, **kwargs):
        # self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)  
        self.fields["custom_url"].widget = HiddenInput()


class NextcloudChangePasswordForm(ChangePasswordForm):
    class Meta:
        fields = ("password",)
        model = SaaS

    def __init__(self, *args, **kwargs):
        super(NextcloudChangePasswordForm, self).__init__(*args, **kwargs)
        self.fields['password'].help_text = _("Suggestion: %s") % random_ascii(20)

    def clean_password2(self):
        super().clean_password2()
        password = self.cleaned_data.get("password2")
        self.fields['password'] = password
        self.instance.set_password(password)


class NextcloudCreateForm(forms.ModelForm):
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
        fields = ("service", "name", "password", "password2", "account")
        model = SaaS

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['account'].initial = user
        self.fields['account'].widget = HiddenInput()
        self.fields['service'].choices = [("nextcloud","nextCloud")]
        self.fields['password'].help_text = _("Suggestion: %s") % random_ascii(20)
        


    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return  password
    
    def clean_password(self):
        password = self.cleaned_data.get("password")
        self.fields['password'] = password
        self.instance.set_password(password)
    
