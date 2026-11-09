from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    # Cuenta
    path("ingresar/", auth_views.LoginView.as_view(), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("registro/", views.registro, name="registro"),
    # Propietarios
    path("propietarios/", views.propietarios, name="propietarios"),
    path("propietarios/nuevo/", views.propietario_nuevo, name="propietario_nuevo"),
    # Fincas
    path("fincas/", views.fincas, name="fincas"),
    path("fincas/nueva/", views.finca_nueva, name="finca_nueva"),
    path("fincas/<int:pk>/editar/", views.finca_editar, name="finca_editar"),
    path("fincas/<int:pk>/resumen/", views.finca_resumen, name="finca_resumen"),
    # Animales
    path("animales/", views.animales, name="animales"),
    path("animales/nuevo/", views.animal_nuevo, name="animal_nuevo"),
    path("animales/exportar/", views.animales_csv, name="animales_csv"),
    path("animales/<int:pk>/", views.animal_detalle, name="animal_detalle"),
    path("animales/<int:pk>/editar/", views.animal_editar, name="animal_editar"),
    path("animales/<int:pk>/evento/", views.animal_evento, name="animal_evento"),
    path("animales/<int:pk>/estado/", views.animal_estado, name="animal_estado"),
    # Reportes
    path("reportes/", views.reportes, name="reportes"),
    path("reportes/nuevo/", views.reporte_nuevo, name="reporte_nuevo"),
    path("reportes/<int:pk>/", views.reporte_detalle, name="reporte_detalle"),
    path("reportes/<int:pk>/pdf/", views.reporte_pdf, name="reporte_pdf"),
    # Auditoría
    path("auditoria/", views.auditoria, name="auditoria"),
]
