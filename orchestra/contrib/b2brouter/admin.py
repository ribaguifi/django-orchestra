from django.contrib import admin
from django.utils import timezone
from orchestra.contrib.b2brouter.models import B2BContact

from orchestra.contrib.b2brouter.management.commands.sync_contacts import Command
from django.urls import reverse
from django.utils.html import format_html

@admin.register(B2BContact)
class B2BContactAdmin(admin.ModelAdmin):
    list_display = ("pk", "orchestra_contact_link", "remote_id", "status", "last_synced_at", "message")
    search_fields = ("pk", "orchestra_contact__name", "orchestra_contact__vat", "remote_id")
    list_filter = ("status",)

    actions = ["sync_push_to_remote"]

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
