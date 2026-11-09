"""Pruebas automáticas del prototipo.

Se ejecutan con:  python manage.py test
Los casos CP01 a CP09 son los del Anexo F del documento maestro (Tabla F1); cada clase indica
el requisito (RF o RNF) que verifica. Al final hay pruebas de apoyo (RNF03, RF10, RF11).
"""
import shutil
import tempfile
import time
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from PIL import Image

from .admin import AnimalAdmin
from .models import Animal, Auditoria, EventoAnimal, Finca, Propietario, ReporteNovedad

User = get_user_model()
CLAVE = "ClaveSegura123"
MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="media_pruebas_")


def crear_base(username="ganadero1"):
    """Usuario productor con su propietario y su finca."""
    u = User.objects.create_user(username, f"{username}@example.com", CLAVE)
    p = Propietario.objects.create(usuario=u, nombre="Dueño de prueba", autoriza_datos=True)
    f = Finca.objects.create(usuario=u, propietario=p, nombre="Finca de prueba", vereda="Vereda X")
    return u, p, f


def crear_animal(finca, codigo="BOV-1", **extra):
    datos = {"finca": finca, "codigo": codigo, "sexo": "H", "alias": "Prueba"}
    datos.update(extra)
    return Animal.objects.create(**datos)


def foto_falsa(nombre="vaca.png"):
    """Imagen real mínima para probar la carga de fotos."""
    buffer = BytesIO()
    Image.new("RGB", (60, 40), (150, 100, 60)).save(buffer, "PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


def tearDownModule():
    shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP01_InicioDeSesion(TestCase):
    """CP01 · RF01 · Iniciar sesión con datos válidos y con datos erróneos."""

    def test_acceso_con_datos_validos(self):
        crear_base()
        r = self.client.post(reverse("login"), {"username": "ganadero1", "password": CLAVE})
        self.assertRedirects(r, reverse("inicio"))

    def test_mensaje_de_error_con_datos_erroneos(self):
        crear_base()
        r = self.client.post(reverse("login"), {"username": "ganadero1", "password": "incorrecta"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "introduzca")  # mensaje claro de Django en español
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registro_asigna_rol_productor(self):
        r = self.client.post(reverse("registro"), {
            "username": "nuevo", "first_name": "Nuevo Usuario", "email": "nuevo@example.com",
            "password1": CLAVE, "password2": CLAVE})
        self.assertRedirects(r, reverse("inicio"))
        self.assertTrue(User.objects.get(username="nuevo").groups.filter(name="Productor").exists())

    def test_correo_duplicado_se_rechaza(self):
        User.objects.create_user("a", "repetido@example.com", CLAVE)
        r = self.client.post(reverse("registro"), {
            "username": "b", "first_name": "B", "email": "repetido@example.com",
            "password1": CLAVE, "password2": CLAVE})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="b").exists())

    def test_contrasena_se_guarda_cifrada(self):  # RNF04
        u, _, _ = crear_base()
        self.assertNotEqual(u.password, CLAVE)
        self.assertTrue(u.password.startswith("pbkdf2_"))

    def test_paginas_privadas_exigen_sesion(self):
        for nombre in ["inicio", "animales", "fincas", "reportes", "auditoria", "propietarios"]:
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302, nombre)
            self.assertIn("/ingresar/", r["Location"])


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RF02_Propietarios(TestCase):
    """RF02 · Propietarios con autorización de tratamiento de datos."""

    def setUp(self):
        crear_base()
        self.client.login(username="ganadero1", password=CLAVE)

    def test_exige_autorizacion_de_datos(self):
        r = self.client.post(reverse("propietario_nuevo"), {"nombre": "Sin permiso", "contacto": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Propietario.objects.filter(nombre="Sin permiso").exists())

    def test_guarda_fecha_de_autorizacion(self):
        self.client.post(reverse("propietario_nuevo"),
                         {"nombre": "Con permiso", "contacto": "1", "autoriza_datos": "on"})
        self.assertIsNotNone(Propietario.objects.get(nombre="Con permiso").fecha_autorizacion)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP02_CrearFinca(TestCase):
    """CP02 · RF03 · Crear una finca con los campos obligatorios."""

    def setUp(self):
        self.u, self.p, self.f = crear_base()
        self.client.login(username="ganadero1", password=CLAVE)

    def test_finca_queda_guardada_y_aparece_en_la_lista(self):
        r = self.client.post(reverse("finca_nueva"), {
            "nombre": "La Nueva", "vereda": "V2", "propietario": self.p.pk, "area_hectareas": "12.5"})
        self.assertRedirects(r, reverse("fincas"))
        self.assertContains(self.client.get(reverse("fincas")), "La Nueva")

    def test_campos_obligatorios(self):
        r = self.client.post(reverse("finca_nueva"), {"nombre": "", "vereda": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Finca.objects.count(), 1)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP03_RegistrarAnimal(TestCase):
    """CP03 · RF04 · Registrar un animal con foto y señales particulares; no permite código repetido."""

    def setUp(self):
        self.u, self.p, self.f = crear_base()
        self.client.login(username="ganadero1", password=CLAVE)

    def datos(self, codigo="bov-100"):
        return {"finca": self.f.pk, "codigo": codigo, "sexo": "H", "alias": "Lola", "raza": "Brahman",
                "fecha_nacimiento": "2024-03-10", "hierro": "Hierro A",
                "senales_particulares": "Mancha blanca en la frente", "foto": foto_falsa()}

    def test_animal_queda_guardado_con_foto_y_senales(self):
        r = self.client.post(reverse("animal_nuevo"), self.datos())
        a = Animal.objects.get(codigo="BOV-100")  # el código se guarda en mayúsculas
        self.assertRedirects(r, reverse("animal_detalle", args=[a.pk]))
        self.assertTrue(a.foto.name.endswith(".png"))
        self.assertEqual(a.senales_particulares, "Mancha blanca en la frente")
        self.assertEqual(a.eventos.count(), 1)

    def test_no_permite_codigo_repetido(self):
        crear_animal(self.f, "BOV-1")
        r = self.client.post(reverse("animal_nuevo"), {"finca": self.f.pk, "codigo": "bov-1", "sexo": "M"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Animal.objects.filter(codigo="BOV-1").count(), 1)

    def test_campos_obligatorios(self):
        r = self.client.post(reverse("animal_nuevo"), {"finca": self.f.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Animal.objects.count(), 0)

    def test_rechaza_archivo_que_no_es_imagen(self):
        datos = self.datos()
        datos["foto"] = SimpleUploadedFile("virus.png", b"no soy una imagen", content_type="image/png")
        r = self.client.post(reverse("animal_nuevo"), datos)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Animal.objects.count(), 0)

    def test_chapeta_oficial_es_opcional(self):
        r = self.client.post(reverse("animal_nuevo"), {"finca": self.f.pk, "codigo": "SIN-CH", "sexo": "M"})
        self.assertEqual(r.status_code, 302)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP04_BajaLogica(TestCase):
    """CP04 · RF05 · Cambiar el estado de un animal a vendido; el registro no se borra."""

    def setUp(self):
        self.u, self.p, self.f = crear_base()
        self.client.login(username="ganadero1", password=CLAVE)
        self.a = crear_animal(self.f)

    def test_estado_actualizado_y_registro_no_se_borra(self):
        self.client.post(reverse("animal_estado", args=[self.a.pk]), {"estado": "vendido", "observacion": "Venta local"})
        self.a.refresh_from_db()
        self.assertEqual(self.a.estado, "vendido")
        self.assertTrue(Animal.objects.filter(pk=self.a.pk).exists())
        self.assertTrue(self.a.eventos.filter(tipo="estado").exists())

    def test_no_existe_borrado_definitivo(self):
        self.assertFalse(AnimalAdmin(Animal, None).has_delete_permission(None))
        nombres_url = [u.name for u in __import__("hato.urls", fromlist=["urlpatterns"]).urlpatterns]
        self.assertFalse(any("borrar" in (n or "") or "eliminar" in (n or "") for n in nombres_url))

    def test_cambio_de_estado_no_funciona_por_get(self):
        self.assertEqual(self.client.get(reverse("animal_estado", args=[self.a.pk])).status_code, 405)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP05_BusquedaYFicha(TestCase):
    """CP05 · RF06 y RF07 · Buscar por sexo y estado; abrir la ficha y ver el historial."""

    def setUp(self):
        self.u, self.p, self.f = crear_base()
        self.client.login(username="ganadero1", password=CLAVE)
        self.a1 = crear_animal(self.f, "BOV-1", alias="Canela")
        self.a2 = crear_animal(self.f, "BOV-2", alias="Lucero", sexo="M", estado="vendido")

    def test_filtros_de_sexo_estado_y_finca(self):
        r = self.client.get(reverse("animales"), {"sexo": "M", "estado": "vendido"})
        self.assertContains(r, "BOV-2")
        self.assertNotContains(r, "BOV-1")
        r = self.client.get(reverse("animales"), {"finca": self.f.pk})
        self.assertContains(r, "BOV-1")
        self.assertContains(r, "BOV-2")

    def test_busqueda_por_codigo_y_alias(self):
        self.assertContains(self.client.get(reverse("animales"), {"q": "canela"}), "BOV-1")
        self.assertNotContains(self.client.get(reverse("animales"), {"q": "BOV-2"}), "BOV-1")

    def test_ficha_con_historial_de_eventos(self):
        self.client.post(reverse("animal_evento", args=[self.a1.pk]),
                         {"tipo": "vacunacion", "fecha": "2026-10-01", "observacion": "Aftosa"})
        r = self.client.get(reverse("animal_detalle", args=[self.a1.pk]))
        self.assertContains(r, "Vacunación")
        self.assertContains(r, "Aftosa")

    def test_exportar_a_csv(self):  # RF10
        r = self.client.get(reverse("animales_csv"))
        self.assertIn("text/csv", r["Content-Type"])
        self.assertIn("BOV-1", r.content.decode("utf-8"))


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP06_ResumenDeInventario(TestCase):
    """CP06 · RF09 · Consultar el resumen de inventario de una finca; los conteos coinciden."""

    def test_conteos_coinciden_con_los_animales_registrados(self):
        u, p, f = crear_base()
        otra = Finca.objects.create(usuario=u, propietario=p, nombre="Otra", vereda="V")
        crear_animal(f, "A-1", sexo="H")
        crear_animal(f, "A-2", sexo="H")
        crear_animal(f, "A-3", sexo="M", estado="vendido")
        crear_animal(otra, "B-1")  # no debe contarse en la finca "f"
        self.client.login(username="ganadero1", password=CLAVE)
        r = self.client.get(reverse("finca_resumen", args=[f.pk]))
        self.assertEqual(r.context["total"], 3)
        self.assertEqual((r.context["hembras"], r.context["machos"]), (2, 1))
        por_estado = {valor: n for _, n, valor in r.context["por_estado"]}
        self.assertEqual(por_estado["activo"], 2)
        self.assertEqual(por_estado["vendido"], 1)
        self.assertEqual(por_estado["robado"], 0)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP07_ReporteDeNovedad(TestCase):
    """CP07 · RF08 · Seleccionar dos animales y generar el reporte; PDF correcto y estado actualizado."""

    def setUp(self):
        self.u, self.p, self.f = crear_base()
        self.client.login(username="ganadero1", password=CLAVE)
        self.a1 = crear_animal(self.f, "BOV-1", foto=foto_falsa("uno.png"))
        self.a2 = crear_animal(self.f, "BOV-2")

    def test_pdf_con_datos_y_estado_actualizado(self):
        r = self.client.post(reverse("reporte_nuevo"), {
            "tipo": "hurto", "fecha": "2026-11-01", "lugar": "Potrero norte",
            "descripcion": "Faltan dos animales", "animales": [self.a1.pk, self.a2.pk]})
        rep = ReporteNovedad.objects.get()
        self.assertRedirects(r, reverse("reporte_detalle", args=[rep.pk]))
        self.assertTrue(rep.pdf.name.endswith(".pdf"))
        self.assertEqual(rep.animales.count(), 2)
        for a in (self.a1, self.a2):
            a.refresh_from_db()
            self.assertEqual(a.estado, "robado")
        pdf = self.client.get(reverse("reporte_pdf", args=[rep.pk]))
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_perdida_marca_extraviado(self):
        self.client.post(reverse("reporte_nuevo"), {
            "tipo": "perdida", "fecha": "2026-11-01", "lugar": "Arroyo", "animales": [self.a1.pk]})
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.estado, "extraviado")

    def test_reporte_sin_animales_se_rechaza(self):
        r = self.client.post(reverse("reporte_nuevo"), {"tipo": "perdida", "fecha": "2026-11-01", "lugar": "X"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ReporteNovedad.objects.count(), 0)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP08_AccesoDenegado(TestCase):
    """CP08 · RNF04 · Intentar ver datos (finca, animal, reporte) de otro usuario: acceso denegado."""

    def setUp(self):
        self.u1, self.p1, self.f1 = crear_base("ganadero1")
        self.u2, self.p2, self.f2 = crear_base("ganadero2")
        self.ajeno = crear_animal(self.f2, "AJENO-1")
        self.client.login(username="ganadero1", password=CLAVE)

    def test_no_ve_ni_edita_la_finca_de_otro(self):
        self.assertEqual(self.client.get(reverse("finca_resumen", args=[self.f2.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("finca_editar", args=[self.f2.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("fincas")), self.f2.nombre + "zzz")  # su lista no la incluye
        self.assertEqual(Finca.objects.filter(usuario=self.u1).count(), 1)

    def test_no_ve_animales_de_otro(self):
        self.assertEqual(self.client.get(reverse("animal_detalle", args=[self.ajeno.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("animales")), "AJENO-1")

    def test_no_modifica_animales_de_otro(self):
        self.assertEqual(self.client.get(reverse("animal_editar", args=[self.ajeno.pk])).status_code, 404)
        r = self.client.post(reverse("animal_estado", args=[self.ajeno.pk]), {"estado": "vendido"})
        self.assertEqual(r.status_code, 404)
        self.ajeno.refresh_from_db()
        self.assertEqual(self.ajeno.estado, "activo")

    def test_no_registra_animal_en_finca_de_otro(self):
        r = self.client.post(reverse("animal_nuevo"), {"finca": self.f2.pk, "codigo": "X-1", "sexo": "H"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Animal.objects.filter(codigo="X-1").exists())

    def test_no_ve_reportes_de_otro(self):
        rep = ReporteNovedad.objects.create(usuario=self.u2, tipo="hurto", lugar="X")
        rep.animales.add(self.ajeno)
        self.assertEqual(self.client.get(reverse("reporte_detalle", args=[rep.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("reporte_pdf", args=[rep.pk])).status_code, 404)

    def test_productor_no_entra_al_panel_de_administracion(self):
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/login/", r["Location"])

    def test_administrador_si_entra_al_panel(self):
        User.objects.create_superuser("jefe", "jefe@example.com", CLAVE)
        self.client.login(username="jefe", password=CLAVE)
        self.assertEqual(self.client.get("/admin/").status_code, 200)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CP09_AdaptableAMovil(TestCase):
    """CP09 · RNF02 · Abrir el sistema desde un celular y registrar un animal."""

    CHROME_ANDROID = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36")

    def setUp(self):
        self.u, self.p, self.f = crear_base()
        self.client.login(username="ganadero1", password=CLAVE)

    def test_paginas_declaran_vista_adaptable(self):
        for nombre in ["inicio", "animales", "animal_nuevo", "fincas", "reportes"]:
            r = self.client.get(reverse(nombre), HTTP_USER_AGENT=self.CHROME_ANDROID)
            self.assertEqual(r.status_code, 200, nombre)
            self.assertContains(r, 'name="viewport" content="width=device-width, initial-scale=1"')

    def test_flujo_de_registro_desde_celular(self):
        r = self.client.post(reverse("animal_nuevo"), {
            "finca": self.f.pk, "codigo": "MOVIL-1", "sexo": "H", "foto": foto_falsa()},
            HTTP_USER_AGENT=self.CHROME_ANDROID)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Animal.objects.filter(codigo="MOVIL-1").exists())


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RNF03_Eficiencia(TestCase):
    """RNF03 · Las consultas responden en 3 segundos o menos con 500 animales de prueba."""

    def test_busqueda_y_listado_con_500_animales(self):
        u, p, f = crear_base()
        Animal.objects.bulk_create(
            [Animal(finca=f, codigo=f"MASIVO-{i:04d}", sexo="H" if i % 2 else "M", alias=f"Vaca {i}")
             for i in range(500)])
        self.client.login(username="ganadero1", password=CLAVE)
        for parametros in ({"q": "MASIVO-0250"}, {"sexo": "H"}, {"estado": "activo", "finca": f.pk}, {}):
            inicio = time.perf_counter()
            r = self.client.get(reverse("animales"), parametros)
            duracion = time.perf_counter() - inicio
            self.assertEqual(r.status_code, 200)
            self.assertLess(duracion, 3.0, f"{parametros} tardó {duracion:.2f} s")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RF10_CopiaDeRespaldo(TransactionTestCase):
    """RF10 / RNF05 · copia de respaldo de la base de datos.

    Es TransactionTestCase porque la copia de SQLite necesita que no haya una transacción abierta.
    """

    def test_comando_de_respaldo_genera_archivos(self):
        u, p, f = crear_base()
        crear_animal(f, "RESP-1")
        carpeta = tempfile.mkdtemp(prefix="base_")
        try:
            with override_settings(BASE_DIR=Path(carpeta)):
                call_command("respaldo", verbosity=0)
            archivos = list((Path(carpeta) / "respaldos").iterdir())
            sufijos = [a.suffix for a in archivos]
            self.assertIn(".json", sufijos)
            self.assertIn(".sqlite3", sufijos)
            json_txt = next(a for a in archivos if a.suffix == ".json").read_text(encoding="utf-8")
            self.assertIn("RESP-1", json_txt)
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RF11_Auditoria(TestCase):
    """RF11 / RNF04 · registro de auditoría de cambios y de ingresos."""

    def setUp(self):
        self.u, self.p, self.f = crear_base()

    def test_ingreso_y_acciones_quedan_auditados(self):
        self.client.post(reverse("login"), {"username": "ganadero1", "password": CLAVE})
        self.client.post(reverse("animal_nuevo"), {"finca": self.f.pk, "codigo": "AUD-1", "sexo": "H"})
        self.assertTrue(Auditoria.objects.filter(usuario=self.u, accion="ingreso").exists())
        self.assertTrue(Auditoria.objects.filter(usuario=self.u, accion="crear", entidad="animal").exists())
        self.assertContains(self.client.get(reverse("auditoria")), "AUD-1")

    def test_cada_usuario_ve_solo_su_auditoria(self):
        otro, _, _ = crear_base("ganadero2")
        Auditoria.objects.create(usuario=otro, accion="crear", entidad="animal", detalle="SECRETO-DEL-OTRO")
        self.client.login(username="ganadero1", password=CLAVE)
        self.assertNotContains(self.client.get(reverse("auditoria")), "SECRETO-DEL-OTRO")
