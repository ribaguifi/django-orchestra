import textwrap

from django import forms
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.contrib.admin.util import unquote
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.safestring import mark_safe

from orchestra.admin import ExtendedModelAdmin, ChangePasswordAdminMixin
from orchestra.admin.utils import wrap_admin_view
from orchestra.apps.accounts.admin import SelectAccountAdminMixin
from orchestra.apps.accounts.filters import IsActiveListFilter
from orchestra.forms import UserCreationForm, UserChangeForm

from . import settings
from .actions import grant_permission, delete_selected
from .filters import IsMainListFilter
from .forms import SystemUserCreationForm, SystemUserChangeForm
from .models import SystemUser


class SystemUserAdmin(ChangePasswordAdminMixin, SelectAccountAdminMixin, ExtendedModelAdmin):
    list_display = (
        'username', 'account_link', 'shell', 'display_home', 'display_active', 'display_main'
    )
    list_filter = (IsActiveListFilter, 'shell', IsMainListFilter)
    fieldsets = (
        (None, {
            'fields': ('username', 'password', 'account_link', 'is_active')
        }),
        (_("System"), {
            'fields': ('shell', ('home', 'directory'), 'groups'),
        }),
    )
    add_fieldsets = (
        (None, {
            'fields': ('account_link', 'username', 'password1', 'password2')
        }),
        (_("System"), {
            'fields': ('shell', ('home', 'directory'), 'groups'),
        }),
    )
    search_fields = ('username', 'account__username')
    readonly_fields = ('account_link',)
    change_readonly_fields = ('username',)
    filter_horizontal = ('groups',)
    filter_by_account_fields = ('groups',)
    add_form = SystemUserCreationForm
    form = SystemUserChangeForm
    ordering = ('-id',)
    actions = (delete_selected, grant_permission,)
    change_view_actions = actions
    
    def display_main(self, user):
        return user.is_main
    display_main.short_description = _("Main")
    display_main.boolean = True
    
    def display_home(self, user):
        return user.get_home()
    display_home.short_description = _("Home")
    display_home.admin_order_field = 'home'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(SystemUserAdmin, self).get_form(request, obj, **kwargs)
        form.account = self.account
        if obj:
            # Has to be done here and not in the form because of strange phenomenon
            # derived from monkeypatching formfield.widget.render on AccountAdminMinxin,
            # don't ask.
            formfield = form.base_fields['groups']
            formfield.queryset = formfield.queryset.exclude(id=obj.id)
        return form
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_main:
            return False
        return super(SystemUserAdmin, self).has_delete_permission(request, obj)


admin.site.register(SystemUser, SystemUserAdmin)
