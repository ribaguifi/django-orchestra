import pkgutil
import textwrap
import requests
import time
import sys

from orchestra.contrib.resources import ServiceMonitor
from orchestra.contrib.orchestration import replace
from django.utils.translation import gettext_lazy as _
import xml.etree.ElementTree as ET

from .. import settings


class ApacheTrafficByHost(ServiceMonitor):
    """
    Parses apache logs,
    looking for the size of each request on the last word of the log line.
    
    Compatible log format:
    <tt>LogFormat "%h %l %u %t \"%r\" %>s %O %{Host}i" host</tt>
    or if include_received_bytes:
    <tt>LogFormat "%h %l %u %t \"%r\" %>s %I %O %{Host}i" host</tt>
    <tt>CustomLog /home/pangea/logs/apache/host_blog.pangea.org.log host</tt>
    """
    model = 'saas.SaaS'
    script_executable = '/usr/bin/python3'
    monthly_sum_old_values = True
    abstract = True
    include_received_bytes = False
    
    def prepare(self):
        access_log = self.log_path
        context = {
            'access_logs': str((access_log, access_log+'.1')),
            'current_date': self.current_date.strftime("%Y-%m-%d %H:%M:%S %Z"),
            'ignore_hosts': str(settings.SAAS_TRAFFIC_IGNORE_HOSTS),
            'include_received_bytes': str(self.include_received_bytes),
        }
        self.append(textwrap.dedent("""\
            import re
            import sys
            from datetime import datetime
            from dateutil import tz
            
            def to_local_timezone(date, tzlocal=tz.tzlocal()):
                date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S %Z')
                date = date.replace(tzinfo=tz.tzutc())
                date = date.astimezone(tzlocal)
                return date
            
            # Use local timezone
            end_date = to_local_timezone('{current_date}')
            end_date = int(end_date.strftime('%Y%m%d%H%M%S'))
            access_logs = {access_logs}
            sites = {{}}
            months = {{
                'Jan': '01',
                'Feb': '02',
                'Mar': '03',
                'Apr': '04',
                'May': '05',
                'Jun': '06',
                'Jul': '07',
                'Aug': '08',
                'Sep': '09',
                'Oct': '10',
                'Nov': '11',
                'Dec': '12',
            }}
            
            def prepare(object_id, site_domain, ini_date):
                global sites
                ini_date = to_local_timezone(ini_date)
                ini_date = int(ini_date.strftime('%Y%m%d%H%M%S'))
                sites[site_domain] = [ini_date, object_id, 0]
            
            def monitor(sites, end_date, months, access_logs):
                include_received = {include_received_bytes}
                for access_log in access_logs:
                    try:
                        with open(access_log, 'r') as handler:
                            for line in handler.readlines():
                                line = line.split()
                                host, __, __, date = line[:4]
                                if host in {ignore_hosts}:
                                    continue
                                size, hostname = line[-2:]
                                size = int(size)
                                if include_received:
                                    size += int(line[-3])
                                try:
                                    site = sites[hostname]
                                except KeyError:
                                    continue
                                else:
                                    # [16/Sep/2015:11:40:38
                                    day, month, date = date[1:].split('/')
                                    year, hour, min, sec = date.split(':')
                                    date = year + months[month] + day + hour + min + sec
                                    if site[0] < int(date) < end_date:
                                        site[2] += size
                    except IOError as e:
                        sys.stderr.write(str(e)+'\\n')
                for opts in sites.values():
                    ini_date, object_id, size = opts
                    sys.stdout.write('%s %s\\n' % (object_id, size))
            """).format(**context)
        )
    
    def monitor(self, saas):
        context = self.get_context(saas)
        self.append("prepare(%(object_id)s, '%(site_domain)s', '%(last_date)s')" % context)
    
    def commit(self):
        self.append('monitor(sites, end_date, months, access_logs)')
    
    def get_context(self, saas):
        return {
            'site_domain': saas.get_site_domain(),
            'last_date': self.get_last_date(saas.pk).strftime("%Y-%m-%d %H:%M:%S %Z"),
            'object_id': saas.pk,
        }


class ApacheTrafficByName(ApacheTrafficByHost):
    __doc__ = ApacheTrafficByHost.__doc__
    
    def get_context(self, saas):
        return {
            'site_domain': saas.name,
            'last_date': self.get_last_date(saas.pk).strftime("%Y-%m-%d %H:%M:%S %Z"),
            'object_id': saas.pk,
        }

    
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

    
for __, module_name, __ in pkgutil.walk_packages(__path__):
    # sorry for the exec(), but Import module function fails :(
    exec('from . import %s' % module_name)
