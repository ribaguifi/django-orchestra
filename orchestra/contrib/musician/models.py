import ast
import logging

from django.utils.dateparse import parse_datetime
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from . import settings as musician_settings
from .utils import get_bootstraped_percent


logger = logging.getLogger(__name__)


class OrchestraModel:
    """ Base class from which all orchestra models will inherit. """
    api_name = None
    verbose_name = None
    fields = ()
    param_defaults = {}
    id = None

    def __init__(self, **kwargs):
        if self.verbose_name is None:
            self.verbose_name = self.api_name

        for (param, default) in self.param_defaults.items():
            setattr(self, param, kwargs.get(param, default))


    @classmethod
    def new_from_json(cls, data, **kwargs):
        """ Create a new instance based on a JSON dict. Any kwargs should be
        supplied by the inherited, calling class.
        Args:
            data: A JSON dict, as converted from the JSON in the orchestra API.
        """
        if data is None:
            return cls()

        json_data = data.copy()
        if kwargs:
            for key, val in kwargs.items():
                json_data[key] = val

        c = cls(**json_data)
        c._json = data

        return c

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)

    def __str__(self):
        return '%s object (%s)' % (self.__class__.__name__, self.id)


class Bill(OrchestraModel):
    api_name = 'bill'
    param_defaults = {
        "id": None,
        "number": "1",
        "type": "INVOICE",
        "total": 0.0,
        "is_sent": False,
        "created_on": "",
        "due_on": "",
        "comments": "",
    }


class BillingContact(OrchestraModel):
    param_defaults = {
        'name': None,
        'address': None,
        'city': None,
        'zipcode': None,
        'country': None,
        'vat': None,
    }


