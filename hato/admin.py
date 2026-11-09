from django.contrib import admin

from .models import Animal, Auditoria, EventoAnimal, Finca, Propietario, ReporteNovedad


@admin.register(Propietario)
class PropietarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "contacto", "autoriza_datos", "usuario")
    search_fields = ("nombre",)


@admin.register(Finca)
class FincaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "vereda", "propietario", "usuario")
    search_fields = ("nombre", "vereda")


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ("codigo", "alias", "sexo", "estado", "finca")
    list_filter = ("estado", "sexo")
    search_fields = ("codigo", "alias", "chapeta_oficial")

    # RF05: baja lógica, sin borrado definitivo.
    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(EventoAnimal)
admin.site.register(ReporteNovedad)


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "accion", "entidad", "detalle")
    list_filter = ("accion", "entidad")
    # La auditoría es solo de lectura.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
