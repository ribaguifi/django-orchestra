from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import (CreateView, DeleteView, FormView,
                                       UpdateView)
from django.views.generic.list import ListView

from orchestra.contrib.musician.mixins import (CustomContextMixin, ExtendedPaginationMixin,
                     UserTokenRequiredMixin)

from .forms import ( NextcloudChangePasswordForm, SaasNextcloudUpdateForm,
                    SaasWordpressUpdateForm, NextcloudCreateForm )
from orchestra.contrib.saas.models import SaaS


class SaasNextcloudListView(CustomContextMixin, UserTokenRequiredMixin, ListView):
    model = SaaS
    template_name = "musician/saas_nextcloud_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Software as a Service'),
        'verbose_name': _('Nextcloud Service'),
        'description': _("Members can manage their Nextcloud users in this section."),
    }

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user, service='nextcloud')


class SaasWordpressListView(CustomContextMixin, UserTokenRequiredMixin, ListView):
    model = SaaS
    template_name = "musician/saas_wordpress_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Software as a Service'),
        'verbose_name': _('Community WordPress'),
        'description': _("Pangea's multisite WordPress service. Members can have their WordPress on this community WordPress hosted and maintained by Pangea."),
    }

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user, service='wordpress')


class SaasWordpressUpdateView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    model = SaaS
    form_class = SaasWordpressUpdateForm
    template_name = "musician/saas_wordpress_form.html"

    def get_queryset(self):
        qs = SaaS.objects.filter(account=self.request.user)
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:saas-wordpress-list")
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SaasNextcloudUpdateView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    model = SaaS
    form_class = SaasNextcloudUpdateForm
    template_name = "musician/saas_nextcloud_form.html"

    def get_queryset(self):
        qs = SaaS.objects.filter(account=self.request.user)
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:saas-nextcloud-list")
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

class NextcloudChangePasswordView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    template_name = "musician/nextcloud_change_password.html"
    model = SaaS
    form_class = NextcloudChangePasswordForm
    success_url = reverse_lazy("musician:saas-nextcloud-list")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)


class SaasDeleteView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    template_name = "musician/saas_check_delete.html"
    model = SaaS
    success_url = reverse_lazy("musician:saas-nextcloud-list")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)


class NextcloudCreateView(CustomContextMixin, UserTokenRequiredMixin, CreateView):
    model = SaaS
    template_name = "musician/saas_nextcloud_form.html"
    form_class = NextcloudCreateForm
    success_url = reverse_lazy("musician:saas-nextcloud-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
