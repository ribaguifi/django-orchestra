from orchestra.contrib.settings import Setting
from collections import defaultdict
from django.conf import settings


def getsetting(name):
    value = getattr(settings, name, None)
    return value or DEFAULTS.get(name)

# provide a default value allowing to overwrite it for each type of account
def allowed_resources_default_factory():
    return {'mailbox': 2, 'database': 1, 'account': 2, 'nextcloud': 2,}

DEFAULTS = {
    # allowed resources limit hardcoded because cannot be retrieved from the API.
    "ALLOWED_RESOURCES": defaultdict(
        allowed_resources_default_factory,
        {
            'INDIVIDUAL':
            {
                # 'disk': 1024,
                # 'traffic': 2048,
                'mailbox': 2,
                'database': 1,
                'account': 2,
                'nextcloud': 2,
            },
            'ASSOCIATION': {
                # 'disk': 5 * 1024,
                # 'traffic': 20 * 1024,
                'mailbox': 10,
                'database': 1,
                'account': 8,
                'nextcloud': 10,
            }
        }
    ),
    "URL_DB_PHPMYADMIN": "https://phpmyadmin.pangea.org/",
    "URL_MAILTRAIN": "https://grups.pangea.org/",
    "URL_SAAS_GITLAB": "https://gitlab.pangea.org/",
    "URL_SAAS_OWNCLOUD": "https://nextcloud.pangea.org/",
    "URL_SAAS_WORDPRESS": "https://blog.pangea.org/",
}

ALLOWED_RESOURCES = getsetting("ALLOWED_RESOURCES")

URL_DB_PHPMYADMIN = getsetting("URL_DB_PHPMYADMIN")

URL_MAILTRAIN = getsetting("URL_MAILTRAIN")

URL_SAAS_GITLAB = getsetting("URL_SAAS_GITLAB")

URL_SAAS_OWNCLOUD = getsetting("URL_SAAS_OWNCLOUD")

URL_SAAS_WORDPRESS = getsetting("URL_SAAS_WORDPRESS")


MUSICIAN_EDIT_ENABLE_PHP_OPTIONS = Setting('MUSICIAN_EDIT_ENABLE_PHP_OPTIONS', (
    'public-root',
    'timeout',
    'max_input_time',
    'max_input_vars',
    'memory_limit',
    'post_max_size',
    'upload_max_filesize',
))

MUSICIAN_WEBSITES_ENABLE_GROUP_DIRECTIVE = Setting('MUSICIAN_WEBSITES_ENABLE_GROUP_DIRECTIVE', (
    'HTTPD',
    ),
    help_text="Valid groups: HTTPD, ModSecurity, SSL, SaaS"
)

LANGUAGES = [
    ('en', 'English'),
    ('es', 'Spanish'),
    ('ca', 'Catalan'),
]