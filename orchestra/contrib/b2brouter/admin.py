from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _

from orchestra.contrib.accounts.models import Account
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.b2brouter.management.commands.sync_contacts import Command
from orchestra.contrib.b2brouter.models import B2BContact
from orchestra.contrib.b2brouter.settings import B2BROUTER_API_URL
from orchestra.contrib.b2brouter.signals import sync_remote_invoice
from orchestra.contrib.bills.models import Bill, BillContact


@admin.register(B2BContact)
class B2BContactAdmin(admin.ModelAdmin):
    list_display = ("pk", "orchestra_contact_link", "remote_id", "status", "last_synced_at", "message")
    search_fields = ("remote_id",)
    list_filter = ("status",)

    actions = ["sync_push_to_remote"]

    def get_search_results(self, request, queryset, search_term):
        """
        Custom search implementation to handle OneToOneField relationships.
        Allows searching by remote_id, contact name, and VAT number.
        """
        if not search_term:
            return queryset, False

        # Split search term into individual words for more flexible searching
        search_terms = search_term.strip().split()

        # Build the query for multiple fields
        search_query = Q()

        for term in search_terms:
            term_query = (
                Q(remote_id__icontains=term)
                | Q(orchestra_contact__name__icontains=term)
                | Q(orchestra_contact__vat__icontains=term)
                | Q(orchestra_contact__account__username__icontains=term)
            )
            search_query &= term_query

        # Apply the search query
        filtered_queryset = queryset.filter(search_query)

        # Return the filtered queryset and indicate that search was used
        return filtered_queryset, True

    def orchestra_contact_link(self, obj):
        def bill_contact_representation(contact):
            return contact.name or f"{contact.country}{contact.vat}"

        url = reverse("admin:accounts_account_change", args=[obj.orchestra_contact.account.pk])
        contact = bill_contact_representation(obj.orchestra_contact)

        return format_html('<a href="{}">{}</a>', url, contact)

    orchestra_contact_link.allow_tags = True
    orchestra_contact_link.short_description = "Bill Contact"

    @admin.action(description="Sync selected contacts to remote")
    def sync_push_to_remote(self, request, queryset):
        failed = 0
        updated = 0
        for b2bcontact in queryset:
            cmd = Command()
            cmd.init_api()

            update = b2bcontact.remote_id is not None
            try:
                cmd.sync_remote_contact(b2bcontact, update=update)
            except Exception as e:
                b2bcontact.message = e.body if hasattr(e, "body") else str(e)
                b2bcontact.save()
                failed += 1
            else:
                updated += 1

        queryset.update(last_synced_at=timezone.now())
        self.message_user(request, f"Synced {updated} contacts to remote. Failed: {failed}.")


def b2bcontact_link(obj):
    """Custom column defined in your app."""
    try:
        b2bcontact = obj.billcontact.b2bcontact
    except (BillContact.DoesNotExist, B2BContact.DoesNotExist):
        return "-"

    if not b2bcontact.remote_id:
        if b2bcontact.message:
            return format_html(
                "<span class='error' style='cursor:help' title='{}'>sync {}</span>",
                b2bcontact.message,
                b2bcontact.status,
            )
        return "-"

    url = f"{B2BROUTER_API_URL}/contacts/{b2bcontact.remote_id}"
    return format_html("<a href='{}' target='_blank'>{}</a>", url, b2bcontact.remote_id)


b2bcontact_link.short_description = "B2B contact ID"

# monkey patch Account admin to add B2B contact link
if Account in admin.site._registry:
    account_admin = admin.site._registry[Account]
    account_admin.list_display = list(account_admin.list_display) + [b2bcontact_link]
    setattr(account_admin.__class__, "b2bcontact_link", staticmethod(b2bcontact_link))


@transaction.atomic
def sync_bills(modeladmin, request, queryset):
    """Sync selected bills with external system"""

    for bill in queryset:
        modeladmin.log_change(request, bill, "Synchronized with external system")
        try:
            sync_remote_invoice(bill)
        except B2BSyncError as e:
            messages.error(
                request,
                _("Failed to sync bill %(bill)s: %(error)s")
                % {
                    "bill": bill.number,
                    "error": str(e),
                },
            )
            continue

    messages.success(request, _("Selected bills have been synchronized with the external system."))


sync_bills.tool_description = _("Sync Bills")
sync_bills.url_name = "sync_bills"

# TODO(@slamora): FIX monkey patching Bill admin to add sync_bills action
# if Bill in admin.site._registry:
#     bill_admin = admin.site._registry[Bill]
#     # Get current actions, handling both list and tuple cases
#     if hasattr(bill_admin, "actions") and bill_admin.actions:
#         if isinstance(bill_admin.actions, (list, tuple)):
#             current_actions = list(bill_admin.actions)
#         else:
#             current_actions = []
#     else:
#         current_actions = []

#     # Add the sync_bills action
#     current_actions.append(sync_bills)
#     bill_admin.actions = current_actions

#     # Clear the cached actions to force re-evaluation
#     if hasattr(bill_admin, "_actions"):
#         bill_admin._actions = None
