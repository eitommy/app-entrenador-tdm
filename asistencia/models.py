from django.db import models


class Jugador(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellido}".strip()


class Entrenamiento(models.Model):
    TURNOS = [
        (1, "Turno 1"),
        (2, "Turno 2"),
        (3, "Turno 3"),
    ]

    fecha = models.DateField()
    turno = models.PositiveSmallIntegerField(choices=TURNOS)

    class Meta:
        unique_together = ("fecha", "turno")
        ordering = ["-fecha", "turno"]

    def __str__(self):
        return f"{self.fecha} - Turno {self.turno}"


class Asistencia(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("asistio", "Asistió"),
        ("ausente", "Ausente"),
        ("tarde", "Tarde"),
    ]

    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="asistencias")
    entrenamiento = models.ForeignKey(Entrenamiento, on_delete=models.CASCADE, related_name="asistencias")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    class Meta:
        unique_together = ("jugador", "entrenamiento")
        ordering = ["jugador__apellido", "jugador__nombre"]

    def __str__(self):
        return f"{self.jugador} - {self.entrenamiento} - {self.estado}"


class Ejercicio(models.Model):
    class Categoria(models.TextChoices):
        MOVILIDAD = "movilidad", "Movilidad"
        REACCION = "reaccion", "Reacción"
        SAQUE = "saque", "Saque"
        RECEPCION = "recepcion", "Recepción"

    nombre = models.CharField(max_length=150)
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.MOVILIDAD,
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["categoria", "nombre"]
        unique_together = ("nombre", "categoria")

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.nombre}"


class EjercicioRealizado(models.Model):
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="ejercicios_realizados")
    fecha = models.DateField()
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE, related_name="realizaciones")

    class Meta:
        unique_together = ("jugador", "fecha", "ejercicio")
        ordering = ["-fecha", "jugador__apellido", "ejercicio__categoria", "ejercicio__nombre"]

    def __str__(self):
        return f"{self.jugador} - {self.fecha} - {self.ejercicio}"