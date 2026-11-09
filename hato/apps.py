from django.apps import AppConfig


class HatoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hato"
    verbose_name = "Trazabilidad bovina"

    def ready(self):
        from . import signals  # noqa: F401  (registra la auditoría de ingreso y salida)
