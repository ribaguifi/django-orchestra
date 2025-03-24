from django.utils.translation import gettext_lazy as _

from orchestra.contrib.orchestration import ServiceController

from . import NextCloudAPIMixin
from .. import settings

import textwrap
from orchestra.contrib.resources import ServiceMonitor

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


class ApacheTrafficNextcloud(ServiceMonitor):
    """
    Parses apache logs,
    looking for the size of each request on the last word of the log line.
    
    Compatible log format:
    <tt>LogFormat "%h %l %u %t \"%r\" %>s %O %{nc_username}C"</tt>
    or if include_received_bytes:
    <tt>LogFormat "%h %l %u %t \"%r\" %>s %I %O %{nc_username}C"</tt>
    <tt>CustomLog /var/log/apache2/access_nextcloud_nomusuari.log</tt>
    """
    model = 'saas.SaaS'
    script_executable = '/usr/bin/python3'
    monthly_sum_old_values = True
    abstract = True
    include_received_bytes = True
    
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
                        with open(access_log, 'r', encoding="utf-8", errors="ignore") as handler:
                            for line in handler.readlines():
                                line = line.split()
                                host, __, __, date = line[:4]
                                if host in {ignore_hosts}:
                                    continue
                                size, hostname = line[-2:]
                                size = int(size)
                                if include_received:
                                    size += int(line[-3])
                                if hostname == "-":
                                    pattern = r'remote.php/dav/files/([^/]+)/'
                                    match = re.search(pattern, ' '.join(line))
                                    if match:
                                        hostname = match.group(1)
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
            'site_domain': saas.name,
            'last_date': self.get_last_date(saas.pk).strftime("%Y-%m-%d %H:%M:%S %Z"),
            'object_id': saas.pk,
        }


class NextcloudTraffic(ApacheTrafficNextcloud):
    __doc__ = ApacheTrafficNextcloud.__doc__
    verbose_name = _("nextCloud SaaS Traffic")
    default_route_match = "saas.service == 'nextcloud'"
    doc_settings = (settings,
        ('SAAS_TRAFFIC_IGNORE_HOSTS', 'SAAS_NEXTCLOUD_LOG_PATH')
    )
    log_path = settings.SAAS_NEXTCLOUD_LOG_PATH