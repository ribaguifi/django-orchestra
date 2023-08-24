from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from orchestra.contrib.orchestration.models import Server
from orchestra.contrib.websites.models import Website
from orchestra.settings import WEB_SERVERS

class IsActiveListFilter(SimpleListFilter):
    title = _("is active")
    parameter_name = 'active'
    
    def lookups(self, request, model_admin):
        return (
            ('True', _("Yes")),
            ('False', _("No")),
            ('account', _("Account disabled")),
            ('object', _("Object disabled")),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(is_active=True, account__is_active=True)
        elif self.value() == 'False':
            return queryset.filter(Q(is_active=False) | Q(account__is_active=False))
        elif self.value() == 'account':
            return queryset.filter(account__is_active=False)
        elif self.value() == 'object':
            return queryset.filter(is_active=False)
        return queryset

class HasTipeServerFilter(SimpleListFilter):
    title = _("has type server")
    parameter_name = 'has_servers'

    def lookups(self, request, model_admin):
        return [ (x.id, x.name) for x in Server.objects.filter(name__in=WEB_SERVERS) ]
    
    def queryset(self, request, queryset):
        if self.value() is not None:
            serverWebsites = Website.objects.filter(target_server=self.value())
            return queryset.filter(id__in=[ x.account.id for x in serverWebsites ] )
        return queryset        