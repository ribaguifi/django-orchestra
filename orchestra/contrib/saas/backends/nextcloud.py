import re
import sys
import textwrap
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests
from django.utils.translation import gettext_lazy as _

from orchestra.contrib.orchestration import ServiceController
from orchestra.contrib.resources import ServiceMonitor
from orchestra.contrib.resources.models import ResourceData
from orchestra.contrib.saas.models import SaaS

from . import ApacheTrafficByName
from .. import settings


class NextCloudAPIMixin(object):
    def validate_response(self, response):
        request = response.request
        context = (request.method, response.url, request.body, response.status_code)
        # sys.stderr.write("%s %s '%s' HTTP %s\n" % context)
        if response.status_code != requests.codes.ok:
            raise RuntimeError("%s %s '%s' HTTP %s" % context)
        root = ET.fromstring(response.text)
        statuscode = root.find("./meta/statuscode").text
        if statuscode != '100':
            message = root.find("./meta/status").text
            request = response.request
            context = (request.method, response.url, request.body, statuscode, message)
            raise RuntimeError("%s %s '%s' ERROR %s, %s" % context)
    
    def api_call(self, action, url_path, *args, **kwargs):
        BASE_URL = settings.SAAS_NEXTCLOUD_API_URL.rstrip('/')
        url = '/'.join((BASE_URL, url_path))
        response = action(url, headers={'OCS-APIRequest':'true'}, verify=False, *args, **kwargs)
        self.validate_response(response)
        return response
    
    def api_get(self, url_path, *args, **kwargs):
        return self.api_call(requests.get, url_path, *args, **kwargs)
    
    def api_post(self, url_path, *args, **kwargs):
        return self.api_call(requests.post, url_path, *args, **kwargs)
    
    def api_put(self, url_path, *args, **kwargs):
        return self.api_call(requests.put, url_path, *args, **kwargs)
    
    def api_delete(self, url_path, *args, **kwargs):
        return self.api_call(requests.delete, url_path, *args, **kwargs)
    
    def create(self, saas):
        data = {
            'userid': saas.name,
            'password': saas.password,
        }
        self.api_post('users', data)

    def update_group(self, saas):
        data = {
            'groupid': saas.account.username
        }
        try:
            self.api_get('groups/%s' % saas.account.username)
        except RuntimeError:
            self.api_post('groups', data)
        self.api_post(f'users/{saas.name}/groups', data)
    
    def update_quota(self, saas):
        if hasattr(saas, 'resources') and hasattr(saas.resources, 'nextcloud-disk'):
            resource = getattr(saas.resources, 'nextcloud-disk')
            quotaValue = f"{resource.allocated}G" if resource.allocated > 0 else "default"
            data = {
                'key': "quota",
                'value': quotaValue
            }
            self.api_put(f'users/{saas.name}', data)

    def update_password(self, saas):
        """
        key: email|quota|display|password
        value: el valor a modificar.
            Si es un email, tornarà un error si la direcció no te la "@"
            Si es una quota, sembla que algo per l'estil "5G", "100M", etc. funciona. Quota 0 = infinit
            "display" es el display name, no crec que el fem servir, és cosmetic
        """
        data = {
            'key': 'password',
            'value': saas.password,
        }
        self.api_put('users/%s' % saas.name, data)

    def disable_user(self, saas):
        self.api_put('users/%s/disable' % saas.name)
    
    def enable_user(self, saas):
        self.api_put('users/%s/enable' % saas.name)
    
    def get_user(self, saas):
        """
        {
            'displayname'
            'email'
            'quota' =>
            {
                'free' (en Bytes)
                'relative' (en tant per cent sense signe %, e.g. 68.17)
                'total' (en Bytes)
                'used' (en Bytes)
            }
        }
        """
        response = self.api_get('users/%s' % saas.name)
        root = ET.fromstring(response.text)
        ret = {}
        for data in root.find('./data'):
            ret[data.tag] = data.text
        ret['quota'] = {}
        for data in root.find('.data/quota'):
            ret['quota'][data.tag] = data.text
        return ret


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


class NextCloudDiskQuota(NextCloudAPIMixin, ServiceMonitor):
    model = 'saas.SaaS'
    verbose_name = _("nextCloud SaaS Disk Quota")
    default_route_match = "saas.service == 'nextcloud'"
    resource = ServiceMonitor.DISK
    delete_old_equal_values = True
    
    def monitor(self, user):
        context = self.get_context(user)
        self.append("echo %(object_id)s $(monitor %(base_home)s)" % context)
    
    def get_context(self, user):
        context = {
            'object_id': user.pk,
            'base_home': user.get_base_home(),
        }
        return replace(context, "'", '"')
    
    def get_quota(self, saas, server):
        try:
            user = self.get_user(saas)
        except requests.exceptions.ConnectionError:
            time.sleep(2)
            user = self.get_user(saas)
        context = {
            'object_id': saas.pk,
            'used': int(user['quota'].get('used', 0)),
        }
        sys.stdout.write('%(object_id)i %(used)i\n' % context)
    
    def monitor(self, saas):
        self.append(self.get_quota, saas)
