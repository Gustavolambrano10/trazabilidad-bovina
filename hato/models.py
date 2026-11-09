from django.conf import settings
from django.db import models
from django.utils import timezone


class Propietario(models.Model):
    """Dueño de una o varias fincas. Se guarda la autorización de datos (Ley 1581 de 2012)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="propietarios")
    nombre = models.CharField("nombre", max_length=120)
    contacto = models.CharField("contacto (teléfono)", max_length=60, blank=True)
    autoriza_datos = models.BooleanField("autoriza el tratamiento de sus datos", default=False)
    fecha_autorizacion = models.DateField("fecha de autorización", null=True, blank=True)

    class Meta:
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        # Si autoriza y no hay fecha, se registra la de hoy.
        if self.autoriza_datos and not self.fecha_autorizacion:
            self.fecha_autorizacion = timezone.localdate()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Finca(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fincas")
    propietario = models.ForeignKey(Propietario, on_delete=models.PROTECT, related_name="fincas")
    nombre = models.CharField("nombre de la finca", max_length=120)
    vereda = models.CharField("vereda o corregimiento", max_length=120)
    area_hectareas = models.DecimalField("área aproximada (ha)", max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.vereda})"


class Animal(models.Model):
    SEXOS = [("H", "Hembra"), ("M", "Macho")]
    ESTADOS = [
        ("activo", "Activo"),
        ("vendido", "Vendido"),
        ("muerto", "Muerto"),
        ("extraviado", "Extraviado"),
        ("robado", "Robado"),
    ]

    finca = models.ForeignKey(Finca, on_delete=models.PROTECT, related_name="animales")
    codigo = models.CharField("código interno", max_length=30, unique=True)
    chapeta_oficial = models.CharField("chapeta oficial (opcional)", max_length=40, blank=True)
    alias = models.CharField("alias o nombre", max_length=60, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXOS)
    raza = models.CharField(max_length=60, blank=True)
    fecha_nacimiento = models.DateField("fecha aproximada de nacimiento", null=True, blank=True)
    senales_particulares = models.TextField("señales particulares", blank=True)
    hierro = models.CharField("hierro o marca", max_length=80, blank=True)
    foto = models.ImageField(upload_to="animales/%Y/%m/", blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="activo")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]
        indexes = [models.Index(fields=["estado"]), models.Index(fields=["sexo"])]

    def __str__(self):
        return f"{self.codigo} {self.alias}".strip()


class EventoAnimal(models.Model):
    TIPOS = [
        ("nacimiento", "Nacimiento"),
        ("vacunacion", "Vacunación"),
        ("traslado", "Traslado"),
        ("venta", "Venta"),
        ("muerte", "Muerte"),
        ("estado", "Cambio de estado"),
        ("otro", "Otro"),
    ]

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=12, choices=TIPOS)
    fecha = models.DateField(default=timezone.localdate)
    observacion = models.CharField("observación", max_length=255, blank=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.animal.codigo}"


class ReporteNovedad(models.Model):
    TIPOS = [("perdida", "Pérdida"), ("hurto", "Hurto")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reportes")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha = models.DateField(default=timezone.localdate)
    lugar = models.CharField(max_length=160)
    descripcion = models.TextField("descripción", blank=True)
    animales = models.ManyToManyField(Animal, related_name="reportes")
    pdf = models.FileField("PDF generado", upload_to="reportes/%Y/%m/", blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Reporte {self.id} - {self.get_tipo_display()} ({self.fecha})"


class Auditoria(models.Model):
    """Registro de quién hizo qué (RF11)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="auditorias")
    accion = models.CharField(max_length=20)
    entidad = models.CharField(max_length=40)
    detalle = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name_plural = "auditorías"

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M} {self.usuario} {self.accion} {self.entidad}"
