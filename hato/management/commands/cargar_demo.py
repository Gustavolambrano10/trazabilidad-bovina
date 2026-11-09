"""Carga datos FICTICIOS para probar y grabar la demostración.

Uso:  python manage.py cargar_demo
Crea el productor  demo / Demo12345!  (2 fincas y 12 animales) y el administrador
admin_demo / Admin12345!  Solo para pruebas locales: NO ejecutar en un servidor real.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from hato.models import Animal, EventoAnimal, Finca, Propietario

User = get_user_model()


class Command(BaseCommand):
    help = "Crea un usuario de demostración con datos ficticios."

    def handle(self, *args, **opciones):
        user, creado = User.objects.get_or_create(
            username="demo", defaults={"first_name": "Productor de Demostración", "email": "demo@example.com"}
        )
        if creado:
            user.set_password("Demo12345!")
            user.save()

        from django.contrib.auth.models import Group

        grupo, _ = Group.objects.get_or_create(name="Productor")
        user.groups.add(grupo)
        admin, creado_admin = User.objects.get_or_create(
            username="admin_demo", defaults={"first_name": "Administrador de Demostración",
                                             "email": "admin@example.com", "is_staff": True, "is_superuser": True})
        if creado_admin:
            admin.set_password("Admin12345!")
            admin.save()

        prop, _ = Propietario.objects.get_or_create(
            usuario=user, nombre="Productor Demo (ficticio)",
            defaults={"contacto": "3000000000", "autoriza_datos": True},
        )
        f1, _ = Finca.objects.get_or_create(usuario=user, nombre="La Esperanza", defaults={
            "propietario": prop, "vereda": "Vereda Demo Uno", "area_hectareas": 35})
        f2, _ = Finca.objects.get_or_create(usuario=user, nombre="El Remanso", defaults={
            "propietario": prop, "vereda": "Vereda Demo Dos", "area_hectareas": 20})

        razas = ["Brahman", "Cebú", "Romosinuano", "Brahman cruzado", "Gyr"]
        alias = ["Canela", "Lucero", "Morena", "Tigre", "Paloma", "Bandido",
                 "Estrella", "Cacique", "Luna", "Negro", "Mariposa", "Trueno"]
        nuevos = 0
        for i, nombre in enumerate(alias, start=1):
            codigo = f"BOV-{i:04d}"
            animal, creado_a = Animal.objects.get_or_create(codigo=codigo, defaults={
                "finca": f1 if i <= 8 else f2,
                "alias": nombre,
                "sexo": "H" if i % 3 else "M",
                "raza": razas[i % len(razas)],
                "fecha_nacimiento": date.today() - timedelta(days=400 + i * 60),
                "hierro": f"Hierro demo {1 + i % 3}",
                "senales_particulares": "Mancha blanca en la frente" if i % 2 else "Cola corta, oreja izquierda marcada",
            })
            if creado_a:
                nuevos += 1
                EventoAnimal.objects.create(animal=animal, tipo="nacimiento",
                                            fecha=animal.fecha_nacimiento, observacion="Dato de demostración")
        self.stdout.write(self.style.SUCCESS(
            f"Listo. Productor: demo / Demo12345!  Administrador: admin_demo / Admin12345!  (animales nuevos: {nuevos})"))
