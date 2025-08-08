import os
import re
import textwrap

from django.template import Template, Context
from django.utils.translation import gettext_lazy as _

from orchestra.contrib.orchestration import ServiceController

from .. import settings
from ..utils import normurlpath
from .apache import Apache2Controller



class Apache2ControllerAnubis(Apache2Controller):
    """
    Apache backend Local website where Anubis redirects.
    """
    verbose_name = _("Apache 2 Anubis")

    def get_extra_conf(self, site, context, ssl=False):
        extra_conf = self.get_content_directives(site, context)
        directives = site.get_directives()

        extra_conf += self.get_security(directives)
        extra_conf += self.get_redirects(directives)
        extra_conf += self.get_proxies(directives)
        extra_conf += self.get_errordocuments(directives)
        settings_context = site.get_settings_context()
        for location, directive in settings.WEBSITES_VHOST_EXTRA_DIRECTIVES:
            extra_conf.append((location, directive % settings_context))
        # Order extra conf directives based on directives (longer first)
        extra_conf = sorted(extra_conf, key=lambda a: len(a[0]), reverse=True)
        return '\n'.join([conf for location, conf in extra_conf])

    def render_virtual_host(self, site, context):
        context.update({
            'vhost_set_fcgid': False,
            'server_alias_lines': ' \\\n                '.join(context['server_alias']),
        })
        context['extra_conf'] = self.get_extra_conf(site, context)
        return Template(textwrap.dedent("""\
            <VirtualHost {{ listen }}:{{ port_local }}>
                IncludeOptional /etc/apache2/site[s]-override/{{ site_unique_name }}.con[f]
                ServerName {{ server_name }}\
            {% if server_alias %}
                ServerAlias {{ server_alias_lines }}{% endif %}\
            {% if access_log %}
                CustomLog {{ access_log }} combined{% endif %}\
            {% if error_log %}
                ErrorLog {{ error_log }}{% endif %}

                SetEnvIf X-Forwarded-Proto "https" HTTPS=on
                                        
            {% for line in extra_conf.splitlines %}
                {{ line | safe }}{% endfor %}
            </VirtualHost>
            """)
        ).render(Context(context))

    def render_virtual_host_redirect_to_anubis(self, site, context):
        if context['server_name'] and site.active and site.extra_firewall:
            self.append(textwrap.dedent("""\
                read -r -d '' anubis_conf << 'EOF' || true
                # %(banner)s
                
                # These headers need to be set or else Anubis will
                # throw an "admin misconfiguration" error.
                RequestHeader set "X-Real-Ip" expr=%%{REMOTE_ADDR}
                RequestHeader set X-Forwarded-Proto "https"
                RequestHeader set "X-Http-Version" "%%{SERVER_PROTOCOL}s"

                ProxyPreserveHost On
                ProxyRequests Off
                ProxyVia Off

                ProxyPass / unix:/run/anubis/%(site_unique)s/%(site_unique)s.sock|http://localhost/
                ProxyPassReverse / unix:/run/anubis/%(site_unique)s/%(site_unique)s.sock|http://localhost/
                EOF
                {
                    echo -e "${anubis_conf}" | diff -N -I'^\s*#' %(sites_override)s -
                } || {
                    echo -e "${anubis_conf}" > %(sites_override)s
                    UPDATED_APACHE=1
                }""") % context
            )
        else:
            self.append(textwrap.dedent("""\
                rm %(sites_override)s %(sites_available)s || true 
                }""") % context
            )

    def save(self, site):
        context = self.get_context(site)
        if context['server_name'] and site.active and site.extra_firewall:
            apache_conf = '# %(banner)s\n' % context
            apache_conf += self.render_virtual_host(site, context)
            context['apache_conf'] = apache_conf.strip()
            self.append(textwrap.dedent("""
                # Generate Apache config for site %(site_name)s
                read -r -d '' apache_conf << 'EOF' || true
                %(apache_conf)s
                EOF
                {
                    echo -e "${apache_conf}" | diff -N -I'^\s*#' %(sites_available)s -
                } || {
                    echo -e "${apache_conf}" > %(sites_available)s
                    UPDATED_APACHE=1
                }""") % context
            )
            self.append(textwrap.dedent("""
                # Enable site %(site_name)s
                [[ $(a2ensite %(site_unique_name)s) =~ "already enabled" ]] || UPDATED_APACHE=1\
                """) % context
            )
        else:
            self.append(textwrap.dedent("""
                # Disable site %(site_name)s
                [[ $(a2dissite %(site_unique_name)s) =~ "already disabled" ]] || UPDATED_APACHE=1\
                """) % context
            )
        self.render_virtual_host_redirect_to_anubis(site, context)

    
    def delete(self, site):
        context = self.get_context(site)
        self.append(textwrap.dedent("""
            # Remove site configuration for %(site_name)s
            [[ $(a2dissite %(site_unique_name)s) =~ "already disabled" ]] || UPDATED_APACHE=1
            rm -f %(sites_available)s
            rm -f %(sites_override)s
            """) % context
        )


    def prepare(self):
        super(Apache2ControllerAnubis, self).prepare()
        # Coordinate apache restart with php backend in order not to overdo it
        self.append(textwrap.dedent("""
            BACKEND="Apache2ControllerAnubis"
            echo "$BACKEND" >> /dev/shm/reload.apache2

            function coordinate_apache_reload () {
                # Coordinate Apache reload with other concurrent backends (e.g. PHPController)
                is_last=0
                counter=0
                while ! mv /dev/shm/reload.apache2 /dev/shm/reload.apache2.locked; do
                    if [[ $counter -gt 4 ]]; then
                        echo "[ERROR]: Apache reload synchronization deadlocked!" >&2
                        exit 10
                    fi
                    counter=$(($counter+1))
                    sleep 0.1;
                done
                state="$(grep -v -E "^$BACKEND($|\s)" /dev/shm/reload.apache2.locked)" || is_last=1
                [[ $is_last -eq 0 ]] && {
                    echo "$state" | grep -v ' RELOAD$' || is_last=1
                }
                if [[ $is_last -eq 1 ]]; then
                    echo "[DEBUG]: Last backend to run, update: $UPDATED_APACHE, state: '$state'"
                    if [[ $UPDATED_APACHE -eq 1 || "$state" =~ .*RELOAD$ ]]; then
                        if service apache2 status > /dev/null; then
                            service apache2 reload
                        else
                            service apache2 start
                        fi
                    fi
                    rm /dev/shm/reload.apache2.locked
                else
                    echo "$state" > /dev/shm/reload.apache2.locked
                    if [[ $UPDATED_APACHE -eq 1 ]]; then
                        echo -e "[DEBUG]: Apache will be reloaded by another backend:\\n${state}"
                        echo "$BACKEND RELOAD" >> /dev/shm/reload.apache2.locked
                    fi
                    mv /dev/shm/reload.apache2.locked /dev/shm/reload.apache2
                fi
            }""")
        )

    def get_context(self, site):
        base_apache_conf = settings.WEBSITES_BASE_APACHE_CONF
        sites_override = os.path.join(base_apache_conf, 'sites-override')
        sites_available = os.path.join(base_apache_conf, 'sites-available')
        sites_enabled = os.path.join(base_apache_conf, 'sites-enabled')
        server_name, server_alias = self.get_server_names(site)
        context = {
            'site': site,
            'site_name': f"{site.name}_anubis",
            'listen': settings.WEBSITES_ANUBIS_LISTEN,
            'port_local': settings.WEBSITES_ANUBIS_PORT,
            'site_unique_name': f"{site.unique_name}_anubis",
            'site_unique': f"{site.unique_name}",
            'user': self.get_username(site),
            'group': self.get_groupname(site),
            'server_name': server_name,
            'server_alias': server_alias,
            'sites_enabled': "%s_anubis.conf" % os.path.join(sites_enabled, site.unique_name),
            'sites_available': "%s_anubis.conf" % os.path.join(sites_available, site.unique_name),
            'sites_override': "%s_redirect_anubis.conf" % os.path.join(sites_override, site.unique_name),
            'access_log': site.get_www_access_log_path(),
            'error_log': site.get_www_error_log_path(),
            'banner': self.get_banner(),
        }
        if not context['listen']:
            raise ValueError("WEBSITES_ANUBIS_LISTEN is empty.")
        return context

    def set_content_context(self, content, context):
        content_context = {
            'type': content.webapp.type,
            'location': normurlpath(content.path),
            'app_name': content.webapp.name,
            'app_path': content.webapp.get_path(),
        }
        context.update(content_context)





