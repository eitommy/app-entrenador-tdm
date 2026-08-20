from django.core.management.base import BaseCommand
from asistencia.models import Jugador


DEPORTISTAS = [
    ("Ignacio", "Bianchini"),
    ("Isabella", "Olivares"),
    ("Nicolas", "Notturno"),
    ("Ixchel", "Guia Monzon"),
    ("Martina", "Cruz Muñoz"),
    ("Luana", "Salpeter"),
    ("Sofia", "Castellano"),
    ("Matias", "Vivas"),
    ("Bruno", "Di Girolamo"),
    ("Martin", "Bentancor"),
    ("Lorena", "Gitelman"),
    ("Juan Martin", "Molina"),
    ("Mariam", "Shahmuradyan"),
    ("Brisa", "Takahashi"),
    ("Camilo", "Mosteirin"),
    ("Julia", "Perez Mazzarello"),
    ("Malena", "Perez Mazzarello"),
    ("Mia", "Sato"),
    ("Alexia", "Salusso"),
    ("Camila", "Perez"),
    ("Alma", "Marcial"),
    ("Valentino", "Marcial"),
    ("Agustin", "Asmu"),
    ("Abril", "Iwasa"),
    ("Alan", "Nakagama"),
    ("Lautaro", "Sato"),
    ("Nicolas", "Callaba"),
    ("Ernesto", "Romego"),
    ("Sol", "Serrano"),
    ("Dante", "Rubin Minetti"),
    ("Lucas", "Bayona"),
    ("Victoria", "Tan"),
    ("Franco", "Varela"),
    ("Luca", "Muller"),
    ("Santiago", "Uslenghi"),
    ("Leonardo", "Sato"),
    ("Marcos", "Heredia"),
    ("Enzo", "Fernandez"),
    ("Ilan", "Muller"),
    ("Galo", "Rubin Minetti"),
    ("Olivia", "Mansilla"),
    ("Camila", "Cassara"),
    ("Lionel", "Arce"),
    ("Costantino", "Kaladjian"),
    ("Francisco", "Petell"),
    ("Isabella", "Palmerio"),
    ("Ayelen", "Lai"),
    ("Juan Manuel Makoto", "Fiore Shimoji"),
    ("Mia", "Lopez"),
    ("Dror", "Dratewka"),
    ("Juan Cruz", "Axon"),
    ("Chiara", "Bellomo"),
    ("Dante", "Massare"),
    ("Francisco", "Urfeig"),
    ("Francisco", "Crimaldi"),
    ("Luciana", "Frias Paz"),
    ("Giuliano", "La Via"),
    ("Rodrigo", "Gilabert"),
    ("Santiago", "Lorenzo"),
    ("Alexis", "Orencel"),
    ("Leandro", "Fuentes"),
    ("Santino", "Rossi Vera"),
    ("Sebatian", "Bedoya Urquillo"),
    ("Emanuel", "Otalvaro Garcia"),
    ("Mateo", "Carranza"),
    ("Tomas", "Bernardou"),
    ("Thiago", "Spinelli"),
    ("Candela", "Molero"),
    ("Lucia", "Cordero Veliz"),
    ("Camila", "Arguelles"),
    ("Tobias", "Martinez"),
]


class Command(BaseCommand):
    help = "Importa solo deportistas FATM 2026 como jugadores"

    def handle(self, *args, **options):
        creados = 0
        existentes = 0

        for nombre, apellido in DEPORTISTAS:
            jugador, creado = Jugador.objects.get_or_create(
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

                if not jugador.activo:
                    jugador.activo = True
                    jugador.save(
                        update_fields=[
                            "activo",
                        ],
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Importación terminada. Deportistas creados: {creados}. Ya existían: {existentes}."
            )
        )