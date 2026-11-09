"""Generación del reporte de novedad en PDF (RF08) con ReportLab."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _foto(animal):
    """Devuelve la foto del animal ajustada, o un texto si no tiene."""
    if animal.foto:
        try:
            img = Image(animal.foto.path)
            ancho_max, alto_max = 4 * cm, 3.5 * cm
            escala = min(ancho_max / img.imageWidth, alto_max / img.imageHeight)
            img.drawWidth = img.imageWidth * escala
            img.drawHeight = img.imageHeight * escala
            return img
        except Exception:
            pass
    return "Sin foto"


def generar_pdf_reporte(reporte):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Reporte de novedad {reporte.id}", author="Trazabilidad Bovina San Pedro",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=estilos["Title"], fontSize=18, textColor=colors.HexColor("#1f5130"))
    normal = estilos["BodyText"]
    chico = ParagraphStyle("c", parent=normal, fontSize=9, leading=11)

    contenido = [
        Paragraph("Reporte de novedad de ganado", titulo),
        Paragraph(f"Reporte N.º {reporte.id} &nbsp;|&nbsp; Generado el {reporte.creado:%d/%m/%Y %H:%M}", chico),
        Spacer(1, 0.4 * cm),
    ]

    # Datos generales del hecho
    nombre_usuario = reporte.usuario.get_full_name() or reporte.usuario.username
    datos = [
        ["Tipo de novedad", reporte.get_tipo_display()],
        ["Fecha del hecho", reporte.fecha.strftime("%d/%m/%Y")],
        ["Lugar", reporte.lugar],
        ["Reportado por", nombre_usuario],
        ["Descripción", Paragraph(reporte.descripcion or "Sin descripción", chico)],
    ]
    t = Table(datos, colWidths=[4 * cm, 13 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e6f0e8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    contenido += [t, Spacer(1, 0.6 * cm), Paragraph("Animales incluidos", estilos["Heading3"])]

    # Una fila por animal, con su foto y señales
    filas = [["Foto", "Datos del animal"]]
    for a in reporte.animales.select_related("finca__propietario").all():
        detalle = (
            f"<b>Código:</b> {a.codigo}<br/>"
            f"<b>Chapeta oficial:</b> {a.chapeta_oficial or '—'}<br/>"
            f"<b>Alias:</b> {a.alias or '—'}<br/>"
            f"<b>Sexo / raza:</b> {a.get_sexo_display()} / {a.raza or '—'}<br/>"
            f"<b>Hierro:</b> {a.hierro or '—'}<br/>"
            f"<b>Señales particulares:</b> {a.senales_particulares or '—'}<br/>"
            f"<b>Finca:</b> {a.finca.nombre} ({a.finca.vereda})<br/>"
            f"<b>Propietario:</b> {a.finca.propietario.nombre}"
        )
        filas.append([_foto(a), Paragraph(detalle, chico)])
    tabla = Table(filas, colWidths=[4.5 * cm, 12.5 * cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f5130")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    contenido += [
        tabla,
        Spacer(1, 0.8 * cm),
        Paragraph(
            "Este documento es un registro de apoyo generado por el prototipo. No reemplaza la denuncia "
            "formal ante la Policía, la Fiscalía o el ICA.",
            chico,
        ),
    ]
    doc.build(contenido)
    return buffer.getvalue()
