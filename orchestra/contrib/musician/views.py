import logging
import smtplib
from typing import Any

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import mail_managers
from django.db.models import Value
from django.db.models.functions import Concat
from django.http import (HttpResponse, HttpResponseNotFound,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import (CreateView, DeleteView, FormView,
                                       UpdateView)
from django.views.generic.list import ListView
from requests.exceptions import HTTPError

from django.urls import reverse
from django.db.models import Q

from orchestra import get_version
from orchestra.contrib.bills.models import Bill
from orchestra.contrib.databases.models import Database
from orchestra.contrib.domains.models import Domain, Record
from orchestra.contrib.lists.models import List
from orchestra.contrib.mailboxes.models import Address, Mailbox
from orchestra.contrib.resources.models import Resource, ResourceData
from orchestra.contrib.systemusers.models import WebappUsers, SystemUser
from orchestra.utils.html import html_to_pdf

from .auth import logout as auth_logout
from .forms import (LoginForm, MailboxChangePasswordForm, MailboxCreateForm,
                    MailboxSearchForm, MailboxUpdateForm, MailForm,
                    RecordCreateForm, RecordUpdateForm, WebappUsersChangePasswordForm,
                    SystemUsersChangePasswordForm, BannedForm)
from .mixins import (CustomContextMixin, ExtendedPaginationMixin,
                     UserTokenRequiredMixin)
from .models import Address as AddressService
from .models import Bill as BillService
from .models import DatabaseService
from .models import Mailbox as MailboxService
from .models import MailinglistService, SaasService
from .settings import ALLOWED_RESOURCES, MUSICIAN_EDIT_ENABLE_PHP_OPTIONS
from .utils import get_bootstraped_percent, get_bootstraped_percent_exact

from .webapps.views import *
from .websites.views import *
from .lists.views import *
from .saas.views import *

logger = logging.getLogger(__name__)

import json
from urllib.parse import parse_qs
from orchestra.contrib.resources.helpers import get_history_data
from django.http import HttpResponseNotFound, Http404

class HistoryView(CustomContextMixin, UserTokenRequiredMixin, View):

    def check_resource(self, pk):
        related_resources = self.get_all_resources()
        
        account = related_resources.filter(resource_id__verbose_name='account-disk').first()
        account_trafic = related_resources.filter(resource_id__verbose_name='account-traffic').first()
        account = getattr(account, "id", False) == pk
        account_trafic = getattr(account_trafic, "id", False) == pk
        if account == False and account_trafic == False:
            raise Http404(f"Resource with id {pk} does not exist")


    def get(self, request, pk, *args, **kwargs):
        context = {
            'ids': pk
        }
        self.check_resource(pk)
        return render(request, "musician/history.html", context)

    # TODO: funcion de dashborad, mirar como no repetir esta funcion 
    def get_all_resources(self):
        user = self.request.user
        resources = Resource.objects.select_related('content_type')
        resource_models = {r.content_type.model_class(): r.content_type_id for r in resources}
        ct_id = resource_models[user._meta.model]
        qset = Q(content_type_id=ct_id, object_id=user.id, resource__is_active=True)
        for field, rel in user._meta.fields_map.items():
            try:
                ct_id = resource_models[rel.related_model]
            except KeyError:
                pass
            else:           
                manager = getattr(user, field)
                ids = manager.values_list('id', flat=True)
                qset = Q(qset) | Q(content_type_id=ct_id, object_id__in=ids, resource__is_active=True)
        return ResourceData.objects.filter(qset)


class HistoryDataView(CustomContextMixin, UserTokenRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        ids = [pk]
        queryset = ResourceData.objects.filter(id__in=ids)
        history = get_history_data(queryset)
        response = json.dumps(history, indent=4)
        return HttpResponse(response, content_type="application/json")


class DashboardView(CustomContextMixin, UserTokenRequiredMixin, TemplateView):
    template_name = "musician/dashboard.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Dashboard'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        related_resources = self.get_all_resources()
        
        account = related_resources.filter(resource_id__verbose_name='account-disk').first()
        account_trafic = related_resources.filter(resource_id__verbose_name='account-traffic').first()

        mailboxes = related_resources.filter(resource_id__verbose_name='mailbox-disk')
        lists = related_resources.filter(resource_id__verbose_name='list-traffic')
        databases = related_resources.filter(resource_id__verbose_name='database-disk')
        nextcloud = related_resources.filter(resource_id__verbose_name='nextcloud-disk', content_object_repr__iregex=r'^.*@nextcloud$')
        domains = Domain.objects.filter(account_id=self.request.user)

        # TODO(@slamora) update when backend supports notifications
        notifications = []

        # show resource usage based on plan definition
        profile_type = context['profile'].type

        # TODO(@slamora) update when backend provides resource usage data
        resource_usage = {
            'mailbox': self.get_resource_usage(profile_type, mailboxes, 'mailbox'),
            'database': self.get_resource_usage(profile_type, databases, 'database'),
            'nextcloud': self.get_resource_usage(profile_type, nextcloud, 'nextcloud'),
            'list': self.get_resource_usage(profile_type, lists, 'Mailman list Traffic'),
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
            'account': self.get_account_usage(profile_type, account, account_trafic),
        })

        return context

    def get_all_resources(self):
        user = self.request.user
        resources = Resource.objects.select_related('content_type')
        resource_models = {r.content_type.model_class(): r.content_type_id for r in resources}
        ct_id = resource_models[user._meta.model]
        qset = Q(content_type_id=ct_id, object_id=user.id, resource__is_active=True)
        for field, rel in user._meta.fields_map.items():
            try:
                ct_id = resource_models[rel.related_model]
            except KeyError:
                pass
            else:           
                manager = getattr(user, field)
                ids = manager.values_list('id', flat=True)
                qset = Q(qset) | Q(content_type_id=ct_id, object_id__in=ids, resource__is_active=True)
        return ResourceData.objects.filter(qset)

    def get_resource_usage(self, profile_type, resource_data, name_resource):
        limit_rs = 0
        total_rs = len(resource_data)
        rs_left = 0
        alert = ''
        progres_bar = False

        if ALLOWED_RESOURCES[profile_type].get(name_resource):
            progres_bar = True
            limit_rs = ALLOWED_RESOURCES[profile_type][name_resource]
            rs_left = limit_rs - total_rs

            alert = ''
            if rs_left < 0:
                alert = format_html(f"<span class='text-danger'>{rs_left * -1} extra {name_resource}</span>")
            elif rs_left <= 1:
                alert = format_html("<span class='text-warning'>{} {} {}</span>".format(rs_left, name_resource, _('available')))
            elif rs_left > 1:
                alert = format_html("<span class='text-secondary'>{} {} {}</span>".format(rs_left, name_resource, _('available')))

        # porcentage de uso en los recursos
        for x in resource_data:
            if getattr(x, 'used', False) and getattr(x, 'allocated', False):
                rs_percent = getattr(x, 'used') / getattr(x, 'allocated') * 100
                x.rs_percent = int(rs_percent)
                

        return {
            'verbose_name': _(name_resource.capitalize()),
            'data': {
                'progres_bar': progres_bar,
                'used': total_rs,
                'total': limit_rs,
                'alert': alert,
                'unit': name_resource.capitalize(),
                'percent': get_bootstraped_percent_exact(total_rs, limit_rs),
            },
            'objects': resource_data,
        }
    
    def get_account_usage(self, profile_type, account, account_trafic):
        total_size = 0
        if account != None and getattr(account, "used") != None:
            total_size = account.used

        allowed_size = ALLOWED_RESOURCES[profile_type]['account']
        size_left = allowed_size - total_size
        unit = account.unit if account != None else "GiB"

        alert = ''
        if size_left < 0:
            alert = format_html(f"<span class='text-danger'>{size_left * -1} {unit} extra</span>")
        elif size_left <= 1:
            alert = format_html("<span class='text-warning'>{} {} {}</span>".format(size_left, unit, _('available')))

        return {
            'verbose_name': _('Account'),
            'data': {
                'progres_bar': True,
                'used': total_size,
                'total': allowed_size,
                'alert': alert,
                'unit': 'GiB Size',
                'percent': get_bootstraped_percent_exact(total_size, allowed_size),
            },
            'objects': {
                'size': {'ac': account},
                'traffic': {'ac': account_trafic}
            },
        }


class DomainListView(CustomContextMixin, UserTokenRequiredMixin, TemplateView):
    template_name = "musician/domain_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Domains'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domains = self.orchestra.retrieve_domain_list()

        name = self.request.GET.get('name')
        if name:
            domains = domains.filter(name__icontains=name)

        support_email = getattr(settings, "USER_SUPPORT_EMAIL", "suport@pangea.org")
        support_email_anchor = format_html(
            "<a href='mailto:{}'>{}</a>",
            support_email,
            support_email,
        )
        context.update({
            'domains': domains,
            "support_email_anchor": support_email_anchor,
        })
        return context


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
        url_is_safe = url_has_allowed_host_and_scheme(
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
        queryfilter = {}

        domain_id = self.clean_domain_id()
        if domain_id:
            queryfilter.update({"domain": domain_id})

        else:
            domain_name = self.request.GET.get('domain__name')
            if domain_name:
                queryfilter.update({"domain__name__icontains": domain_name})

        return queryfilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain_id = self.clean_domain_id()
        if domain_id:
            qs = Domain.objects.filter(account=self.request.user)
            context.update({
                'active_domain': get_object_or_404(qs, pk=domain_id)
            })
        context['mailboxes'] = Mailbox.objects.filter(account=self.request.user)
        return context

    def clean_domain_id(self):
        try:
            return int(self.request.GET.get('domain', ''))
        except ValueError:
            return None

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


class MailboxListView(ServiceListView):
    service_class = MailboxService
    model = Mailbox
    template_name = "musician/mailbox_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mailboxes'),
    }
    search_form_class = MailboxSearchForm

    def get_queryset(self):
        qs = super().get_queryset()

        search_form = self.search_form_class(self.request.GET)
        cleaned_data = search_form.cleaned_data if search_form.is_valid() else {}

        if "address" in cleaned_data:
            qs = qs.annotate(
                    full_address=Concat("addresses__name", Value("@"), "addresses__domain__name")
                ).filter(
                    full_address__icontains=cleaned_data["address"]
                )
        
        if "name" in cleaned_data:
            qs = qs.filter(name__icontains=cleaned_data["name"])
        
        return qs


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.search_form_class()#self.request.GET)
        return context


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


class DatabaseListView(ServiceListView):
    template_name = "musician/database_list.html"
    model = Database
    service_class = DatabaseService
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Databases'),
    }

    def get_queryset(self):
        qs = super().get_queryset().order_by("name")

        name = self.request.GET.get('name')
        if name:
            qs = qs.filter(name__icontains=name)

        # TODO(@slamora): optimize query
        ctype = ContentType.objects.get_for_model(self.model)
        disk_resource = Resource.objects.get(name='disk', content_type=ctype)
        for db in qs:
            try:
                db.usage = db.resource_set.get(resource=disk_resource)
            except ResourceData.DoesNotExist:
                db.usage = ResourceData(resource=disk_resource)
        return qs


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
        url_is_safe = url_has_allowed_host_and_scheme(
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


class WebappUserListView(ServiceListView):
    model = WebappUsers
    template_name = "musician/webapps/webappuser_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Webapp users'),
    }

    def get_queryset(self):
        qs = self.model.objects.filter(account=self.request.user)
        name = self.request.GET.get('name')
        if name:
            qs = qs.filter(username__icontains=name)
        return qs

