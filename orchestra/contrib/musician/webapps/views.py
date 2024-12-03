from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from orchestra.contrib.musician.mixins import (CustomContextMixin, ExtendedPaginationMixin,
                     UserTokenRequiredMixin)

from orchestra.contrib.webapps.models import WebApp, WebAppOption
from .forms import WebappOptionCreateForm, WebappOptionUpdateForm

from orchestra.contrib.musician.settings import MUSICIAN_EDIT_ENABLE_PHP_OPTIONS




class WebappListView(CustomContextMixin, UserTokenRequiredMixin, ListView):
    model = WebApp
    template_name = "musician/webapps/webapp_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Webapps'),
    }

    def get_queryset(self):
        qs = self.model.objects.filter(account=self.request.user)
        name = self.request.GET.get('name')
        if name:
            qs = qs.filter(name__icontains=name)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'description': _("A web app is the directory where your website is stored. Through SFTP, you can access this directory and upload/edit/delete files."),
            'description2': _("Each Webapp has its own SFTP user, which is created automatically when the Webapp is created.")
        })
        return context


class WebappDetailView(CustomContextMixin, UserTokenRequiredMixin, DetailView):
    template_name = "musician/webapps/webapp_detail.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('webapp details'),
    }

    def get_queryset(self):
        return WebApp.objects.filter(account=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'edit_allowed_PHP_options': MUSICIAN_EDIT_ENABLE_PHP_OPTIONS
        })
        return context


class WebappAddOptionView(CustomContextMixin, UserTokenRequiredMixin, CreateView):
    model = WebAppOption
    form_class = WebappOptionCreateForm
    template_name = "musician/webapps/webapp_option_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        webapp = get_object_or_404(WebApp, account=self.request.user, pk=self.kwargs["pk"])
        kwargs['webapp'] = webapp
        return kwargs

    def get_success_url(self):
        return reverse_lazy("musician:webapp-detail", kwargs={"pk": self.kwargs["pk"]})

class WebappDeleteOptionView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    model = WebAppOption
    template_name = "musician/webapps/webappoption_check_delete.html"
    pk_url_kwarg = "option_pk"

    def get_queryset(self):
        qs = WebAppOption.objects.filter(webapp__account=self.request.user, webapp=self.kwargs["pk"])
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:webapp-detail", kwargs={"pk": self.kwargs["pk"]})
    
    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        response = super().delete(request, *args, **kwargs)
        object.webapp.save()
        return response


class WebappUpdateOptionView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    model = WebAppOption
    form_class = WebappOptionUpdateForm
    template_name = "musician/webapps/webapp_option_form.html"
    pk_url_kwarg = "option_pk"

    def get_queryset(self):
        qs = WebAppOption.objects.filter(webapp__account=self.request.user, webapp=self.kwargs["pk"])
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:webapp-detail", kwargs={"pk": self.kwargs["pk"]})
