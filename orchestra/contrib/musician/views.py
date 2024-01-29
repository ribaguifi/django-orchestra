import logging
import smtplib
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import mail_managers
from django.http import (HttpResponse, HttpResponseNotFound,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.html import format_html
from django.utils.http import is_safe_url
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import (CreateView, DeleteView, FormView,
                                       UpdateView)
from django.views.generic.list import ListView
from requests.exceptions import HTTPError

from orchestra import get_version
from orchestra.contrib.bills.models import Bill
from orchestra.contrib.databases.models import Database
from orchestra.contrib.domains.models import Domain, Record
from orchestra.contrib.lists.models import List
from orchestra.contrib.mailboxes.models import Address, Mailbox
from orchestra.contrib.saas.models import SaaS
from orchestra.utils.html import html_to_pdf

# from .auth import login as auth_login
from .auth import logout as auth_logout
from .forms import (LoginForm, MailboxChangePasswordForm, MailboxCreateForm,
                    MailboxUpdateForm, MailForm, RecordCreateForm,
                    RecordUpdateForm)
from .mixins import (CustomContextMixin, ExtendedPaginationMixin,
                     UserTokenRequiredMixin)
from .models import Address as AddressService
from .models import Bill as BillService
from .models import DatabaseService
from .models import Mailbox as MailboxService
from .models import MailinglistService, SaasService
from .settings import ALLOWED_RESOURCES
from .utils import get_bootstraped_percent

logger = logging.getLogger(__name__)


class DashboardView(CustomContextMixin, UserTokenRequiredMixin, TemplateView):
    template_name = "musician/dashboard.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Dashboard'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domains = self.orchestra.retrieve_domain_list()

        # TODO(@slamora) update when backend supports notifications
        notifications = []

        # show resource usage based on plan definition
        profile_type = context['profile'].type

        # TODO(@slamora) update when backend provides resource usage data
        resource_usage = {
            'mailbox': self.get_mailbox_usage(profile_type),
        }

        support_email = getattr(settings, "USER_SUPPORT_EMAIL", "suport@pangea.org")
        support_email_anchor = format_html(
            "<a href='mailto:{}'>{}</a>",
            support_email,
            support_email,
        )
        context.update({
            'domains': domains,
            'resource_usage': resource_usage,
            'notifications': notifications,
            "support_email_anchor": support_email_anchor,
        })

        return context

    def get_mailbox_usage(self, profile_type):
        allowed_mailboxes = ALLOWED_RESOURCES[profile_type]['mailbox']
        total_mailboxes = len(self.orchestra.retrieve_mailbox_list())
        mailboxes_left = allowed_mailboxes - total_mailboxes

        alert = ''
        if mailboxes_left < 0:
            alert = format_html("<span class='text-danger'>{} extra mailboxes</span>", mailboxes_left * -1)
        elif mailboxes_left <= 1:
            alert = format_html("<span class='text-warning'>{} mailbox left</span>", mailboxes_left)

        return {
            'verbose_name': _('Mailbox usage'),
            'data': {
                'usage': total_mailboxes,
                'total': allowed_mailboxes,
                'alert': alert,
                'unit': 'mailboxes',
                'percent': get_bootstraped_percent(total_mailboxes, allowed_mailboxes),
            },
        }


class ProfileView(CustomContextMixin, UserTokenRequiredMixin, TemplateView):
    template_name = "musician/profile.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('User profile'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update({
            'payment': user.paymentsources.first(),
            'preferred_language_code': user.language.lower(),
        })

        return context


def profile_set_language(request, code):
    # set user language as active language

    if any(x[0] == code for x in settings.LANGUAGES):
        user_language = code
        translation.activate(user_language)

        redirect_to = request.GET.get('next', '')
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        if not url_is_safe:
            redirect_to = reverse_lazy(settings.LOGIN_REDIRECT_URL)

        response = HttpResponseRedirect(redirect_to)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)

        return response
    else:
        response = HttpResponseNotFound('Languague not found')
        return response


