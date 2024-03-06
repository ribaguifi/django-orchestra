import os
import textwrap

from django.utils.translation import gettext_lazy as _

from orchestra.contrib.orchestration import ServiceController, replace
from django.template import Template, Context
from orchestra.settings import NEW_SERVERS
from .. import settings

from . import WebAppServiceMixin


class LimesurveyController(WebAppServiceMixin, ServiceController):
    """
    Installs the latest version of Limesurvey available on git github.com/LimeSurvey/LimeSurvey
    """
    verbose_name = _("Limesurvey")
    model = 'webapps.WebApp'
    default_route_match = "webapp.type == 'limesurvey-php'"
    doc_settings = (settings,
        ('WEBAPPS_DEFAULT_MYSQL_DATABASE_HOST',)
    )
    
    
    def save(self, webapp):
        context = self.get_context(webapp)
        perms = Template(textwrap.dedent("""\
            {% if sftpuser %}
            chown -R {{sftpuser}}:{{sftpuser}} {{home}}/webapps/{{app_name}}
            {% else %}
            chown -R {{user}}:{{group}} {{home}}/webapps/{{app_name}}
            {% endif %}
            """
        ))
        linenohub = Template(textwrap.dedent("""\
            {% if sftpuser %}
            su - {{sftpuser}} --shell /bin/bash << 'EOF'
            {% else %}
            su - {{user}} --shell /bin/bash << 'EOF'
            {% endif %}
            """
        ))
        context.update({'perms' :  perms.render(Context(context)), 'linenohub' :  linenohub.render(Context(context)) })
        self.append(textwrap.dedent("""\
            if [[ $(ls "%(app_path)s" | wc -l) -gt 1 ]]; then
                echo "App directory not empty." 2> /dev/null
                exit 0
            fi
            mkdir -p %(app_path)s
                        
            # Download limesurvey
            git clone --depth 1 https://github.com/LimeSurvey/LimeSurvey.git  %(app_path)s/
                                    
            # create database config       
            if [[ ! -e %(app_path)s/application/config/config.php ]]; then
                cp %(app_path)s/application/config/config-sample-mysql.php  %(app_path)s/application/config/config.php
                sed -i "s/'connectionString' => .*/'connectionString' => 'mysql:host=%(db_host)s;port=3306;dbname=%(db_name)s;',/"  %(app_path)s/application/config/config.php
                sed -i "s/'username' => .*/'username' => '%(db_user)s',/"         %(app_path)s/application/config/config.php
                sed -i "s/'password' => .*/'password' => '%(password)s',/"     %(app_path)s/application/config/config.php
                
            fi
            
            # add correct perms
            %(perms)s
            find  %(app_path)s/ -type f -exec chmod -x {} ";"
            
            # Run install moodle cli command on the background, because it takes so long...
            stdout=$(mktemp)
            stderr=$(mktemp)
            %(linenohub)s
                cd %(app_path)s/application/commands/
                php console.php install admin "%(password)s" admin "%(email)s" verbose
            EOF
            """) % context
        )
    
    def get_context(self, webapp):
        context = super(LimesurveyController, self).get_context(webapp)
        contents = webapp.content_set.all()
        context.update({
            'db_name': webapp.data['db_name'],
            'db_user': webapp.data['db_user'],
            'password': webapp.data['password'],
            'db_host': 'localhost' if webapp.target_server.name in NEW_SERVERS else settings.WEBAPPS_DEFAULT_MYSQL_DATABASE_HOST,
            'email': webapp.account.email,
            'sftpuser':  webapp.sftpuser.username if webapp.target_server.name in NEW_SERVERS else None ,
        })
        return replace(context, '"', "'")
