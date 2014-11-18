import decimal

from django.core.validators import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from orchestra.core import services, accounts
from orchestra.core.validators import validate_name
from orchestra.models import queryset

from . import rating


class Plan(models.Model):
    name = models.CharField(_("name"), max_length=32, unique=True, validators=[validate_name])
    verbose_name = models.CharField(_("verbose_name"), max_length=128, blank=True)
    is_default = models.BooleanField(_("default"), default=False,
        help_text=_("Designates whether this plan is used by default or not."))
    is_combinable = models.BooleanField(_("combinable"), default=True,
        help_text=_("Designates whether this plan can be combined with other plans or not."))
    allow_multiple = models.BooleanField(_("allow multiple"), default=False,
        help_text=_("Designates whether this plan allow for multiple contractions."))
    
    def __unicode__(self):
        return self.name
    
    def clean(self):
        self.verbose_name = self.verbose_name.strip()
    
    def get_verbose_name(self):
        return self.verbose_name or self.name


class ContractedPlan(models.Model):
    plan = models.ForeignKey(Plan, verbose_name=_("plan"), related_name='contracts')
    account = models.ForeignKey('accounts.Account', verbose_name=_("account"),
            related_name='plans')
    
    class Meta:
        verbose_name_plural = _("plans")
    
    def __unicode__(self):
        return str(self.plan)
    
    def clean(self):
        if not self.pk and not self.plan.allow_multiples:
            if ContractedPlan.objects.filter(plan=self.plan, account=self.account).exists():
                raise ValidationError("A contracted plan for this account already exists.")


class RateQuerySet(models.QuerySet):
    group_by = queryset.group_by
    
    def by_account(self, account):
        # Default allways selected
        return self.filter(
            Q(plan__is_default=True) |
            Q(plan__contracts__account=account)
        ).order_by('plan', 'quantity').select_related('plan')


class Rate(models.Model):
    STEP_PRICE = 'STEP_PRICE'
    MATCH_PRICE = 'MATCH_PRICE'
    RATE_METHODS = {
        STEP_PRICE: rating.step_price,
        MATCH_PRICE: rating.match_price,
    }
    
    service = models.ForeignKey('services.Service', verbose_name=_("service"),
            related_name='rates')
    plan = models.ForeignKey(Plan, verbose_name=_("plan"), related_name='rates')
    quantity = models.PositiveIntegerField(_("quantity"), null=True, blank=True)
    price = models.DecimalField(_("price"), max_digits=12, decimal_places=2)
    
    objects = RateQuerySet.as_manager()
    
    class Meta:
        unique_together = ('service', 'plan', 'quantity')
    
    def __unicode__(self):
        return "{}-{}".format(str(self.price), self.quantity)
    
    @classmethod
    def get_methods(self):
        return self.RATE_METHODS


accounts.register(ContractedPlan)
services.register(ContractedPlan, menu=False)
