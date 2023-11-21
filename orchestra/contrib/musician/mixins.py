from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import ContextMixin
from django.conf import settings

from orchestra import get_version
from . import api
from .auth import SESSION_KEY_TOKEN


class CustomContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # generate services menu items
        services_menu = [
            {'icon': 'globe-europe', 'pattern_name': 'musician:dashboard', 'title': _('Domains & websites')},
            {'icon': 'envelope', 'pattern_name': 'musician:address-list', 'title': _('Mails')},
            {'icon': 'mail-bulk', 'pattern_name': 'musician:mailing-lists', 'title': _('Mailing lists')},
            {'icon': 'database', 'pattern_name': 'musician:database-list', 'title': _('Databases')},
            {'icon': 'fire', 'pattern_name': 'musician:saas-list', 'title': _('SaaS')},
        ]
        context.update({
            'services_menu': services_menu,
            'version': get_version(),
            'languages': settings.LANGUAGES,
        })

        return context


class ExtendedPaginationMixin:
    paginate_by = 20
    paginate_by_kwarg = 'per_page'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'per_page_values': [5, 10, 20, 50],
            'per_page_param': self.paginate_by_kwarg,
        })
        return context

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get(self.paginate_by_kwarg) or self.paginate_by
        try:
            paginate_by = int(per_page)
        except ValueError:
            paginate_by = self.paginate_by
        return paginate_by


class UserTokenRequiredMixin(UserPassesTestMixin):
    """
    Checks that the request has a token that authenticates him/her.
    If the user is logged adds context variable 'profile' with its information.
    """

    def test_func(self):
        """Check that the user has an authorized token."""
        token = self.request.session.get(SESSION_KEY_TOKEN, None)
        if token is None:
            return False

        # initialize orchestra api orm
        self.orchestra = api.Orchestra(auth_token=token)

        # verify if the token is valid
        if self.orchestra.verify_credentials() is None:
            return False

        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'profile': self.orchestra.retrieve_profile(),
        })
        return context