class WebappUserChangePasswordView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    template_name = "musician/webapps/webappuser_change_password.html"
    model = WebappUsers
    form_class = WebappUsersChangePasswordForm
    success_url = reverse_lazy("musician:webappuser-list")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)


class SystemUserListView(ServiceListView):
    model = SystemUser
    template_name = "musician/systemuser_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Main users'),
    }

class SystemUserChangePasswordView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    template_name = "musician/systemuser_change_password.html"
    model = SystemUser
    form_class = SystemUsersChangePasswordForm
    success_url = reverse_lazy("musician:systemuser-list")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)




class BannedView(CustomContextMixin, UserTokenRequiredMixin, TemplateView):
    template_name = "musician/banned.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Im banned'),
    }

    def get(self, request):
        form = BannedForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = BannedForm(request.POST)
        mensaje = ''
        if form.is_valid():
            ip = form.cleaned_data['ip']
            # try:
            #     # Ejecuta el script personalizado (ejemplo: bloquear IP con iptables)
            #     subprocess.run(['sudo', 'iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'], check=True)
            #     mensaje = f"IP {ip} bloqueada con éxito."
            # except subprocess.CalledProcessError as e:
            #     mensaje = f"Error al bloquear IP: {e}"
        return render(request, self.template_name, {'form': form, 'mensaje': mensaje})