class AnubisController(ServiceController):
    """
    Anubis backend.
    """
    verbose_name = _("Anubis")
    model = 'websites.Website'
    actions = ('save', 'delete',)

    def remove_config(self, context):
        self.append(textwrap.dedent("""\
            if [ -e "/etc/anubis/%(site_unique_name)s.env" ]; then
                systemctl stop anubis@%(site_unique_name)s
                systemctl disable anubis@%(site_unique_name)s
                rm /etc/anubis/%(site_unique_name)s.env             
            fi
            """) % context
        )

    def save(self, site):
        context = self.get_context(site)
        if context['server_name'] and site.active and site.extra_firewall:
            self.append(textwrap.dedent("""\
                read -r -d '' anubis_conf << 'EOF' || true
                # %(banner)s
                BIND=/run/anubis/%(site_unique_name)s/%(site_unique_name)s.sock
                BIND_NETWORK=unix
                SOCKET_MODE=0770
                DIFFICULTY=4
                METRICS_BIND_NETWORK=unix
                METRICS_BIND=/run/anubis/%(site_unique_name)s/%(site_unique_name)s_metrics.sock
                POLICY_FNAME=/etc/anubis/botPolicies.yaml
                TARGET=http://%(server_name)s:%(port)s
                EOF
                {
                    echo -e "${anubis_conf}" | diff -N -I'^\s*#' /etc/anubis/%(site_unique_name)s.env -
                } || {
                    echo -e "${anubis_conf}" > /etc/anubis/%(site_unique_name)s.env
                    systemctl restart anubis@%(site_unique_name)s
                    systemctl enable anubis@%(site_unique_name)s
                }""") % context
            )
        else:
            self.remove_config(context)


    
    def delete(self, site):
        context = self.get_context(site)
        self.remove_config(context)
        

    def get_server_names(self, site):
        server_name = None
        server_alias = []
        for domain in site.domains.all().order_by('name'):
            if not server_name and not domain.name.startswith('*'):
                server_name = domain.name
            else:
                server_alias.append(domain.name)
        return server_name, server_alias


    def get_context(self, site):
        server_name, server_alias = self.get_server_names(site)
        context = {
            'site': site,
            'site_name': site.name,
            'listen': settings.WEBSITES_ANUBIS_LISTEN,
            'port': settings.WEBSITES_ANUBIS_PORT,
            'site_unique_name': site.unique_name,
            'server_name': server_name,
            'banner': self.get_banner(),
        }
        print(context)
        if not context['listen']:
            raise ValueError("WEBSITES_ANUBIS_LISTEN is empty.")
        return context
