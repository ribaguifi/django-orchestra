from django.utils.translation import gettext_lazy as _

from orchestra.contrib.orchestration import ServiceController

from . import ApacheTrafficByName, NextCloudAPIMixin
from .. import settings


class NextCloudController(NextCloudAPIMixin, ServiceController):
    """
    Creates a wordpress site on a WordPress MultiSite installation.
    
    You should point it to the database server
    """
    verbose_name = _("nextCloud SaaS")
    model = 'saas.SaaS'
    default_route_match = "saas.service == 'nextcloud'"
    doc_settings = (settings,
        ('SAAS_NEXTCLOUD_API_URL',)
    )
    
    def update_or_create(self, saas, server):
        try:
            self.api_get('users/%s' % saas.name)
        except RuntimeError:
            if getattr(saas, 'password', None):
                self.create(saas)
                self.update_group(saas)
                self.update_quota(saas)
            else:
                raise
        else:
            if getattr(saas, 'password', None):
                self.update_password(saas)
            else:
                self.update_group(saas)
                self.update_quota(saas)
        if saas.is_active:        
            self.enable_user(saas)
        else:
            self.disable_user(saas)

    def remove(self, saas, server):
        self.api_delete('users/%s' % saas.name)
    
    def save(self, saas):  
        self.append(self.update_or_create, saas)
          
    def delete(self, saas):
        self.append(self.remove, saas)


class NextcloudTraffic(ApacheTrafficByName):
    __doc__ = ApacheTrafficByName.__doc__
    verbose_name = _("nextCloud SaaS Traffic")
    default_route_match = "saas.service == 'nextcloud'"
    doc_settings = (settings,
        ('SAAS_TRAFFIC_IGNORE_HOSTS', 'SAAS_NEXTCLOUD_LOG_PATH')
    )
    log_path = settings.SAAS_NEXTCLOUD_LOG_PATH
