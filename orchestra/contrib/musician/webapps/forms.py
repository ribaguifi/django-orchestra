from django import forms
from orchestra.forms.widgets import DynamicHelpTextSelect

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str

from orchestra.contrib.webapps.models import WebApp, WebAppOption
from orchestra.contrib.webapps.options import AppOption
from orchestra.contrib.webapps.types import AppType

from orchestra.contrib.musician.settings import MUSICIAN_EDIT_ENABLE_PHP_OPTIONS



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
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.webapp = self.webapp
        if commit:
            super().save(commit=True)
            self.webapp.save()
        return instance
        

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
