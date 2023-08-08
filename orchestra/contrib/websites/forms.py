from collections import defaultdict

from django import forms
from django.core.exceptions import ValidationError

from orchestra.contrib.webapps.models import WebApp

from .utils import normurlpath
from .validators import validate_domain_protocol, validate_server_name


class WebsiteAdminForm(forms.ModelForm):
    def clean(self):
        """ Prevent multiples domains on the same protocol """
        super(WebsiteAdminForm, self).clean()
        domains = self.cleaned_data.get('domains')
        if not domains:
            return self.cleaned_data
        protocol = self.cleaned_data.get('protocol')
        domains = domains.all()
        for domain in domains:
            try:
                validate_domain_protocol(self.instance, domain, protocol)
            except ValidationError as err:
                self.add_error(None, err)
        try:
            validate_server_name(domains)
        except ValidationError as err:
            self.add_error('domains', err)
        return self.cleaned_data
    
    def clean_target_server(self):
        # valida que el webapp pertenezca al server indicado
        try:
            server = self.cleaned_data['target_server']
        except:
            server = self.instance.target_server

        diferentServer = False
        for i in range(int(self.data['content_set-TOTAL_FORMS']) + 1):
            if f"content_set-{i}-webapp" in self.data.keys() and f"content_set-{i}-DELETE" not in self.data.keys():
                if self.data[f"content_set-{i}-webapp"]:
                    idWebapp = self.data[f"content_set-{i}-webapp"]
                    webapp = WebApp.objects.get(id=idWebapp)
                    if webapp.target_server.id != server.id :
                        diferentServer = True
        if diferentServer:
            self.add_error("target_server", f"Some Webapp does not belong to the {server.name} server")
        return server


class WebsiteDirectiveInlineFormSet(forms.models.BaseInlineFormSet):
    def clean(self):
        # directives formset cross-validation with contents for unique locations
        locations = set()
        for form in self.content_formset.forms:
            location = form.cleaned_data.get('path')
            delete = form.cleaned_data.get('DELETE')
            if not delete and location is not None:
                locations.add(normurlpath(location))
        
        values = defaultdict(list)
        for form in self.forms:
            wdirective = form.instance
            directive = form.cleaned_data
            if directive.get('name') is not None:
                try:
                    wdirective.directive_instance.validate_uniqueness(directive, values, locations)
                except ValidationError as err:
                    for k,v in err.error_dict.items():
                        form.add_error(k, v)
