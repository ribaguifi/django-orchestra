from django.contrib import admin
from django.utils import timezone
from django.db.models import Q
from orchestra.contrib.b2brouter.models import B2BContact

from orchestra.contrib.b2brouter.management.commands.sync_contacts import Command
from django.urls import reverse
from django.utils.html import format_html

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
                Q(remote_id__icontains=term) |
                Q(orchestra_contact__name__icontains=term) |
                Q(orchestra_contact__vat__icontains=term) |
                Q(orchestra_contact__account__username__icontains=term)
            )
            search_query &= term_query

        # Apply the search query
        filtered_queryset = queryset.filter(search_query)

        # Return the filtered queryset and indicate that search was used
        return filtered_queryset, True

    def orchestra_contact_link(self, obj):
        url = reverse('admin:accounts_account_change', args=[obj.orchestra_contact.account.pk])
        return format_html('<a href="{}">{}</a>', url, obj.orchestra_contact)
    orchestra_contact_link.allow_tags = True
    orchestra_contact_link.short_description = "Bill Contact"

    @admin.action(description="Sync selected contacts to remote")
    def sync_push_to_remote(self, request, queryset):
        failed = 0
        updated = 0
        for b2bcontact in queryset:
            # Here you would call the sync logic, for example:
            # contact.sync_to_remote()
            contact = b2bcontact.orchestra_contact

            c = Command()
            c.init_api()

            update = b2bcontact.remote_id is not None
            try:
                c.sync_remote_contact(contact, remote_id=b2bcontact.remote_id, update=update)
            except Exception as e:
                b2bcontact.message = e.body if hasattr(e, 'body') else str(e)
                b2bcontact.save()
                failed += 1
            else:
                updated += 1

        queryset.update(last_synced_at=timezone.now())
        self.message_user(request, f"Synced {updated} contacts to remote. Failed: {failed}.")
