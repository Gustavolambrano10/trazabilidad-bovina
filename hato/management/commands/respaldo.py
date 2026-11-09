"""RF10 y RNF05: copia de respaldo de la base de datos.

Uso:  python manage.py respaldo
Genera dos archivos en la carpeta  respaldos/ :
  - respaldo_AAAAMMDD_HHMM.json   (todos los datos, sirve con SQLite o PostgreSQL)
  - respaldo_AAAAMMDD_HHMM.sqlite3 (copia del archivo, solo si se usa SQLite)
Para restaurar el JSON:  python manage.py loaddata respaldos/respaldo_XXXX.json
"""
import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Crea una copia de respaldo de la base de datos en la carpeta respaldos/."

    def handle(self, *args, **opciones):
        carpeta = Path(settings.BASE_DIR) / "respaldos"
        carpeta.mkdir(exist_ok=True)
        marca = timezone.localtime().strftime("%Y%m%d_%H%M")

        archivo_json = carpeta / f"respaldo_{marca}.json"
        with open(archivo_json, "w", encoding="utf-8") as f:
            call_command("dumpdata", "--natural-foreign", "--natural-primary", "--indent", "2",
                         "--exclude", "contenttypes", "--exclude", "auth.permission",
                         "--exclude", "sessions", stdout=f)
        self.stdout.write(self.style.SUCCESS(f"Respaldo de datos: {archivo_json}"))

        if connection.vendor == "sqlite":
            archivo_db = carpeta / f"respaldo_{marca}.sqlite3"
            connection.ensure_connection()
            destino = sqlite3.connect(archivo_db)
            with destino:
                connection.connection.backup(destino)  # copia consistente aunque el sistema esté en uso
            destino.close()
            self.stdout.write(self.style.SUCCESS(f"Copia de la base SQLite: {archivo_db}"))
