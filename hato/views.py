import csv

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    AnimalForm, EstadoForm, EventoForm, FincaForm, PropietarioForm,
    RegistroForm, ReporteForm,
)
from .models import Animal, Auditoria, EventoAnimal, Finca, Propietario, ReporteNovedad
from .pdf import generar_pdf_reporte


def registrar(request, accion, entidad, detalle=""):
    """Guarda en la auditoría quién hizo qué."""
    Auditoria.objects.create(usuario=request.user, accion=accion, entidad=entidad, detalle=detalle[:255])


def animales_del_usuario(user):
    return Animal.objects.filter(finca__usuario=user).select_related("finca", "finca__propietario")


# ------------------------------------------------------------------ Cuenta
def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        # RF01: todo usuario nuevo entra con el rol Productor.
        grupo, _ = Group.objects.get_or_create(name="Productor")
        user.groups.add(grupo)
        login(request, user)
        messages.success(request, "Cuenta creada. Bienvenido al sistema.")
        return redirect("inicio")
    return render(request, "registration/registro.html", {"form": form})


# ------------------------------------------------------------------ Inicio
@login_required
def inicio(request):
    animales = animales_del_usuario(request.user)
    por_estado = {e["estado"]: e["n"] for e in animales.values("estado").annotate(n=Count("id"))}
    contexto = {
        "total_animales": animales.count(),
        "total_fincas": Finca.objects.filter(usuario=request.user).count(),
        "activos": por_estado.get("activo", 0),
        "novedades": por_estado.get("robado", 0) + por_estado.get("extraviado", 0),
        "recientes": animales.order_by("-creado")[:5],
    }
    return render(request, "hato/inicio.html", contexto)


# ------------------------------------------------------------------ Propietarios
@login_required
def propietarios(request):
    lista = Propietario.objects.filter(usuario=request.user)
    return render(request, "hato/propietarios.html", {"propietarios": lista})


@login_required
def propietario_nuevo(request):
    form = PropietarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        p = form.save(commit=False)
        p.usuario = request.user
        p.save()
        registrar(request, "crear", "propietario", p.nombre)
        messages.success(request, "Propietario registrado.")
        return redirect("propietarios")
    return render(request, "hato/formulario.html", {"form": form, "titulo": "Nuevo propietario"})


# ------------------------------------------------------------------ Fincas
@login_required
def fincas(request):
    lista = Finca.objects.filter(usuario=request.user).select_related("propietario").annotate(total=Count("animales"))
    return render(request, "hato/fincas.html", {"fincas": lista})


@login_required
def finca_nueva(request):
    if not Propietario.objects.filter(usuario=request.user).exists():
        messages.info(request, "Primero registre un propietario para poder crear la finca.")
        return redirect("propietario_nuevo")
    form = FincaForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        f = form.save(commit=False)
        f.usuario = request.user
        f.save()
        registrar(request, "crear", "finca", f.nombre)
        messages.success(request, "Finca registrada.")
        return redirect("fincas")
    return render(request, "hato/formulario.html", {"form": form, "titulo": "Nueva finca"})


