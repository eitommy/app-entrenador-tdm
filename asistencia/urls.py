from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),

    path("ir-a-fecha-asistencia/", views.ir_a_fecha_asistencia, name="ir_a_fecha_asistencia"),

    path("dia/<str:fecha_str>/turno/<int:turno>/", views.dia_turno, name="dia_turno"),

    path("entrenamiento/<int:entrenamiento_id>/agregar-jugador/", views.agregar_jugador, name="agregar_jugador"),
    path("entrenamiento/<int:entrenamiento_id>/copiar-ayer/", views.copiar_lista_ayer, name="copiar_lista_ayer"),
    path("entrenamiento/<int:entrenamiento_id>/todos-asistieron/", views.marcar_todos_asistieron, name="marcar_todos_asistieron"),

    path("asistencia/<int:asistencia_id>/quitar/", views.quitar_jugador, name="quitar_jugador"),
    path("asistencia/<int:asistencia_id>/estado/", views.cambiar_estado, name="cambiar_estado"),

    path("jugadores/", views.lista_jugadores, name="lista_jugadores"),
    path("jugadores/nuevo/", views.crear_jugador, name="crear_jugador"),
    path("jugadores/<int:pk>/editar/", views.editar_jugador, name="editar_jugador"),

    path("ejercicios/", views.lista_ejercicios, name="lista_ejercicios"),
    path("ejercicios/nuevo/", views.crear_ejercicio, name="crear_ejercicio"),
    path("ejercicios/<int:pk>/editar/", views.editar_ejercicio, name="editar_ejercicio"),
    path("ejercicios/cargar/", views.cargar_ejercicios, name="cargar_ejercicios"),
    path("ejercicios/guardar/", views.guardar_ejercicios, name="guardar_ejercicios"),

    path("seguimiento-semanal/", views.seguimiento_semanal, name="seguimiento_semanal"),
    path("reportes/", views.reportes, name="reportes"),
]