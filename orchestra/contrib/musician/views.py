import datetime
import logging
import smtplib

from django.conf import settings
from django.contrib import messages
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
from django.views.generic.edit import DeleteView, FormView
from django.views.generic.list import ListView
from requests.exceptions import HTTPError

from orchestra import get_version
from orchestra.contrib.bills.models import Bill
from orchestra.contrib.domains.models import Domain
from orchestra.contrib.saas.models import SaaS
from orchestra.utils.html import html_to_pdf

# from .auth import login as auth_login
from .auth import logout as auth_logout
from .forms import (LoginForm, MailboxChangePasswordForm, MailboxCreateForm,
                    MailboxUpdateForm, MailForm)
from .mixins import (CustomContextMixin, ExtendedPaginationMixin,
                     UserTokenRequiredMixin)
from .models import Address
from .models import Bill as BillService
from .models import (DatabaseService, Mailbox, MailinglistService,
                     PaymentSource, SaasService)
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
            'disk': {
                'verbose_name': _('Disk usage'),
                'data': {
                    # 'usage': 534,
                    # 'total': 1024,
                    # 'unit': 'MB',
                    # 'percent': 50,
                },
            },
            'traffic': {
                'verbose_name': _('Traffic'),
                'data': {
                    # 'usage': 300,
                    # 'total': 2048,
                    # 'unit': 'MB/month',
                    # 'percent': 25,
                },
            },
            'mailbox': self.get_mailbox_usage(profile_type),
        }

        context.update({
            'domains': domains,
            'resource_usage': resource_usage,
            'notifications': notifications,
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
        try:
            pay_source = self.orchestra.retrieve_service_list(
                PaymentSource.api_name)[0]
        except IndexError:
            pay_source = {}
        context.update({
            'payment': PaymentSource.new_from_json(pay_source)
        })

        return context


def profile_set_language(request, code):
    # set user language as active language

    if any(x[0] == code for x in settings.LANGUAGES):
        # http://127.0.0.1:8080/profile/setLang/es
        user_language = code
        translation.activate(user_language)

        response = HttpResponseRedirect('/dashboard')
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
        content_type = request.META.get('HTTP_ACCEPT')
        if content_type == 'application/pdf':
            pdf = html_to_pdf(bill.html or bill.render())
            return HttpResponse(pdf, content_type='application/pdf')
        else:
            return HttpResponse(bill.html or bill.render())


class MailView(ServiceListView):
    service_class = Address
    template_name = "musician/addresses.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mail addresses'),
    }

    def get_queryset(self):
        # retrieve mails applying filters (if any)
        queryfilter = self.get_queryfilter()
        addresses = self.orchestra.retrieve_mail_address_list(
            querystring=queryfilter
        )
        return addresses

    def get_queryfilter(self):
        """Retrieve query params (if any) to filter queryset"""
        domain_id = self.request.GET.get('domain')
        if domain_id:
            return "domain={}".format(domain_id)

        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain_id = self.request.GET.get('domain')
        if domain_id:
            context.update({
                'active_domain': self.orchestra.retrieve_domain(domain_id)
            })
        context['mailboxes'] = self.orchestra.retrieve_mailbox_list()
        return context


class MailCreateView(CustomContextMixin, UserTokenRequiredMixin, FormView):
    service_class = Address
    template_name = "musician/address_form.html"
    form_class = MailForm
    success_url = reverse_lazy("musician:address-list")
    extra_context = {'service': service_class}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['domains'] = self.orchestra.retrieve_domain_list()
        kwargs['mailboxes'] = self.orchestra.retrieve_mailbox_list()
        return kwargs

    def form_valid(self, form):
        # handle request errors e.g. 400 validation
        try:
            serialized_data = form.serialize()
            self.orchestra.create_mail_address(serialized_data)
        except HTTPError as e:
            form.add_error(field='__all__', error=e)
            return self.form_invalid(form)

        return super().form_valid(form)


class MailUpdateView(CustomContextMixin, UserTokenRequiredMixin, FormView):
    service_class = Address
    template_name = "musician/address_form.html"
    form_class = MailForm
    success_url = reverse_lazy("musician:address-list")
    extra_context = {'service': service_class}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = self.orchestra.retrieve_mail_address(self.kwargs['pk'])

        kwargs.update({
            'instance': instance,
            'domains': self.orchestra.retrieve_domain_list(),
            'mailboxes': self.orchestra.retrieve_mailbox_list(),
        })

        return kwargs

    def form_valid(self, form):
        # handle request errors e.g. 400 validation
        try:
            serialized_data = form.serialize()
            self.orchestra.update_mail_address(self.kwargs['pk'], serialized_data)
        except HTTPError as e:
            form.add_error(field='__all__', error=e)
            return self.form_invalid(form)

        return super().form_valid(form)


class AddressDeleteView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    template_name = "musician/address_check_delete.html"
    success_url = reverse_lazy("musician:address-list")

    def get_object(self, queryset=None):
        obj = self.orchestra.retrieve_mail_address(self.kwargs['pk'])
        return obj

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.orchestra.delete_mail_address(self.object.id)
            messages.success(self.request,  _('Address deleted!'))
        except HTTPError as e:
            messages.error(self.request, _('Cannot process your request, please try again later.'))
            logger.error(e)

        return HttpResponseRedirect(self.success_url)


class MailingListsView(ServiceListView):
    service_class = MailinglistService
    template_name = "musician/mailinglists.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mailing lists'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain_id = self.request.GET.get('domain')
        if domain_id:
            context.update({
                'active_domain': self.orchestra.retrieve_domain(domain_id)
            })
        return context

    def get_queryfilter(self):
        """Retrieve query params (if any) to filter queryset"""
        # TODO(@slamora): this is not working because backend API
        #   doesn't support filtering by domain
        domain_id = self.request.GET.get('domain')
        if domain_id:
            return "domain={}".format(domain_id)

        return ''


class MailboxesView(ServiceListView):
    service_class = Mailbox
    template_name = "musician/mailboxes.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mailboxes'),
    }


