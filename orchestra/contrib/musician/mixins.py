from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import ContextMixin

from orchestra import get_version

from . import api
from .settings import LANGUAGES
from .auth import SESSION_KEY_TOKEN


class CustomContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # generate services menu items
        services_menu = [
            {'icon': 'fas fa-home', 'pattern_name': 'musician:dashboard', 'title': _('Dashboard')},
            {'icon': 'fas fa-globe', 'pattern_name': 'musician:domain-list', 'title': _('Domains')},
            {'icon': 'fas fa-envelope', 'pattern_name': 'musician:address-list', 'title': _('Mails')},
            {'icon': 'fas fa-mail-bulk', 'pattern_name': 'musician:mailing-lists', 'title': _('Mailing lists')},
            {'icon': 'fas fa-database', 'pattern_name': 'musician:database-list', 'title': _('Databases')},
            {'icon': 'fas fa-fire', 'pattern_name': 'musician:saas-nextcloud-list', 'title': _('SaaS')},
            {'icon': 'fas fa-cloud', 'pattern_name': 'musician:saas-nextcloud-list', 'title': _('Nextcloud'), 'indent': True},
            {'icon': 'fab fa-wordpress', 'pattern_name': 'musician:saas-wordpress-list', 'title': _('Community WP'), 'indent': True},
            {'icon': 'fas fa-globe', 'pattern_name': 'musician:website-list', 'title': _('Websites')},
            {'icon': 'fas fa-folder', 'pattern_name': 'musician:webapp-list', 'title': _('Webapps'), 'indent': True},
            {'icon': 'fas fa-user', 'pattern_name': 'musician:systemuser-list', 'title': _('Users'), 'indent': True},
        ]
        context.update({
            'services_menu': services_menu,
            'version': get_version(),
            # 'languages': settings.LANGUAGES,
            'languages': LANGUAGES,
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


class UserTokenRequiredMixin(LoginRequiredMixin):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.orchestra = api.OrchestraConnector(self.request)
        context.update({
            'profile': self.orchestra.retrieve_profile(),
        })
        return context
