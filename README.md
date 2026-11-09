# Prototipo web de trazabilidad del ganado bovino — San Pedro, Sucre

Prototipo funcional (TRL 5) desarrollado en **Python + Django** como parte del proyecto de grado
de Ingeniería de Sistemas (UNAD). Apoya la prevención del abigeato permitiendo a los productores
registrar su ganado, consultar su historial y generar un reporte en PDF cuando hay una pérdida o un hurto.

## Qué hace (módulos)

| Módulo | Qué permite |
|---|---|
| Cuenta y roles | Registro, ingreso y salida. Contraseñas cifradas. Roles: **Productor** (usa el sistema) y **Administrador** (panel `/admin/`, gestiona usuarios y soporte). |
| Propietarios | Registro con autorización de tratamiento de datos (Ley 1581 de 2012). |
| Fincas | Crear y editar fincas (vereda, área, propietario) y **resumen de inventario por finca**. |
| Animales | Registro con código, chapeta, hierro, señales particulares y foto. Edición y baja lógica (nunca se borran definitivamente). |
| Búsqueda | Por código, chapeta, alias, hierro o raza, con filtros de estado, sexo y finca. |
| Historial | Eventos por animal (vacunación, traslado, venta, etc.) y cambios de estado. |
| Reportes | Reporte de pérdida o hurto con PDF descargable. Cambia el estado de los animales. |
| Exportar y respaldo | Inventario en CSV (se abre en Excel) y comando de copia de respaldo de la base de datos. |
| Actividad | Auditoría de ingresos, salidas y cambios: quién hizo qué y cuándo. |

Cada productor **solo ve y modifica sus propios datos**.

## Tecnologías

Python 3.11+, Django 5.x, SQLite (desarrollo) o PostgreSQL (producción), ReportLab (PDF),
Pillow (fotos), HTML/CSS responsive, Git y GitHub.

## Cómo ejecutarlo en su computador

1. Instalar **Python 3.11 o superior** desde https://www.python.org/downloads/
   (en Windows, marcar la casilla *"Add Python to PATH"*).
2. Abrir una terminal dentro de la carpeta del proyecto (en Visual Studio Code: *Terminal → Nueva terminal*).
3. Crear y activar un entorno virtual:

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux / Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

4. Instalar las dependencias:

   ```bash
   pip install Django reportlab Pillow
   ```

5. Crear la base de datos y cargar datos de demostración (ficticios):

   ```bash
   python manage.py migrate
   python manage.py cargar_demo
   ```

6. Iniciar el servidor:

   ```bash
   python manage.py runserver
   ```

7. Abrir en el navegador http://127.0.0.1:8000/ e ingresar con:

   - Productor: usuario `demo`, contraseña `Demo12345!`
   - Administrador: usuario `admin_demo`, contraseña `Admin12345!` (entra también a `/admin/`)

   Estos usuarios son solo para pruebas locales. No ejecute `cargar_demo` en un servidor real.

Para crear otro administrador: `python manage.py createsuperuser`.

## Copia de respaldo (RF10 y RNF05)

```bash
python manage.py respaldo
```

Crea en la carpeta `respaldos/` un archivo `.json` con todos los datos y, si se usa SQLite, una copia del archivo `.sqlite3`.
Se recomienda ejecutarlo al menos una vez por semana durante el piloto. Para restaurar en una base nueva:

```bash
python manage.py migrate
python manage.py loaddata respaldos/respaldo_AAAAMMDD_HHMM.json
```

## Pruebas automáticas

```bash
python manage.py test
```

Ejecuta 39 pruebas. Los casos CP01 a CP09 son los del Anexo F del documento maestro:

| Caso | Requisito | Qué verifica |
|---|---|---|
| CP01 | RF01 | Inicio de sesión con datos válidos y erróneos; rol Productor al registrarse |
| CP02 | RF03 | Crear una finca con campos obligatorios |
| CP03 | RF04 | Registrar animal con foto y señales; sin códigos repetidos |
| CP04 | RF05 | Cambiar estado a vendido; el registro no se borra |
| CP05 | RF06 y RF07 | Búsqueda por sexo y estado; ficha con historial |
| CP06 | RF09 | Resumen de inventario por finca |
| CP07 | RF08 | Reporte de dos animales en PDF y cambio de estado |
| CP08 | RNF04 | Acceso denegado a datos de otro usuario y al panel de administración |
| CP09 | RNF02 | Páginas adaptables y registro de un animal desde un celular |

Además: RNF03 (consultas en 3 s o menos con 500 animales), RF10 (respaldo) y RF11 (auditoría).

## Estructura

```
config/            configuración del proyecto Django
hato/models.py     modelos (Propietario, Finca, Animal, EventoAnimal, ReporteNovedad, Auditoria)
hato/views.py      lógica de cada pantalla
hato/forms.py      formularios y validaciones
hato/pdf.py        generación del reporte en PDF
hato/signals.py    auditoría de ingreso y salida
hato/management/   comandos: cargar_demo y respaldo
hato/templates/    pantallas HTML
hato/static/       estilos CSS
hato/tests.py      pruebas automáticas
```

## Subirlo a GitHub

```bash
git init
git add .
git commit -m "Prototipo funcional de trazabilidad bovina"
git branch -M main
git remote add origin https://github.com/SU_USUARIO/trazabilidad-bovina.git
git push -u origin main
```

Luego, en GitHub: *Settings → Collaborators* (o *Manage access*) y dar acceso de lectura al tutor.

## Publicarlo en internet (opcional)

Se incluyen `build.sh` y `Procfile` pensados para un hosting tipo Render. Variables de entorno:
`PRODUCCION=1`, `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS` (su dominio) y `CSRF_TRUSTED_ORIGINS` (`https://su-dominio`).
Para PostgreSQL basta con `DATABASE_URL` (o `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`).
Con `PRODUCCION=1` se activan HTTPS, cookies seguras y HSTS. Comando de construcción: `./build.sh`; de inicio: `gunicorn config.wsgi`.
La revisión `python manage.py check --deploy` solo deja dos avisos opcionales (HSTS para subdominios y precarga).

Ojo: en los hosting gratuitos el disco es temporal, por lo que las fotos subidas pueden perderse al reiniciar.
Para el piloto conviene un almacenamiento persistente o repetir la carga de fotos.
El despliegue no se ha probado en un hosting real; hay que verificarlo al publicarlo.

## Alcance y limitaciones

Es un prototipo académico. Los datos de demostración son ficticios. No se conecta a los sistemas
oficiales del ICA ni de la Policía, y el PDF generado no reemplaza una denuncia formal.
