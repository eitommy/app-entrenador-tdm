from django.core.management.base import BaseCommand
from asistencia.models import Entrenador


ENTRENADORES = [
    "Matías Pighini",
    "Diego Temperley",
    "Paula Fukuhara",
    "Irina Hambardzumyan"
]


class Command(BaseCommand):
    help = "Crea entrenadores iniciales"

    def handle(self, *args, **options):
        creados = 0
        existentes = 0

        for nombre_completo in ENTRENADORES:
            partes = nombre_completo.split(" ", 1)
            nombre = partes[0]
            apellido = partes[1] if len(partes) > 1 else ""

            entrenador, creado = Entrenador.objects.get_or_create(
                nombre=nombre,
                apellido=apellido,
                defaults={
                    "activo": True,
                },
            )

            if creado:
                creados += 1
            else:
                existentes += 1

                if not entrenador.activo:
                    entrenador.activo = True
                    entrenador.save(update_fields=["activo"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Entrenadores creados: {creados}. Ya existían: {existentes}."
            )
        )