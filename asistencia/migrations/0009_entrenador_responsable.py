from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("asistencia", "0008_ejercicioturno"),
    ]

    operations = [
        migrations.CreateModel(
            name="Entrenador",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "nombre",
                    models.CharField(
                        max_length=100,
                    ),
                ),
                (
                    "apellido",
                    models.CharField(
                        blank=True,
                        max_length=100,
                    ),
                ),
                (
                    "activo",
                    models.BooleanField(
                        default=True,
                    ),
                ),
            ],
            options={
                "ordering": ["apellido", "nombre"],
                "verbose_name": "Entrenador",
                "verbose_name_plural": "Entrenadores",
            },
        ),
        migrations.AddField(
            model_name="entrenamiento",
            name="entrenador_responsable",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="entrenamientos_responsables",
                to="asistencia.entrenador",
            ),
        ),
    ]