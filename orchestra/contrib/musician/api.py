import urllib.parse

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import Http404
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from .models import (Address, DatabaseService, Domain, Mailbox, SaasService,
                     UserAccount, WebSite)

DOMAINS_PATH = 'domains/'
TOKEN_PATH = '/api-token-auth/'

API_PATHS = {
    # auth
    'token-auth': '/api-token-auth/',
    'my-account': 'accounts/',

    # services
    'database-list': 'databases/',
    'domain-list': 'domains/',
    'domain-detail': 'domains/{pk}/',
    'address-list': 'addresses/',
    'address-detail': 'addresses/{pk}/',
    'mailbox-list': 'mailboxes/',
    'mailbox-detail': 'mailboxes/{pk}/',
    'mailbox-password': 'mailboxes/{pk}/set_password/',
    'mailinglist-list': 'lists/',
    'saas-list': 'saas/',
    'website-list': 'websites/',

    # other
    'bill-list': 'bills/',
    'bill-document': 'bills/{pk}/document/',
    'payment-source-list': 'payment-sources/',
}


class Orchestra(object):
    def __init__(self, request, username=None, password=None, **kwargs):
        self.request = request
        self.username = username
        self.user = self.authenticate(self.username, password)

    def build_absolute_uri(self, path_name):
        path = API_PATHS.get(path_name, None)
        if path is None:
            raise NoReverseMatch(
                "Not found API path name '{}'".format(path_name))

        return urllib.parse.urljoin(self.base_url, path)

    def authenticate(self, username, password):
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            return user

        # Return an 'invalid login' error message.
        return None

    def request(self, verb, resource=None, url=None, data=None, render_as="json", querystring=None, raise_exception=True):
        assert verb in ["HEAD", "GET", "POST", "PATCH", "PUT", "DELETE"]
        if resource is not None:
            url = self.build_absolute_uri(resource)
        elif url is None:
            raise AttributeError("Provide `resource` or `url` params")

        if querystring is not None:
            url = "{}?{}".format(url, querystring)

        verb = getattr(self.session, verb.lower())
        headers = {
            "Authorization": "Token {}".format(self.auth_token),
            "Content-Type": "application/json",
        }
        response = verb(url, json=data, headers=headers, allow_redirects=False)

        if raise_exception:
            response.raise_for_status()

        status = response.status_code
        if status < 500 and render_as == "json":
            output = response.json()
        else:
            output = response.content

        return status, output

    def retrieve_service_list(self, service_name, querystring=None):
        pattern_name = '{}-list'.format(service_name)
        if pattern_name not in API_PATHS:
            raise ValueError("Unknown service {}".format(service_name))
        _, output = self.request("GET", pattern_name, querystring=querystring)
        return output

    def retrieve_profile(self):
        status, output = self.request("GET", 'my-account')
        if status >= 400:
            raise PermissionError("Cannot retrieve profile of an anonymous user.")
        return UserAccount.new_from_json(output[0])

    def retrieve_bill_document(self, pk):
        path = API_PATHS.get('bill-document').format_map({'pk': pk})

        url = urllib.parse.urljoin(self.base_url, path)
        status, bill_pdf = self.request("GET", render_as="html", url=url, raise_exception=False)
        if status == 404:
            raise Http404(_("No domain found matching the query"))
        return bill_pdf

    def create_mail_address(self, data):
        resource = '{}-list'.format(Address.api_name)
        return self.request("POST", resource=resource, data=data)

    def retrieve_mail_address(self, pk):
        path = API_PATHS.get('address-detail').format_map({'pk': pk})
        url = urllib.parse.urljoin(self.base_url, path)
        status, data = self.request("GET", url=url, raise_exception=False)
        if status == 404:
            raise Http404(_("No object found matching the query"))

        return Address.new_from_json(data)

    def update_mail_address(self, pk, data):
        path = API_PATHS.get('address-detail').format_map({'pk': pk})
        url = urllib.parse.urljoin(self.base_url, path)
        return self.request("PUT", url=url, data=data)

    def retrieve_mail_address_list(self, querystring=None):
        # retrieve mails applying filters (if any)
        raw_data = self.retrieve_service_list(
            Address.api_name,
            querystring=querystring,
        )

        addresses = [Address.new_from_json(data) for data in raw_data]

        # PATCH to include Pangea addresses not shown by orchestra
        # described on issue #4
        # TODO(@slamora) disabled hacky patch because breaks another funtionalities
        #   XXX Fix it on orchestra instead of here???
        # raw_mailboxes = self.retrieve_mailbox_list()
        # for mailbox in raw_mailboxes:
        #     if mailbox['addresses'] == []:
        #         address_data = {
        #             'names': [mailbox['name']],
        #             'forward': '',
        #             'domain': {
        #                 'name': 'pangea.org.',
        #             },
        #             'mailboxes': [mailbox],
        #         }
        #         pangea_address = Address.new_from_json(address_data)
        #         addresses.append(pangea_address)

        return addresses

    def delete_mail_address(self, pk):
        path = API_PATHS.get('address-detail').format_map({'pk': pk})
        url = urllib.parse.urljoin(self.base_url, path)
        return self.request("DELETE", url=url, render_as=None)

    def create_mailbox(self, data):
        resource = '{}-list'.format(Mailbox.api_name)
        return self.request("POST", resource=resource, data=data, raise_exception=False)

    def retrieve_mailbox(self, pk):
        path = API_PATHS.get('mailbox-detail').format_map({'pk': pk})

        url = urllib.parse.urljoin(self.base_url, path)
        status, data_json = self.request("GET", url=url, raise_exception=False)
        if status == 404:
            raise Http404(_("No mailbox found matching the query"))
        return Mailbox.new_from_json(data_json)

    def update_mailbox(self, pk, data):
        path = API_PATHS.get('mailbox-detail').format_map({'pk': pk})
        url = urllib.parse.urljoin(self.base_url, path)
        status, response = self.request("PATCH", url=url, data=data, raise_exception=False)
        return status, response

    def retrieve_mailbox_list(self):
        mailboxes = self.retrieve_service_list(Mailbox.api_name)
        return [Mailbox.new_from_json(mailbox_data) for mailbox_data in mailboxes]

    def delete_mailbox(self, pk):
        path = API_PATHS.get('mailbox-detail').format_map({'pk': pk})
        url = urllib.parse.urljoin(self.base_url, path)
        # Mark as inactive instead of deleting
        # return self.request("DELETE", url=url, render_as=None)
        return self.request("PATCH", url=url, data={"is_active": False})

    def set_password_mailbox(self, pk, data):
        path = API_PATHS.get('mailbox-password').format_map({'pk': pk})
        url = urllib.parse.urljoin(self.base_url, path)
        status, response = self.request("POST", url=url, data=data, raise_exception=False)
        return status, response


    def retrieve_domain(self, pk):
        path = API_PATHS.get('domain-detail').format_map({'pk': pk})

        url = urllib.parse.urljoin(self.base_url, path)
        status, domain_json = self.request("GET", url=url, raise_exception=False)
        if status == 404:
            raise Http404(_("No domain found matching the query"))
        return Domain.new_from_json(domain_json)

    def retrieve_domain_list(self):
        output = self.retrieve_service_list(Domain.api_name)
        websites = self.retrieve_website_list()

        domains = []
        for domain_json in output:
            # filter querystring
            querystring = "domain={}".format(domain_json['id'])

            # retrieve services associated to a domain
            domain_json['addresses'] = self.retrieve_service_list(
                Address.api_name, querystring)

            # retrieve websites (as they cannot be filtered by domain on the API we should do it here)
            domain_json['websites'] = self.filter_websites_by_domain(websites, domain_json['id'])

            # TODO(@slamora): update when backend provides resource disk usage data
            domain_json['usage'] = {
                # 'usage': 300,
                # 'total': 650,
                # 'unit': 'MB',
                # 'percent': 50,
            }

            # append to list a Domain object
            domains.append(Domain.new_from_json(domain_json))

        return domains

    def retrieve_website_list(self):
        output = self.retrieve_service_list(WebSite.api_name)
        return [WebSite.new_from_json(website_data) for website_data in output]

    def filter_websites_by_domain(self, websites, domain_id):
        matching = []
        for website in websites:
            web_domains = [web_domain.id for web_domain in website.domains]
            if domain_id in web_domains:
                matching.append(website)

        return matching

    def verify_credentials(self):
        """
        Returns:
          A user profile info if the
          credentials are valid, None otherwise.
        """
        status, output = self.request("GET", 'my-account', raise_exception=False)

        if status < 400:
            return output

        return None
