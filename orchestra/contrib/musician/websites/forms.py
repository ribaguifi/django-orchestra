from django import forms
from orchestra.forms.widgets import DynamicHelpTextSelect

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str

from orchestra.contrib.websites.directives import SiteDirective
from orchestra.contrib.websites.models import Website, Content, WebsiteDirective
from orchestra.contrib.webapps.models import WebApp
from orchestra.contrib.domains.models import Domain

from orchestra.contrib.musician.settings import MUSICIAN_WEBSITES_ENABLE_GROUP_DIRECTIVE

        
class WebsiteUpdateForm(forms.ModelForm):
    class Meta:
        model = Website
        fields = ("is_active", "protocol", "domains")
        help_texts = {
            'domains': _('Hold down "Control", or "Command" on a Mac, to select more than one.')
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        # Excluir dominios de otros websites
        qs = Website.objects.filter(account=self.user).exclude(id=self.instance.id)
        used_domains = []
        for website in qs:
            dominios = website.domains.all()
            for dominio in dominios:
                used_domains.append(dominio)
        self.fields['domains'].queryset = Domain.objects.filter(account=self.user).exclude(name__in=used_domains)


class WesiteContentCreateForm(forms.ModelForm):

    class Meta:
        model = Content
        fields = ("webapp", "path")

    def __init__(self, *args, **kwargs):
        self.website = kwargs.pop('website')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['webapp'].queryset = WebApp.objects.filter(account=self.user, target_server=self.website.target_server)

    def clean(self):
        cleaned_data = super().clean()
        path = self.cleaned_data.get("path")
        path = "/" if path == "" else path
        if Content.objects.filter(website=self.website, path=path).exists():
            self.add_error('path',_("This Path already exists on this Website."))
        return cleaned_data   

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.website = self.website
        if commit:
            super().save(commit=True)
            self.website.save()
        return instance

from collections import defaultdict
from orchestra.contrib.websites.utils import normurlpath

class WesiteDirectiveCreateForm(forms.ModelForm):

    DIRECTIVES_HELP_TEXT = {
        op.name: force_str(op.help_text) for op in SiteDirective.get_plugins()
    }

    class Meta:
        model = WebsiteDirective
        fields = ("name", "value")

    def __init__(self, *args, **kwargs):
        self.website = kwargs.pop('website')
        # self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        target = 'this.id.replace("name", "value")'
        self.fields['name'].widget.attrs = DynamicHelpTextSelect(target, self.DIRECTIVES_HELP_TEXT).attrs
        self.fields['name'].choices = self.get_allow_choices()

    def get_allow_choices(self):
        groups = MUSICIAN_WEBSITES_ENABLE_GROUP_DIRECTIVE
        yield (None, '-------')
        options = SiteDirective.get_option_groups()
        for grp in groups:
            if grp in options.keys():
                yield (grp, [(op.name, op.verbose_name) for op in options[grp]])



    def clean(self):
        # Recoge todos los paths de directive y contents
        locations = set()
        for content in Content.objects.filter(website=self.website):
            location = content.path
            if location is not None:
                locations.add(location)
        for directive_obj in WebsiteDirective.objects.filter(website=self.website):
            location = directive_obj.value
            if location is not None:
                locations.add(normurlpath(location.split()[0]))
        # Comprueva que no se repitan
        directive = self.cleaned_data
        value = normurlpath(directive.get('value'))
        if value:
            value = value.split()[0]
        if value in locations:
            self.add_error('value', f"Location '{value}' already in use by other content/directive.")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.website = self.website
        if commit:
            super().save(commit=True)
            self.website.save()
        return instance