class MailboxCreateView(CustomContextMixin, UserTokenRequiredMixin, FormView):
    service_class = Mailbox
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
        return number_of_mailboxes >= profile.allowed_resources('mailbox')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'addresses': self.orchestra.retrieve_mail_address_list(),
        })

        return kwargs

    def form_valid(self, form):
        serialized_data = form.serialize()
        status, response = self.orchestra.create_mailbox(serialized_data)

        if status >= 400:
            if status == 400:
                # handle errors & add to form (they will be rendered)
                form.add_error(field=None, error=response)
            else:
                logger.error("{}: {}".format(status, response[:120]))
                msg = "Sorry, an error occurred while processing your request ({})".format(status)
                form.add_error(field='__all__', error=msg)
            return self.form_invalid(form)

        return super().form_valid(form)


class MailboxUpdateView(CustomContextMixin, UserTokenRequiredMixin, FormView):
    service_class = Mailbox
    template_name = "musician/mailbox_form.html"
    form_class = MailboxUpdateForm
    success_url = reverse_lazy("musician:mailbox-list")
    extra_context = {'service': service_class}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = self.orchestra.retrieve_mailbox(self.kwargs['pk'])

        kwargs.update({
            'instance': instance,
            'addresses': self.orchestra.retrieve_mail_address_list(),
        })

        return kwargs

    def form_valid(self, form):
        serialized_data = form.serialize()
        status, response = self.orchestra.update_mailbox(self.kwargs['pk'], serialized_data)

        if status >= 400:
            if status == 400:
                # handle errors & add to form (they will be rendered)
                form.add_error(field=None, error=response)
            else:
                logger.error("{}: {}".format(status, response[:120]))
                msg = "Sorry, an error occurred while processing your request ({})".format(status)
                form.add_error(field='__all__', error=msg)

            return self.form_invalid(form)

        return super().form_valid(form)


class MailboxDeleteView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    template_name = "musician/mailbox_check_delete.html"
    success_url = reverse_lazy("musician:mailbox-list")

    def get_object(self, queryset=None):
        obj = self.orchestra.retrieve_mailbox(self.kwargs['pk'])
        return obj

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.orchestra.delete_mailbox(self.object.id)
            messages.success(self.request,  _('Mailbox deleted!'))
        except HTTPError as e:
            messages.error(self.request, _('Cannot process your request, please try again later.'))
            logger.error(e)

        self.notify_managers(self.object)

        return HttpResponseRedirect(self.success_url)

    def notify_managers(self, mailbox):
        user = self.get_context_data()['profile']
        subject = 'Mailbox {} ({}) deleted | Musician'.format(mailbox.id, mailbox.name)
        content = (
            "User {} ({}) has deleted its mailbox {} ({}) via musician.\n"
            "The mailbox has been marked as inactive but has not been removed."
        ).format(user.username, user.full_name, mailbox.id, mailbox.name)

        try:
            mail_managers(subject, content, fail_silently=False)
        except (smtplib.SMTPException, ConnectionRefusedError):
            logger.error("Error sending email to managers", exc_info=True)


class MailboxChangePasswordView(CustomContextMixin, UserTokenRequiredMixin, FormView):
    template_name = "musician/mailbox_change_password.html"
    form_class = MailboxChangePasswordForm
    success_url = reverse_lazy("musician:mailbox-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = self.get_object()
        context.update({
            'object': self.object,
        })
        return context

    def get_object(self, queryset=None):
        obj = self.orchestra.retrieve_mailbox(self.kwargs['pk'])
        return obj

    def form_valid(self, form):
        data = {
            'password': form.cleaned_data['password2']
        }
        status, response = self.orchestra.set_password_mailbox(self.kwargs['pk'], data)

        if status < 400:
            messages.success(self.request,  _('Password updated!'))
        else:
            messages.error(self.request, _('Cannot process your request, please try again later.'))
            logger.error("{}: {}".format(status, str(response)[:100]))

        return super().form_valid(form)


class DatabasesView(ServiceListView):
    template_name = "musician/databases.html"
    service_class = DatabaseService
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Databases'),
    }


class SaasView(ServiceListView):
    service_class = SaasService
    model = SaaS
    template_name = "musician/saas.html"
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