class ServiceListView(CustomContextMixin, ExtendedPaginationMixin, UserTokenRequiredMixin, ListView):
    """Base list view to all services"""
    model = None
    template_name = "musician/service_list.html"

    def get_queryset(self):
        if self.model is None :
            raise ImproperlyConfigured(
                "ServiceListView requires definiton of 'model' attribute")

        queryfilter = self.get_queryfilter()
        qs = self.model.objects.filter(account=self.request.user, **queryfilter)

        return qs

    def get_queryfilter(self):
        """Does nothing by default. Should be implemented on subclasses"""
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            # TODO(@slamora): check where is used on the template
            'service': self.model.__name__,
        })
        return context


class BillingView(ServiceListView):
    service_class = BillService
    model = Bill
    template_name = "musician/billing.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Billing'),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.order_by("-created_on")
        return qs




class BillDownloadView(CustomContextMixin, UserTokenRequiredMixin, View):
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Download bill'),
    }

    def get_object(self):
        return get_object_or_404(
            Bill.objects.filter(account=self.request.user),
            pk=self.kwargs.get('pk')
        )

    def get(self, request, *args, **kwargs):
        # NOTE: this is a copy of method document() on orchestra.contrib.bills.api.BillViewSet
        bill = self.get_object()

        # TODO(@slamora): implement download as PDF, now only HTML is reachable via link
        content_type = request.headers.get('accept')
        if content_type == 'application/pdf':
            pdf = html_to_pdf(bill.html or bill.render())
            return HttpResponse(pdf, content_type='application/pdf')
        else:
            return HttpResponse(bill.html or bill.render())


class AddressListView(ServiceListView):
    service_class = AddressService
    model = Address
    template_name = "musician/address_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mail addresses'),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.order_by("domain", "name")
        return qs

    def get_queryfilter(self):
        """Retrieve query params (if any) to filter queryset"""
        domain_id = self.request.GET.get('domain')
        if domain_id:
            return {"domain": domain_id}

        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain_id = self.request.GET.get('domain')
        if domain_id:
            qs = Domain.objects.filter(account=self.request.user)
            context.update({
                'active_domain': get_object_or_404(qs, pk=domain_id)
            })
        context['mailboxes'] = Mailbox.objects.filter(account=self.request.user)
        return context


class MailCreateView(CustomContextMixin, UserTokenRequiredMixin, CreateView):
    service_class = AddressService
    model = Address
    template_name = "musician/address_form.html"
    form_class = MailForm
    success_url = reverse_lazy("musician:address-list")
    extra_context = {'service': service_class}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class MailUpdateView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    service_class = AddressService
    model = Address
    template_name = "musician/address_form.html"
    form_class = MailForm
    success_url = reverse_lazy("musician:address-list")
    extra_context = {'service': service_class}

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class AddressDeleteView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    template_name = "musician/address_check_delete.html"
    model = Address
    success_url = reverse_lazy("musician:address-list")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)


class MailingListsView(ServiceListView):
    service_class = MailinglistService
    model = List
    template_name = "musician/mailinglist_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mailing lists'),
    }

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain_id = self.request.GET.get('domain')
        if domain_id:
            qs = Domain.objects.filter(account=self.request.user)
            context.update({
                'active_domain': get_object_or_404(qs, pk=domain_id)
            })
        return context

    def get_queryfilter(self):
        """Retrieve query params (if any) to filter queryset"""
        domain_id = self.request.GET.get('domain')
        if domain_id:
            return {"address_domain_id": domain_id}

        return {}


class MailboxListView(ServiceListView):
    service_class = MailboxService
    model = Mailbox
    template_name = "musician/mailbox_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mailboxes'),
    }


class MailboxCreateView(CustomContextMixin, UserTokenRequiredMixin, CreateView):
    service_class = MailboxService
    model = Mailbox
    template_name = "musician/mailbox_form.html"
    form_class = MailboxCreateForm
    success_url = reverse_lazy("musician:mailbox-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'extra_mailbox': self.is_extra_mailbox(context['profile']),
            'service': self.service_class,
        })
        return context

    def is_extra_mailbox(self, profile):
        number_of_mailboxes = len(self.orchestra.retrieve_mailbox_list())
        # TODO(@slamora): how to retrieve allowed mailboxes?
        allowed_mailboxes = 2   # TODO(@slamora): harcoded value
        return number_of_mailboxes >= allowed_mailboxes
        # return number_of_mailboxes >= profile.allowed_resources('mailbox')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

