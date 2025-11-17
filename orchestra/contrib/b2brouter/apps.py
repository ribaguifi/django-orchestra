from django.apps import AppConfig


class B2BrouterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orchestra.contrib.b2brouter'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        from . import signals
        return super().ready()
