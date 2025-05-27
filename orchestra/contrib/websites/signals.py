from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BannedIP

@receiver(post_save, sender=BannedIP)
def delete_data_after_save(sender, instance, created, **kwargs):
    if created:
        BannedIP.objects.all().delete()
        