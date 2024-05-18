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

from orchestra.contrib.websites.models import Website, Content, WebsiteDirective
from orchestra.contrib.musician.tidy_forms.websites import WebsiteUpdateForm, WesiteContentCreateForm


class WebsiteListView(CustomContextMixin, UserTokenRequiredMixin, ListView):
    model = Website
    template_name = "musician/websites/website_list.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('Websites'),
    }

    def get_queryset(self):
        return self.model.objects.filter(account=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'description': _("A website is the place where a domain is associated with the directory where the web files are located. (WebApp)"),
        })
        return context
    

class WebsiteDetailView(CustomContextMixin, UserTokenRequiredMixin, DetailView):
    template_name = "musician/websites/website_detail.html"
    extra_context = {
        # Translators: This message appears on the page title
        'title': _('website details'),
    }

    def get_queryset(self):
        return Website.objects.filter(account=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content'] = Content.objects.filter(website=self.object)
        context['directives'] = WebsiteDirective.objects.filter(website=self.object)
        return context
    

class WebsiteUpdateView(CustomContextMixin, UserTokenRequiredMixin, UpdateView):
    model = Website
    form_class = WebsiteUpdateForm
    template_name = "musician/websites/website_form.html"

    def get_queryset(self):
        qs = Website.objects.filter(account=self.request.user)
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:website-detail", kwargs={"pk": self.kwargs["pk"]})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class WebsiteDeleteContentView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    model = Content
    template_name = "musician/websites/websiteoption_check_delete.html"
    pk_url_kwarg = "content_pk"

    def get_queryset(self):
        qs = Content.objects.filter(website__account=self.request.user, website=self.kwargs["pk"])
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:website-detail", kwargs={"pk": self.kwargs["pk"]})
    
    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        response = super().delete(request, *args, **kwargs)
        object.website.save()
        return response


class WebsiteDeleteDirectiveView(CustomContextMixin, UserTokenRequiredMixin, DeleteView):
    model = WebsiteDirective
    template_name = "musician/websites/websiteoption_check_delete.html"
    pk_url_kwarg = "directive_pk"

    def get_queryset(self):
        qs = WebsiteDirective.objects.filter(website__account=self.request.user, website=self.kwargs["pk"])
        return qs

    def get_success_url(self):
        return reverse_lazy("musician:website-detail", kwargs={"pk": self.kwargs["pk"]})
    
    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        response = super().delete(request, *args, **kwargs)
        object.website.save()
        return response


class WebsiteAddContentView(CustomContextMixin, UserTokenRequiredMixin, CreateView):
    model = Content
    form_class = WesiteContentCreateForm
    template_name = "musician/websites/website_create_option_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        website = get_object_or_404(Website, account=self.request.user, pk=self.kwargs["pk"])
        kwargs['website'] = website
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("musician:website-detail", kwargs={"pk": self.kwargs["pk"]})
        