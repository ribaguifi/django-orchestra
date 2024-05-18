from django import forms
from orchestra.forms.widgets import DynamicHelpTextSelect

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from orchestra.contrib.websites.models import Website, Content, WebsiteDirective
from orchestra.contrib.webapps.models import WebApp
from orchestra.contrib.domains.models import Domain


        
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
        print(f"mypath: {path}")
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