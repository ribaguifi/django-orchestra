from django.conf import settings
from django.core.management.base import BaseCommand

from b2brouter_client import ApiErrorException

from orchestra.contrib.b2brouter.api import fetch_remote_contacts, get_api_client
from orchestra.contrib.b2brouter.models import B2BContact


class Command(BaseCommand):
    help = "Reset b2b sync contacts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Skip confirmation prompt and assume yes.",
        )

    def set_options(self, **options):
        self.verbosity = options.get("verbosity", 1)

    def handle(self, *args, **options):
        self.set_options(**options)
        qs = B2BContact.objects.all()
        count = qs.count()

        if not options["noinput"]:
            confirm = input(
                f"This will reset the sync status of {count} contacts. Are you sure? (y/N) "
            )
            if confirm.lower() != "y":
                self.stdout.write("Operation cancelled.")
                return

        # reset the sync status
        qs.update(remote_id=None, status=B2BContact.Status.PENDING, message="")
        self.stdout.write(f"Reset the sync status of {count} contacts.")

        # delete data on remote via B2B API
        # First, retrieve all existing contacts on API to get their remote IDs
        self.api = get_api_client()

        remote_contacts = fetch_remote_contacts(self.api, limit=500)

        self.stdout.write(f"Found {len(remote_contacts)} remote contacts to delete.")
        for remote_contact in remote_contacts:
            try:
                self.api.contacts.delete(id=remote_contact.id)
                if self.verbosity >= 1:
                    self.stdout.write(
                        f"Deleted remote contact with ID {remote_contact.id}"
                    )
            except ApiErrorException as e:
                if self.verbosity >= 1:
                    self.stderr.write(
                        f"Failed to delete remote contact with ID {remote_contact.id}: {e}"
                    )
