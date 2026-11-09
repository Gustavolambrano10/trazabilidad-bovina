"""RNF04: registro de acciones. Se guarda cada ingreso y salida del sistema."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import Auditoria


@receiver(user_logged_in)
def registrar_ingreso(sender, request, user, **kwargs):
    Auditoria.objects.create(usuario=user, accion="ingreso", entidad="sesión", detalle="Inicio de sesión")


@receiver(user_logged_out)
def registrar_salida(sender, request, user, **kwargs):
    if user is not None:
        Auditoria.objects.create(usuario=user, accion="salida", entidad="sesión", detalle="Cierre de sesión")
