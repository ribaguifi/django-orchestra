import logging
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from b2brouter_client import ApiErrorException

from orchestra.contrib.accounts.models import Account
from orchestra.contrib.b2brouter.api import sync_remote_contact
from orchestra.contrib.b2brouter.exceptions import B2BSyncError
from orchestra.contrib.b2brouter.management.commands.reset_contacts import (
    Command as ResetContactsCommand,
)
from orchestra.contrib.b2brouter.management.commands.sync_contacts import (
    Command as SyncContactsCommand,
)
from orchestra.contrib.b2brouter.models import B2BContact, B2BContactBinding
from orchestra.contrib.bills.models import BillContact
from orchestra.contrib.contacts.models import Contact


class ListWithMeta(list):
    """A list that also has a .meta attribute for mocking API responses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta = {"total_count": len(self)}


class B2BContactTestMixin:
    """Mixin providing helper methods for B2BRouter contact tests."""

    def create_account(self, username="test_account", type="INDIVIDUAL"):
        """Create a test Account."""
        return Account.objects.create(
            username=username,
            email=f"{username}@example.com",
            full_name="Test Account Name",
            type=type,
        )

    def create_bill_contact(self, account=None, vat="ES12345678A", name="Test Company"):
        """Create a test BillContact with associated Account."""
        if not account:
            account = self.create_account()
        return BillContact.objects.create(
            account=account,
            name=name,
            country="ES",
            vat=vat,
            address="Test Address 123",
            city="Madrid",
            zipcode="28001",
        )

    def create_contact_with_billing_email(self, account=None):
        """Create a Contact with BILLING email usage."""
        if not account:
            account = self.create_account()
        return Contact.objects.create(
            account=account,
            short_name=f"{account.username}_contact",
            full_name=f"Billing Contact for {account.username}",
            email=f"billing@{account.username}.example.com",
            email_usage=Contact.BILLING,
            phone="+1234567890",
        )

    def create_b2b_contact(self, bill_contact=None, remote_id=None, status=None):
        """Create a test B2BContact."""
        if not bill_contact:
            bill_contact = self.create_bill_contact()

        if status is None:
            status = B2BContact.Status.PENDING

        vat_key = f"{bill_contact.country}:{bill_contact.vat.replace('-', '').replace(' ', '').replace('.', '').upper()}"

        b2b_contact, _ = B2BContact.objects.get_or_create(
            vat_key=vat_key,
            defaults={
                "remote_id": remote_id,
                "status": status,
            },
        )
        b2b_contact.remote_id = remote_id
        b2b_contact.status = status
        b2b_contact.save(update_fields=["remote_id", "status", "last_synced_at"])

        B2BContactBinding.objects.update_or_create(
            bill_contact=bill_contact,
            defaults={"b2b_contact": b2b_contact},
        )
        return b2b_contact


class ResetContactsCommandTest(B2BContactTestMixin, TestCase):
    """Tests for reset_contacts management command."""

    def setUp(self):
        super().setUp()
        # Patch signal handler to prevent unwanted sync attempts when creating BillContact
        self.signal_patcher = mock.patch(
            "orchestra.contrib.b2brouter.signals.sync_remote_contact"
        )
        self.mock_sync_signal = self.signal_patcher.start()
        self.addCleanup(self.signal_patcher.stop)
        # Create test contacts (one per account due to unique constraint)
        self.account1 = self.create_account(username="account1")
        self.account2 = self.create_account(username="account2")
        self.contact1 = self.create_bill_contact(account=self.account1)
        self.contact2 = self.create_bill_contact(
            account=self.account2, vat="ES87654321B", name="Another Company"
        )
        self.b2b_contact1 = self.create_b2b_contact(
            self.contact1, remote_id=100, status=B2BContact.Status.SYNCED
        )
        self.b2b_contact2 = self.create_b2b_contact(
            self.contact2, remote_id=101, status=B2BContact.Status.SYNCED
        )

    def test_reset_contacts_resets_sync_status(self):
        """Test that reset_contacts command resets sync status to PENDING."""
        # Verify initial state
        self.assertEqual(
            B2BContact.objects.filter(status=B2BContact.Status.SYNCED).count(), 2
        )
        self.assertTrue(self.b2b_contact1.remote_id)

        # Reset contacts with --noinput flag
        with mock.patch("orchestra.contrib.b2brouter.api.get_api_client") as mock_api:
            mock_client = mock.MagicMock()
            mock_api.return_value = mock_client

            # Mock contacts.list to return proper mock with meta attribute
            mock_list_response = mock.MagicMock()
            mock_list_response.__iter__ = mock.MagicMock(return_value=iter([]))
            mock_list_response.meta = {"total_count": 0}
            mock_client.contacts.list.return_value = mock_list_response

            call_command("reset_contacts", "--noinput")

        # Verify status was reset
        self.b2b_contact1.refresh_from_db()
        self.b2b_contact2.refresh_from_db()
        self.assertEqual(self.b2b_contact1.status, B2BContact.Status.PENDING)
        self.assertEqual(self.b2b_contact2.status, B2BContact.Status.PENDING)
        self.assertIsNone(self.b2b_contact1.remote_id)
        self.assertIsNone(self.b2b_contact2.remote_id)

    def test_reset_contacts_verbosity_default(self):
        """Test that reset_contacts command respects default verbosity."""
        out = StringIO()
        with mock.patch("orchestra.contrib.b2brouter.api.get_api_client") as mock_api:
            mock_client = mock.MagicMock()
            mock_api.return_value = mock_client

            # Mock contacts.list to return proper mock with meta attribute
            mock_list_response = mock.MagicMock()
            mock_list_response.__iter__ = mock.MagicMock(return_value=iter([]))
            mock_list_response.meta = {"total_count": 0}
            mock_client.contacts.list.return_value = mock_list_response

            call_command("reset_contacts", "--noinput", stdout=out)

        output = out.getvalue()
        self.assertIn("Reset the sync status of 2 contacts", output)
        self.assertIn("Found 0 remote contacts to delete", output)

    def test_reset_contacts_with_confirmation_decline(self):
        """Test that reset_contacts respects user confirmation when declined."""
        out = StringIO()
        with mock.patch("builtins.input", return_value="n"):
            call_command("reset_contacts", stdout=out)

        output = out.getvalue()
        self.assertIn("Operation cancelled", output)

        # Verify contacts were not reset
        self.b2b_contact1.refresh_from_db()
        self.assertEqual(self.b2b_contact1.status, B2BContact.Status.SYNCED)
        self.assertEqual(self.b2b_contact1.remote_id, 100)

    def test_reset_contacts_deletes_remote_contacts(self):
        """Test that reset_contacts deletes remote contacts via API."""
        remote_contact_mock = mock.MagicMock()
        remote_contact_mock.id = 100

        with mock.patch(
            "orchestra.contrib.b2brouter.management.commands.reset_contacts.fetch_remote_contacts"
        ) as mock_fetch:
            mock_fetch.return_value = ListWithMeta([remote_contact_mock])

            with mock.patch(
                "orchestra.contrib.b2brouter.management.commands.reset_contacts.get_api_client"
            ) as mock_get_api:
                mock_client = mock.MagicMock()
                mock_get_api.return_value = mock_client

                call_command("reset_contacts", "--noinput")

                # Verify delete was called
                mock_client.contacts.delete.assert_called_with(id=100)


class SyncContactsCommandTest(B2BContactTestMixin, TestCase):
    """Tests for sync_contacts management command."""

    def setUp(self):
        super().setUp()
        self.account = self.create_account()
        self.contact = self.create_bill_contact(account=self.account)
        # Patch signal handler to prevent unwanted sync attempts when creating BillContact
        self.signal_patcher = mock.patch(
            "orchestra.contrib.b2brouter.signals.sync_remote_contact"
        )
        self.mock_sync_signal = self.signal_patcher.start()
        self.addCleanup(self.signal_patcher.stop)

    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.fetch_remote_contacts"
    )
    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.get_api_client"
    )
    def test_sync_contacts_creates_new_contact(self, mock_get_api, mock_fetch):
        """Test that sync_contacts creates new remote contacts."""
        # Create a billing contact for the BillContact so sync will try to process it
        self.billing_contact = self.create_contact_with_billing_email(
            account=self.account
        )

        mock_client = mock.MagicMock()
        mock_get_api.return_value = mock_client

        # Mock fetch_remote_contacts to return empty (no existing remote contacts)
        mock_fetch.return_value = ListWithMeta([])

        # Mock the create response with remote_id
        mock_response = mock.MagicMock()
        mock_response.id = 999
        mock_client.contacts.create.return_value = mock_response

        out = StringIO()
        call_command("sync_contacts", "--all", stdout=out)

        # Verify create was called
        mock_client.contacts.create.assert_called()

    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.fetch_remote_contacts"
    )
    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.get_api_client"
    )
    def test_sync_contacts_updates_existing_contact(self, mock_get_api, mock_fetch):
        """Test that sync_contacts updates existing remote contacts."""
        # Create existing B2BContact with remote_id
        b2b_contact = self.create_b2b_contact(self.contact, remote_id=100)

        # Create a billing contact so sync will work
        self.billing_contact = self.create_contact_with_billing_email(
            account=self.account
        )

        mock_client = mock.MagicMock()
        mock_get_api.return_value = mock_client

        # Mock fetch_remote_contacts to return empty
        mock_fetch.return_value = ListWithMeta([])

        out = StringIO()
        call_command("sync_contacts", "--all", stdout=out)

        # Verify update was called
        mock_client.contacts.update.assert_called()

    def test_retrieve_local_contacts_excludes_friend_accounts(self):
        """Test that FRIEND accounts are not returned for B2B sync."""
        friend_account = self.create_account(username="friend_account", type="FRIEND")
        friend_contact = self.create_bill_contact(account=friend_account)

        command = SyncContactsCommand()
        queryset = command.retrieve_local_contacts()

        self.assertIn(self.contact, queryset)
        self.assertNotIn(friend_contact, queryset)

    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.fetch_remote_contacts"
    )
    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.get_api_client"
    )
    def test_sync_contacts_skips_inconsistent_duplicate_vat(
        self, mock_get_api, mock_fetch
    ):
        """Duplicated VAT with inconsistent billing data should be skipped and warned."""
        account2 = self.create_account(username="dup_vat_inconsistent")
        contact2 = self.create_bill_contact(
            account=account2,
            vat=self.contact.vat,
            name="Duplicate VAT Contact",
        )
        contact2.address = "Different Address"
        contact2.save(update_fields=["address"])

        self.create_contact_with_billing_email(account=self.account)
        self.create_contact_with_billing_email(account=account2)

        mock_client = mock.MagicMock()
        mock_get_api.return_value = mock_client
        mock_fetch.return_value = ListWithMeta([])

        out = StringIO()
        err = StringIO()
        call_command("sync_contacts", "--all", stdout=out, stderr=err)

        mock_client.contacts.create.assert_not_called()
        self.assertIn("inconsistent billing data", err.getvalue())

        shared = B2BContact.objects.get(vat_key="ES:ES12345678A")
        self.assertEqual(shared.status, B2BContact.Status.WARNING)
        self.assertIn("Inconsistent billing data", shared.message)
        self.assertEqual(shared.bill_contact_bindings.count(), 2)

    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.fetch_remote_contacts"
    )
    @mock.patch(
        "orchestra.contrib.b2brouter.management.commands.sync_contacts.get_api_client"
    )
    def test_sync_contacts_syncs_duplicate_vat_only_once_when_consistent(
        self, mock_get_api, mock_fetch
    ):
        """Duplicated VAT with consistent data should trigger a single API create."""
        account2 = self.create_account(username="dup_vat_consistent")
        contact2 = self.create_bill_contact(
            account=account2,
            vat=self.contact.vat,
            name="Duplicate VAT Contact",
        )

        self.create_contact_with_billing_email(account=self.account)
        self.create_contact_with_billing_email(account=account2)

        mock_client = mock.MagicMock()
        mock_get_api.return_value = mock_client
        mock_fetch.return_value = ListWithMeta([])

        mock_response = mock.MagicMock()
        mock_response.id = 999
        mock_client.contacts.create.return_value = mock_response

        out = StringIO()
        call_command("sync_contacts", "--all", stdout=out)

        mock_client.contacts.create.assert_called_once()
        mock_client.contacts.update.assert_not_called()

        shared = B2BContact.objects.get(vat_key="ES:ES12345678A")
        self.assertEqual(shared.bill_contact_bindings.count(), 2)
        self.assertEqual(self.contact.b2b_binding.b2b_contact_id, shared.id)
        self.assertEqual(contact2.b2b_binding.b2b_contact_id, shared.id)


class SyncRemoteContactApiTest(B2BContactTestMixin, TestCase):
    """Tests for sync_remote_contact API function."""

    def setUp(self):
        super().setUp()
        self.account = self.create_account()
        # Patch signal handler to prevent unwanted sync attempts when creating BillContact
        self.signal_patcher = mock.patch(
            "orchestra.contrib.b2brouter.signals.sync_remote_contact"
        )
        self.mock_sync_signal = self.signal_patcher.start()
        self.addCleanup(self.signal_patcher.stop)
        self.contact = self.create_bill_contact(account=self.account)
        # Create Contact with BILLING email usage for API tests
        self.billing_contact = self.create_contact_with_billing_email(
            account=self.account
        )

    @mock.patch("orchestra.contrib.b2brouter.api.get_api_client")
    def test_sync_remote_contact_creates_new_contact(self, mock_api):
        """Test sync_remote_contact creates remote contact when remote_id is None."""
        mock_client = mock.MagicMock()
        mock_api.return_value = mock_client

        mock_response = mock.MagicMock()
        mock_response.id = 123
        mock_client.contacts.create.return_value = mock_response

        result = sync_remote_contact(self.contact)

        self.assertEqual(result, 123)
        mock_client.contacts.create.assert_called_once()

    @mock.patch("orchestra.contrib.b2brouter.api.get_api_client")
    def test_sync_remote_contact_updates_existing_contact(self, mock_api):
        """Test sync_remote_contact updates remote contact when remote_id exists."""
        # Create existing B2BContact
        b2b_contact = self.create_b2b_contact(self.contact, remote_id=100)

        mock_client = mock.MagicMock()
        mock_api.return_value = mock_client

        result = sync_remote_contact(self.contact)

        self.assertEqual(result, 100)
        mock_client.contacts.update.assert_called_once()
        mock_client.contacts.create.assert_not_called()

    @mock.patch("orchestra.contrib.b2brouter.api.get_api_client")
    def test_sync_remote_contact_raises_on_api_error(self, mock_api):
        """Test sync_remote_contact raises B2BSyncError on API failure."""
        mock_client = mock.MagicMock()
        mock_api.return_value = mock_client

        error_response = mock.MagicMock()
        error_response.body = "API Error"
        mock_client.contacts.create.side_effect = ApiErrorException(error_response)

        with self.assertRaises(B2BSyncError) as context:
            sync_remote_contact(self.contact)

        self.assertIn("Failed to create contact", str(context.exception))

    @mock.patch("orchestra.contrib.b2brouter.api.get_api_client")
    def test_sync_remote_contact_handles_missing_billing_contact(self, mock_api):
        """Test sync_remote_contact raises B2BSyncError when billing contact not found."""
        # Create a BillContact WITHOUT a Contact - don't use billing_contact from setUp
        account = self.create_account(username="account_no_contact")
        bill_contact = self.create_bill_contact(account=account)

        mock_client = mock.MagicMock()
        mock_api.return_value = mock_client

        with self.assertRaises(B2BSyncError) as context:
            sync_remote_contact(bill_contact)

        self.assertIn("No billing contact found", str(context.exception))

    @mock.patch("orchestra.contrib.b2brouter.api.get_api_client")
    def test_sync_remote_contact_sets_status_to_synced(self, mock_api):
        """Test sync_remote_contact sets status to SYNCED after successful sync."""
        mock_client = mock.MagicMock()
        mock_api.return_value = mock_client

        mock_response = mock.MagicMock()
        mock_response.id = 999
        mock_client.contacts.create.return_value = mock_response

        sync_remote_contact(self.contact)

        # Check B2BContact was created/updated with SYNCED status
        b2b_contact = self.contact.b2b_binding.b2b_contact
        self.assertEqual(b2b_contact.status, B2BContact.Status.SYNCED)
        self.assertEqual(b2b_contact.remote_id, 999)

    @mock.patch("orchestra.contrib.b2brouter.api.get_api_client")
    def test_sync_remote_contact_shares_contact_for_same_vat(self, mock_api):
        """BillContacts with same VAT should share a canonical B2BContact."""
        same_vat_account = self.create_account(username="same_vat_account")
        same_vat_contact = self.create_bill_contact(
            account=same_vat_account,
            vat=self.contact.vat,
            name="Same VAT Company",
        )
        self.create_contact_with_billing_email(account=same_vat_account)

        mock_client = mock.MagicMock()
        mock_api.return_value = mock_client

        mock_create_response = mock.MagicMock()
        mock_create_response.id = 777
        mock_client.contacts.create.return_value = mock_create_response

        sync_remote_contact(self.contact)
        sync_remote_contact(same_vat_contact)

        self.assertEqual(B2BContact.objects.count(), 1)
        shared = B2BContact.objects.get()
        self.assertEqual(shared.bill_contact_bindings.count(), 2)
        self.assertEqual(self.contact.b2b_binding.b2b_contact_id, shared.id)
        self.assertEqual(same_vat_contact.b2b_binding.b2b_contact_id, shared.id)


class AdminSyncActionTest(B2BContactTestMixin, TestCase):
    """Tests for admin sync_push_to_remote action."""

    def setUp(self):
        super().setUp()
        # Patch signal handler to prevent unwanted sync attempts when creating BillContact
        self.signal_patcher = mock.patch(
            "orchestra.contrib.b2brouter.signals.sync_remote_contact"
        )
        self.mock_sync_signal = self.signal_patcher.start()
        self.addCleanup(self.signal_patcher.stop)
        self.account = self.create_account()
        self.contact = self.create_bill_contact(account=self.account)
        self.b2b_contact = self.create_b2b_contact(self.contact)

    @mock.patch("orchestra.contrib.b2brouter.admin.sync_remote_contact")
    def test_sync_push_to_remote_calls_api(self, mock_sync):
        """Test sync_push_to_remote action calls sync_remote_contact."""
        from django.contrib.admin.sites import AdminSite
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory

        from orchestra.contrib.b2brouter.admin import B2BContactAdmin

        admin_site = AdminSite()
        admin = B2BContactAdmin(B2BContact, admin_site)

        # Create proper request with messages support
        factory = RequestFactory()
        request = factory.post("/")
        request.session = {}
        request._messages = FallbackStorage(request)

        queryset = B2BContact.objects.all()

        admin.sync_push_to_remote(request, queryset)

        # Verify sync_remote_contact was called
        mock_sync.assert_called()


class SignalHandlerTest(B2BContactTestMixin, TestCase):
    """Tests for bill_contact_saved signal handler."""

    def setUp(self):
        super().setUp()
        # Don't patch signal here - we want to test it
        self.account = self.create_account()

    @mock.patch("orchestra.contrib.b2brouter.signals.sync_remote_contact")
    def test_bill_contact_saved_triggers_sync(self, mock_sync):
        """Test bill_contact_saved signal triggers sync_remote_contact."""
        # Create a BillContact - this should trigger the signal
        contact = BillContact.objects.create(
            account=self.account,
            name="Test Company",
            country="ES",
            vat="ES12345678A",
            address="Test Address",
            city="Madrid",
            zipcode="28001",
        )

        # Verify signal handler was called
        mock_sync.assert_called_with(contact)

    @mock.patch("orchestra.contrib.b2brouter.signals.logger")
    @mock.patch("orchestra.contrib.b2brouter.signals.sync_remote_contact")
    def test_bill_contact_saved_handles_sync_error(self, mock_sync, mock_logger):
        """Test bill_contact_saved signal handles B2BSyncError gracefully."""
        mock_sync.side_effect = B2BSyncError("Sync failed")

        # Create a BillContact - this should trigger the signal
        contact = BillContact.objects.create(
            account=self.account,
            name="Test Company",
            country="ES",
            vat="ES12345678A",
            address="Test Address",
            city="Madrid",
            zipcode="28001",
        )

        # Verify error was logged
        mock_logger.error.assert_called()

    @mock.patch("orchestra.contrib.b2brouter.signals.logger")
    @mock.patch("orchestra.contrib.b2brouter.signals.sync_remote_contact")
    def test_bill_contact_saved_handles_unexpected_error(self, mock_sync, mock_logger):
        """Test bill_contact_saved signal handles unexpected errors gracefully."""
        mock_sync.side_effect = Exception("Unexpected error")

        # Create a BillContact - this should trigger the signal
        contact = BillContact.objects.create(
            account=self.account,
            name="Test Company",
            country="ES",
            vat="ES12345678A",
            address="Test Address",
            city="Madrid",
            zipcode="28001",
        )

        # Verify exception was logged
        mock_logger.exception.assert_called()


class VerbosityOptionTest(B2BContactTestMixin, TestCase):
    """Tests for management command verbosity option handling."""

    def setUp(self):
        super().setUp()
        # Patch signal handler to prevent unwanted sync attempts when creating BillContact
        self.signal_patcher = mock.patch(
            "orchestra.contrib.b2brouter.signals.sync_remote_contact"
        )
        self.mock_sync_signal = self.signal_patcher.start()
        self.addCleanup(self.signal_patcher.stop)
        self.contact = self.create_bill_contact()
        self.b2b_contact = self.create_b2b_contact(self.contact, remote_id=100)

    def test_reset_contacts_set_options_with_verbosity(self):
        """Test set_options method handles verbosity correctly."""
        cmd = ResetContactsCommand()
        cmd.set_options(verbosity=2)
        self.assertEqual(cmd.verbosity, 2)

    def test_reset_contacts_set_options_default_verbosity(self):
        """Test set_options uses default verbosity when not provided."""
        cmd = ResetContactsCommand()
        cmd.set_options()  # No verbosity provided
        self.assertEqual(cmd.verbosity, 1)

    def test_sync_contacts_set_options_with_all_option(self):
        """Test set_options method handles --all flag."""
        cmd = SyncContactsCommand()
        cmd.set_options(all=True, verbosity=1)
        self.assertTrue(cmd.sync_all)
        self.assertEqual(cmd.verbosity, 1)

    def test_sync_contacts_set_options_default_all_option(self):
        """Test set_options uses default for --all flag."""
        cmd = SyncContactsCommand()
        cmd.set_options()  # No all provided
        self.assertFalse(cmd.sync_all)