@login_required
def finca_editar(request, pk):
    finca = get_object_or_404(Finca, pk=pk, usuario=request.user)
    form = FincaForm(request.POST or None, instance=finca, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        registrar(request, "editar", "finca", finca.nombre)
        messages.success(request, "Finca actualizada.")
        return redirect("fincas")
    return render(request, "hato/formulario.html", {"form": form, "titulo": f"Editar {finca.nombre}"})


@login_required
def finca_resumen(request, pk):
    """RF09: resumen de inventario de una finca."""
    finca = get_object_or_404(Finca.objects.select_related("propietario"), pk=pk, usuario=request.user)
    animales_finca = finca.animales.all()
    conteo_estado = {e["estado"]: e["n"] for e in animales_finca.values("estado").annotate(n=Count("id"))}
    conteo_sexo = {s["sexo"]: s["n"] for s in animales_finca.values("sexo").annotate(n=Count("id"))}
    contexto = {
        "finca": finca,
        "total": animales_finca.count(),
        "por_estado": [(nombre, conteo_estado.get(valor, 0), valor) for valor, nombre in Animal.ESTADOS],
        "hembras": conteo_sexo.get("H", 0),
        "machos": conteo_sexo.get("M", 0),
    }
    return render(request, "hato/finca_resumen.html", contexto)


# ------------------------------------------------------------------ Animales
@login_required
def animales(request):
    """Listado con búsqueda y filtros (RF05)."""
    lista = animales_del_usuario(request.user)
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    finca_id = request.GET.get("finca", "")
    sexo = request.GET.get("sexo", "")
    if q:
        lista = lista.filter(
            Q(codigo__icontains=q) | Q(chapeta_oficial__icontains=q) | Q(alias__icontains=q)
            | Q(hierro__icontains=q) | Q(raza__icontains=q)
        )
    if estado:
        lista = lista.filter(estado=estado)
    if sexo:
        lista = lista.filter(sexo=sexo)
    if finca_id.isdigit():
        lista = lista.filter(finca_id=int(finca_id))

    pagina = Paginator(lista, 10).get_page(request.GET.get("page"))
    parametros = request.GET.copy()
    parametros.pop("page", None)
    contexto = {
        "pagina": pagina,
        "q": q, "estado": estado, "sexo": sexo, "finca_sel": finca_id,
        "estados": Animal.ESTADOS,
        "fincas": Finca.objects.filter(usuario=request.user),
        "parametros": parametros.urlencode(),
    }
    return render(request, "hato/animales.html", contexto)


@login_required
def animal_nuevo(request):
    if not Finca.objects.filter(usuario=request.user).exists():
        messages.info(request, "Primero registre una finca para poder agregar animales.")
        return redirect("finca_nueva")
    form = AnimalForm(request.POST or None, request.FILES or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        a = form.save()
        EventoAnimal.objects.create(animal=a, tipo="nacimiento" if a.fecha_nacimiento else "otro",
                                    fecha=a.fecha_nacimiento or a.creado.date(),
                                    observacion="Registro inicial en el sistema")
        registrar(request, "crear", "animal", a.codigo)
        messages.success(request, f"Animal {a.codigo} registrado.")
        return redirect("animal_detalle", pk=a.pk)
    return render(request, "hato/formulario.html", {"form": form, "titulo": "Registrar animal", "multipart": True})


@login_required
def animal_detalle(request, pk):
    animal = get_object_or_404(animales_del_usuario(request.user), pk=pk)
    contexto = {
        "animal": animal,
        "eventos": animal.eventos.all(),
        "evento_form": EventoForm(),
        "estado_form": EstadoForm(initial={"estado": animal.estado}),
    }
    return render(request, "hato/animal_detalle.html", contexto)


@login_required
def animal_editar(request, pk):
    animal = get_object_or_404(animales_del_usuario(request.user), pk=pk)
    form = AnimalForm(request.POST or None, request.FILES or None, instance=animal, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        registrar(request, "editar", "animal", animal.codigo)
        messages.success(request, "Datos del animal actualizados.")
        return redirect("animal_detalle", pk=animal.pk)
    return render(request, "hato/formulario.html",
                  {"form": form, "titulo": f"Editar {animal.codigo}", "multipart": True})


@login_required
@require_POST
def animal_evento(request, pk):
    animal = get_object_or_404(animales_del_usuario(request.user), pk=pk)
    form = EventoForm(request.POST)
    if form.is_valid():
        ev = form.save(commit=False)
        ev.animal = animal
        ev.save()
        registrar(request, "evento", "animal", f"{animal.codigo}: {ev.get_tipo_display()}")
        messages.success(request, "Evento agregado al historial.")
    else:
        messages.error(request, "No se pudo guardar el evento. Revise los datos.")
    return redirect("animal_detalle", pk=animal.pk)


@login_required
@require_POST
def animal_estado(request, pk):
    animal = get_object_or_404(animales_del_usuario(request.user), pk=pk)
    form = EstadoForm(request.POST)
    if form.is_valid():
        anterior = animal.get_estado_display()
        animal.estado = form.cleaned_data["estado"]
        animal.save(update_fields=["estado", "actualizado"])
        EventoAnimal.objects.create(
            animal=animal, tipo="estado",
            observacion=f"{anterior} → {animal.get_estado_display()}. {form.cleaned_data['observacion']}".strip(),
        )
        registrar(request, "estado", "animal", f"{animal.codigo}: {animal.get_estado_display()}")
        messages.success(request, "Estado actualizado.")
    return redirect("animal_detalle", pk=animal.pk)


@login_required
def animales_csv(request):
    """Exporta el inventario a CSV, útil para abrir en Excel."""
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="inventario_bovino.csv"'
    respuesta.write("﻿")  # para que Excel respete las tildes
    w = csv.writer(respuesta)
    w.writerow(["Código", "Chapeta", "Alias", "Sexo", "Raza", "Nacimiento", "Hierro", "Estado", "Finca", "Vereda", "Propietario"])
    for a in animales_del_usuario(request.user):
        w.writerow([a.codigo, a.chapeta_oficial, a.alias, a.get_sexo_display(), a.raza,
                    a.fecha_nacimiento or "", a.hierro, a.get_estado_display(),
                    a.finca.nombre, a.finca.vereda, a.finca.propietario.nombre])
    registrar(request, "exportar", "inventario", "CSV")
    return respuesta


# ------------------------------------------------------------------ Reportes
@login_required
def reportes(request):
    lista = ReporteNovedad.objects.filter(usuario=request.user).prefetch_related("animales")
    return render(request, "hato/reportes.html", {"reportes": lista})


@login_required
def reporte_nuevo(request):
    form = ReporteForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        rep = form.save(commit=False)
        rep.usuario = request.user
        rep.save()
        form.save_m2m()
        # Cada animal reportado cambia de estado y queda en su historial.
        nuevo_estado = "robado" if rep.tipo == "hurto" else "extraviado"
        for a in rep.animales.all():
            a.estado = nuevo_estado
            a.save(update_fields=["estado", "actualizado"])
            EventoAnimal.objects.create(animal=a, tipo="estado", fecha=rep.fecha,
                                        observacion=f"Reporte N.º {rep.id}: {rep.get_tipo_display()} en {rep.lugar}")
        contenido = generar_pdf_reporte(rep)
        rep.pdf.save(f"reporte_{rep.id}.pdf", ContentFile(contenido), save=True)
        registrar(request, "crear", "reporte", f"N.º {rep.id} ({rep.get_tipo_display()})")
        messages.success(request, "Reporte creado y PDF generado.")
        return redirect("reporte_detalle", pk=rep.pk)
    return render(request, "hato/formulario.html", {"form": form, "titulo": "Reportar pérdida o hurto"})


@login_required
def reporte_detalle(request, pk):
    rep = get_object_or_404(ReporteNovedad, pk=pk, usuario=request.user)
    return render(request, "hato/reporte_detalle.html", {"reporte": rep, "animales": rep.animales.all()})


@login_required
def reporte_pdf(request, pk):
    """Descarga el PDF; si no existe en disco se vuelve a generar."""
    rep = get_object_or_404(ReporteNovedad, pk=pk, usuario=request.user)
    contenido = generar_pdf_reporte(rep)
    respuesta = HttpResponse(contenido, content_type="application/pdf")
    respuesta["Content-Disposition"] = f'inline; filename="reporte_{rep.id}.pdf"'
    registrar(request, "descargar", "reporte", f"N.º {rep.id}")
    return respuesta


# ------------------------------------------------------------------ Auditoría
@login_required
def auditoria(request):
    registros = Auditoria.objects.filter(usuario=request.user)
    pagina = Paginator(registros, 20).get_page(request.GET.get("page"))
    return render(request, "hato/auditoria.html", {"pagina": pagina})
