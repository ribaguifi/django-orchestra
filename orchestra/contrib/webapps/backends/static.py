from django.utils.translation import gettext_lazy as _

from orchestra.contrib.orchestration import ServiceController

from . import WebAppServiceMixin
from ..settings import WEBAPP_NEW_SERVERS

class StaticController(WebAppServiceMixin, ServiceController):
    """
    Static web pages.
    Only creates the webapp dir and leaves the web server the decision to execute CGIs or not.
    """
    verbose_name = _("Static")
    default_route_match = "webapp.type == 'static'"
    
    def save(self, webapp):
        context = self.get_context(webapp)
        if context.get('target_server').name in WEBAPP_NEW_SERVERS:
            self.check_webapp_dir(context)
            self.set_under_construction(context)
        else:
            self.create_webapp_dir(context)
            self.set_under_construction(context)

    def delete(self, webapp):
        context = self.get_context(webapp)
        if context.get('target_server').name in WEBAPP_NEW_SERVERS:
            webapp.sftpuser.delete()
        else:
            self.delete_webapp_dir(context)
