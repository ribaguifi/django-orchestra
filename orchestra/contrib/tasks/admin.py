from django.utils.translation import gettext_lazy as _
from orchestra.contrib.djcelery.admin import PeriodicTaskAdmin

from orchestra.admin.utils import admin_date


display_last_run_at = admin_date('last_run_at', short_description=_("Last run"))

PeriodicTaskAdmin.list_display = ('__str__', display_last_run_at, 'total_run_count', 'enabled')
PeriodicTaskAdmin.list_display_links = ('enabled', '__str__')