class MailboxUpdateView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    service_class = MailboxService
    model = Mailbox
    template_name = "musician/mailbox_form.html"
    form_class = MailboxUpdateForm
    success_url = reverse_lazy("musician:mailbox-list")
    extra_context = {'service': service_class}

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)


class MailboxDeleteView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    model = Mailbox
    template_name = "musician/mailbox_check_delete.html"
    success_url = reverse_lazy("musician:mailbox-list")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        self.notify_managers(self.object)
        return response

    def notify_managers(self, mailbox):
        user = self.request.user
        subject = f"Mailbox '{mailbox.name}' ({mailbox.id}) deleted | Musician"
        content = (
            "User {} ({}) has deleted its mailbox {} ({}) via musician.\n"
            "The mailbox has been marked as inactive but has not been removed."
        ).format(user.username, user.full_name, mailbox.id, mailbox.name)

        try:
            mail_managers(subject, content, fail_silently=False)
        except (smtplib.SMTPException, ConnectionRefusedError):
            logger.error("Error sending email to managers", exc_info=True)


class MailboxChangePasswordView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    template_name = "musician/mailbox_change_password.html"
    model = Mailbox
    form_class = MailboxChangePasswordForm
    success_url = reverse_lazy("musician:mailbox-list")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)


class DatabasesView(ServiceListView):
    template_name = "musician/databases.html"
    model = Database
    service_class = DatabaseService
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Databases'),
    }


class SaasListView(ServiceListView):
    service_class = SaasService
    model = SaaS
    template_name = "musician/saas_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Software as a Service'),
    }


class DomainDetailView(CustomContextMixin, UserTokenRequiredMixin, DetailView):
    template_name = "musician/domain_detail.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Domain details'),
    }

    def get_queryset(self):
        return Domain.objects.filter(account=self.request.user)


class DomainAddRecordView(CustomContextMixin, UserTokenRequiredMixin, CreateView):
    model = Record
    form_class = RecordCreateForm
    template_name = "musician/record_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        domain = get_object_or_404(Domain, account=self.request.user, pk=self.kwargs["pk"])
        kwargs['domain'] = domain
        return kwargs

    def get_success_url(self):
        return reverse_lazy("musician:domain-detail", kwargs={"pk": self.kwargs["pk"]})


class DomainUpdateRecordView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    model = Record
    form_class = RecordUpdateForm
    template_name = "musician/record_form.html"
    pk_url_kwarg = "record_pk"

    def get_queryset(self):
        qs = Record.objects.filter(domain__account=self.request.user, domain=self.kwargs["pk"])
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:domain-detail", kwargs={"pk": self.kwargs["pk"]})


class DomainDeleteRecordView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    model = Record
    template_name = "musician/record_check_delete.html"
    pk_url_kwarg = "record_pk"

    def get_queryset(self):
        qs = Record.objects.filter(domain__account=self.request.user, domain=self.kwargs["pk"])
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:domain-detail", kwargs={"pk": self.kwargs["pk"]})


class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('musician:dashboard')
    redirect_field_name = 'next'
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Login'),
        'version': get_version(),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """Security check complete. Log the user in."""

        # set user language as active language
        user_language = form.user.language
        translation.activate(user_language)

        response = HttpResponseRedirect(self.get_success_url())
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)

        return response

    def get_success_url(self):
        url = self.get_redirect_url()
        return url or self.success_url

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, '')
        )
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            self.redirect_field_name: self.get_redirect_url(),
            **(self.extra_context or {})
        })
        return context


class LogoutView(RedirectView):
    """
    Log out the user.
    """
    permanent = False
    pattern_name = 'musician:login'

    def get_redirect_url(self, *args, **kwargs):
        """
        Logs out the user.
        """
        auth_logout(self.request)
        return super().get_redirect_url(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Logout may be done via POST."""
        return self.get(request, *args, **kwargs)
