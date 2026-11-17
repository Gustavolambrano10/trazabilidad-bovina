# Historial de cambios

Todos los cambios importantes del prototipo de trazabilidad bovina se registran en este archivo.
El formato sigue la idea de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones usan numeración semántica.

## [1.0.0] - 2026-11-09

Primera versión liberada, entregada en la Fase 4 del proyecto de grado.

### Agregado
- **Cuentas y roles (RF01):** registro e inicio de sesión; los usuarios nuevos quedan en el grupo Productor; el Administrador usa el permiso de personal.
- **Propietarios (RF02):** registro con autorización de tratamiento de datos y fecha de autorización.
- **Fincas (RF03) y resumen por finca (RF09):** crear, editar y ver el conteo de animales por sexo y estado.
- **Animales (RF04, RF05):** registro con código único, chapeta, alias, sexo, raza, fecha de nacimiento, señales, hierro y foto; cambio de estado sin borrado definitivo.
- **Búsqueda e historial (RF06, RF07):** búsqueda por código, chapeta, alias, hierro o raza, con filtros y paginación; ficha del animal con eventos.
- **Reporte de pérdida o hurto (RF08):** reporte con varios animales, cambio automático de estado y PDF generado con ReportLab.
- **Exportación y respaldo (RF10):** inventario en CSV y comando `python manage.py respaldo`.
- **Auditoría (RF11):** registro de ingresos, salidas y cambios, con pantalla de actividad por usuario.
- **Datos de demostración:** comando `python manage.py cargar_demo` con datos ficticios.
- **Pruebas automáticas:** 39 pruebas (`python manage.py test`).

### Seguridad
- Contraseñas cifradas, protección CSRF y acceso limitado a los datos propios de cada usuario.
- Modo producción (`PRODUCCION=1`) con redirección a HTTPS, cookies seguras y HSTS.
- Cambios de estado solo por solicitud POST; el panel de administración no permite borrar animales.

### Despliegue
- Publicado en PythonAnywhere: https://gustavolambrano.pythonanywhere.com/

### Pendiente
- Validación con productores reales de San Pedro (Sucre) y entrevistas de diagnóstico.
- Prueba en teléfonos físicos y modo sin conexión.

## Relación entre funcionalidades y requerimientos

| Requerimiento | Funcionalidad en el prototipo |
|---|---|
| RF01 | Cuentas, inicio de sesión y roles |
| RF02 | Propietarios con autorización de datos |
| RF03 | Fincas |
| RF04 | Registro de animales |
| RF05 | Edición y cambio de estado |
| RF06 | Búsqueda y filtros |
| RF07 | Ficha e historial del animal |
| RF08 | Reporte de novedad con PDF |
| RF09 | Resumen por finca |
| RF10 | Exportación CSV y respaldo |
| RF11 | Auditoría y pantalla de actividad |
