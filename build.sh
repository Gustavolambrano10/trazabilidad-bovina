#!/usr/bin/env bash
# Comandos de construcción para un hosting tipo Render (Sprint 5: despliegue con HTTPS).
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
