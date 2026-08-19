from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Crea o resetea el usuario entrenador"

    def handle(self, *args, **options):
        User.objects.filter(username="entrenador").delete()

        user = User.objects.create_user(
            username="entrenador",
            password="entrenador123",
        )

        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.save()

        self.stdout.write(
            self.style.SUCCESS("Usuario entrenador creado correctamente")
        )