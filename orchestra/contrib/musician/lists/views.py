from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from django.views.generic.list import ListView
from orchestra.contrib.musician.mixins import (CustomContextMixin, ExtendedPaginationMixin,
                     UserTokenRequiredMixin)
from django.views.generic.edit import (CreateView, DeleteView, FormView,
                                       UpdateView)

from orchestra.contrib.lists.models import List
from orchestra.contrib.domains.models import Domain, Record
from orchestra.contrib.lists.settings import LISTS_DEFAULT_DOMAIN

from .forms import MailingUpdateForm, MailingCreateForm

class MailingListsView(CustomContextMixin, UserTokenRequiredMixin, ListView):
    model = List
    template_name = "musician/mailinglist_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Mailing lists'),
    }

    def get_queryset(self):
        qs = self.model.objects.filter(account=self.request.user)
        name = self.request.GET.get('name')
        if name:
            qs = qs.filter(name__icontains=name)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain_id = self.request.GET.get('domain')
        if domain_id:
            qs = Domain.objects.filter(account=self.request.user)
            context.update({
                'active_domain': get_object_or_404(qs, pk=domain_id),
            })
        context.update({'default_domain': LISTS_DEFAULT_DOMAIN})
        return context

    def get_queryfilter(self):
        """Retrieve query params (if any) to filter queryset"""
        domain_id = self.request.GET.get('domain')
        if domain_id:
            return {"address_domain_id": domain_id}
        return {}

class MailingUpdateView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    model = List
    form_class = MailingUpdateForm
    template_name = "musician/mailinglist_form.html"

    def get_queryset(self):
        qs = List.objects.filter(account=self.request.user)
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:mailing-lists")
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

class MailingCreateView(CustomContextMixin, UserTokenRequiredMixin, CreateView):
    model = List
    form_class = MailingCreateForm
    template_name = "musician/mailinglist_form.html"
    success_url = reverse_lazy("musician:mailing-lists")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class MailingDeleteView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    template_name = "musician/mailing_check_delete.html"
    model = List
    success_url = reverse_lazy("musician:mailing-lists")

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)