class PaymentSource(OrchestraModel):
    api_name = 'payment-source'
    param_defaults = {
        "method": None,
        "data": [],
        "is_active": False,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # payment details are passed as a plain string
        # try to convert to a python structure
        try:
            self.data = ast.literal_eval(self.data)
        except (ValueError, SyntaxError) as e:
            logger.error(e)


class UserAccount(OrchestraModel):
    api_name = 'accounts'
    param_defaults = {
        'username': None,
        'type': None,
        'language': None,
        'short_name': None,
        'full_name': None,
        'billing': {},
        'last_login': None,
    }

    @classmethod
    def new_from_json(cls, data, **kwargs):
        billing = None
        language = None
        last_login = None

        if 'billcontact' in data:
            billing = BillingContact.new_from_json(data['billcontact'])

        # Django expects that language code is lowercase
        if 'language' in data:
            language = data['language'].lower()

        last_login = data.get('last_login')
        if last_login is not None:
            last_login = parse_datetime(last_login)

        return super().new_from_json(data=data, billing=billing, language=language, last_login=last_login)

    def allowed_resources(self, resource):
        allowed_by_type = musician_settings.ALLOWED_RESOURCES[self.type]
        return allowed_by_type[resource]


class DatabaseUser(OrchestraModel):
    api_name = 'databaseusers'
    fields = ('username',)
    param_defaults = {
        'username': None,
    }


class DatabaseService(OrchestraModel):
    api_name = 'database'
    verbose_name = _('Databases')
    description = _('Description details for databases page.')
    fields = ('name', 'type', 'users')
    param_defaults = {
        "id": None,
        "name": None,
        "type": None,
        "users": None,
        "usage": {},
    }

    @classmethod
    def new_from_json(cls, data, **kwargs):
        users = None
        if 'users' in data:
            users = [DatabaseUser.new_from_json(user_data) for user_data in data['users']]

        usage = cls.get_usage(data)

        return super().new_from_json(data=data, users=users, usage=usage)

    @classmethod
    def get_usage(cls, data):
        try:
            resources = data['resources']
            resource_disk = {}
            for r in resources:
                if r['name'] == 'disk':
                    resource_disk = r
                    break

            details = {
                'usage': float(resource_disk['used']),
                'total': resource_disk['allocated'],
                'unit': resource_disk['unit'],
            }
        except (IndexError, KeyError):
            return {}


        percent = get_bootstraped_percent(
            details['usage'],
            details['total']
        )
        details['percent'] = percent

        return details

    @property
    def manager_url(self):
        return musician_settings.URL_DB_PHPMYADMIN


class Domain(OrchestraModel):
    api_name = 'domain'
    param_defaults = {
        "id": None,
        "name": None,
        "records": [],
        "addresses": [],
        "usage": {},
        "websites": [],
        "url": None,
    }

    @classmethod
    def new_from_json(cls, data, **kwargs):
        records = cls.param_defaults.get("records")
        if 'records' in data:
            records = [DomainRecord.new_from_json(record_data) for record_data in data['records']]

        return super().new_from_json(data=data, records=records)

    def __str__(self):
        return self.name


class DomainRecord(OrchestraModel):
    param_defaults = {
        "type": None,
        "value": None,
    }
    def __str__(self):
        return '<%s: %s>' % (self.type, self.value)


class Address(OrchestraModel):
    api_name = 'address'
    verbose_name = _('Mail addresses')
    description = _('Description details for mail addresses page.')
    fields = ('mail_address', 'aliases', 'type', 'type_detail')
    param_defaults = {
        "id": None,
        "name": None,
        "domain": None,
        "mailboxes": [],
        "forward": None,
        'url': None,
    }

    FORWARD = 'forward'
    MAILBOX = 'mailbox'

    def __init__(self, **kwargs):
        self.data = kwargs
        super().__init__(**kwargs)

    def deserialize(self):
        data = {
            'name': self.data['name'],
            'domain': self.data['domain']['url'],
            'mailboxes': [mbox['url'] for mbox in self.data['mailboxes']],
            'forward': self.data['forward'],
        }
        return data

    @property
    def aliases(self):
        return [
            name + '@' + self.data['domain']['name'] for name in self.data['names'][1:]
        ]

    @property
    def full_address_name(self):
        return "{}@{}".format(self.name, self.domain['name'])

    @property
    def type(self):
        if self.data['forward']:
            return self.FORWARD
        return self.MAILBOX

    @property
    def type_detail(self):
        if self.type == self.FORWARD:
            return self.data['forward']

        # retrieve mailbox usage
        try:
            resource = self.data['mailboxes'][0]['resources']
            resource_disk = {}
            for r in resource:
                if r['name'] == 'disk':
                    resource_disk = r
                    break

            mailbox_details = {
                'usage': float(resource_disk['used']),
                'total': resource_disk['allocated'],
                'unit': resource_disk['unit'],
            }

            percent = get_bootstraped_percent(
                mailbox_details['used'],
                mailbox_details['total']
            )
            mailbox_details['percent'] = percent
        except (IndexError, KeyError):
            mailbox_details = {}
        return mailbox_details


class Mailbox(OrchestraModel):
    api_name = 'mailbox'
    verbose_name = _('Mailbox')
    description = _('Description details for mailbox page.')
    fields = ('name', 'filtering', 'addresses', 'active')
    param_defaults = {
        'id': None,
        'name': None,
        'filtering': None,
        'is_active': True,
        'addresses': [],
        'url': None,
    }

    @classmethod
    def new_from_json(cls, data, **kwargs):
        addresses = [Address.new_from_json(addr) for addr in data.get('addresses', [])]
        return super().new_from_json(data=data, addresses=addresses)

    def deserialize(self):
        data = {
            'addresses': [addr.url for addr in self.addresses],
        }
        return data


class MailinglistService(OrchestraModel):
    api_name = 'mailinglist'
    verbose_name = _('Mailing list')
    description = _('Description details for mailinglist page.')
    fields = ('name', 'status', 'address_name', 'admin_email', 'configure')
    param_defaults = {
        'name': None,
        'is_active': True,
        'admin_email': None,
    }

    def __init__(self, **kwargs):
        self.data = kwargs
        super().__init__(**kwargs)

    @property
    def address_name(self):
        address_domain = self.data['address_domain']
        if address_domain is None:
            return self.data['address_name']
        return "{}@{}".format(self.data['address_name'], address_domain['name'])

    @property
    def manager_url(self):
        return musician_settings.URL_MAILTRAIN


class SaasService(OrchestraModel):
    api_name = 'saas'
    verbose_name = _('Software as a Service (SaaS)')
    description = _('Description details for SaaS page.')
    param_defaults = {
        'name': None,
        'service': None,
        'is_active': True,
        'data': {},
    }


    @property
    def manager_url(self):
        URLS = {
            'gitlab': musician_settings.URL_SAAS_GITLAB,
            'owncloud': musician_settings.URL_SAAS_OWNCLOUD,
            'wordpress': musician_settings.URL_SAAS_WORDPRESS,
        }

        return URLS.get(self.service, '#none')


class WebSite(OrchestraModel):
    api_name = 'website'
    param_defaults = {
        "id": None,
        "name": None,
        "protocol": None,
        "is_active": True,
        "domains": [],
        "contents": [],
    }

    @classmethod
    def new_from_json(cls, data, **kwargs):
        domains = cls.param_defaults.get("domains")
        if 'domains' in data:
            domains = [Domain.new_from_json(domain_data) for domain_data in data['domains']]

        return super().new_from_json(data=data, domains=domains)
