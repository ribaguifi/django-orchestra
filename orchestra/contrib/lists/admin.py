from django.contrib import admin
from django.urls import re_path as url
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from orchestra.admin import ExtendedModelAdmin, ChangePasswordAdminMixin
from orchestra.admin.actions import disable, enable
from orchestra.admin.utils import admin_link
from orchestra.contrib.accounts.actions import list_accounts
from orchestra.contrib.accounts.admin import SelectAccountAdminMixin
from orchestra.contrib.accounts.filters import IsActiveListFilter
from orchestra.forms import UserCreationForm, NonStoredUserChangeForm

from . import settings
from .filters import HasCustomAddressListFilter
from .models import List


class ListAdmin(SelectAccountAdminMixin, ExtendedModelAdmin):
    list_display = (
        'name', 'address_name', 'address_domain_link', 'account_link', 'display_active'
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('account_link', 'name', 'is_active')
        }),
        (_("Address"), {
            'classes': ('wide',),
            'fields': (('address_name', 'address_domain'),)
        }),
        (_("Admin"), {
            'classes': ('wide',),
            'fields': ('admin_email',),
        }),
    )
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('account_link', 'name', 'is_active')
        }),
        (_("Address"), {
            'classes': ('wide',),
            'description': _("Additional address besides the default &lt;name&gt;@%s"
                ) % settings.LISTS_DEFAULT_DOMAIN,
            'fields': (('address_name', 'address_domain'),)
        }),
    )
    search_fields = ('name', 'address_name', 'address_domain__name', 'account__username')
    list_filter = (IsActiveListFilter, HasCustomAddressListFilter)
    readonly_fields = ('account_link',)
    change_readonly_fields = ('name',)
    list_select_related = ('account', 'address_domain',)
    filter_by_account_fields = ['address_domain']
    actions = (disable, enable, list_accounts)
    
    address_domain_link = admin_link('address_domain', order='address_domain__name')

admin.site.register(List, ListAdmin)
