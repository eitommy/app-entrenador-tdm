from django.contrib import admin
from .models import Jugador, Entrenamiento, Asistencia, Ejercicio, EjercicioRealizado


@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "apellido")


@admin.register(Entrenamiento)
class EntrenamientoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "turno")
    list_filter = ("turno", "fecha")


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ("jugador", "entrenamiento", "estado")
    list_filter = ("estado", "entrenamiento__turno", "entrenamiento__fecha")
    search_fields = ("jugador__nombre", "jugador__apellido")


@admin.register(Ejercicio)
class EjercicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre",)


@admin.register(EjercicioRealizado)
class EjercicioRealizadoAdmin(admin.ModelAdmin):
    list_display = ("jugador", "fecha", "ejercicio")
    list_filter = ("fecha", "ejercicio__categoria")
    search_fields = ("jugador__nombre", "jugador__apellido", "ejercicio__nombre")