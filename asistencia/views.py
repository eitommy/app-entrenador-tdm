from datetime import datetime, timedelta

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import JugadorForm, EjercicioForm
from .models import (
    Asistencia,
    Ejercicio,
    EjercicioRealizado,
    Entrenamiento,
    Jugador,
)


def obtener_o_crear_entrenamiento(fecha, turno):
    entrenamiento, _ = Entrenamiento.objects.get_or_create(fecha=fecha, turno=turno)
    return entrenamiento


def inicio(request):
    hoy = timezone.localdate()

    turnos_info = []
    for turno in [1, 2, 3]:
        entrenamiento = obtener_o_crear_entrenamiento(hoy, turno)
        cantidad_jugadores = Asistencia.objects.filter(entrenamiento=entrenamiento).count()

        turnos_info.append({
            "turno": turno,
            "cantidad_jugadores": cantidad_jugadores,
        })

    contexto = {
        "hoy": hoy,
        "turnos_info": turnos_info,
        "total_jugadores": Jugador.objects.filter(activo=True).count(),
        "total_ejercicios": Ejercicio.objects.filter(activo=True).count(),
    }
    return render(request, "asistencia/inicio.html", contexto)

def ir_a_fecha_asistencia(request):
    fecha_str = request.GET.get("fecha")
    turno = request.GET.get("turno", 1)

    if not fecha_str:
        fecha_str = timezone.localdate().isoformat()

    return redirect("dia_turno", fecha_str=fecha_str, turno=int(turno))


def dia_turno(request, fecha_str, turno):
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    turno = int(turno)

    entrenamiento = obtener_o_crear_entrenamiento(fecha, turno)
    asistencias = Asistencia.objects.filter(entrenamiento=entrenamiento).select_related("jugador")

    jugadores_disponibles = Jugador.objects.filter(activo=True).exclude(
        id__in=asistencias.values_list("jugador_id", flat=True)
    )

    contexto = {
        "entrenamiento": entrenamiento,
        "asistencias": asistencias,
        "jugadores_disponibles": jugadores_disponibles,
        "fecha": fecha,
        "turno": turno,
        "ayer": fecha - timedelta(days=1),
        "maniana": fecha + timedelta(days=1),
        "hoy": timezone.localdate(),
    }
    return render(request, "asistencia/dia_turno.html", contexto)


@require_POST
def agregar_jugador(request, entrenamiento_id):
    entrenamiento = get_object_or_404(Entrenamiento, id=entrenamiento_id)
    jugador_id = request.POST.get("jugador_id")
    jugador = get_object_or_404(Jugador, id=jugador_id, activo=True)

    Asistencia.objects.get_or_create(jugador=jugador, entrenamiento=entrenamiento)
    return redirect("dia_turno", fecha_str=entrenamiento.fecha.isoformat(), turno=entrenamiento.turno)


@require_POST
def copiar_lista_ayer(request, entrenamiento_id):
    entrenamiento_actual = get_object_or_404(Entrenamiento, id=entrenamiento_id)
    fecha_ayer = entrenamiento_actual.fecha - timedelta(days=1)

    try:
        entrenamiento_ayer = Entrenamiento.objects.get(
            fecha=fecha_ayer,
            turno=entrenamiento_actual.turno
        )
    except Entrenamiento.DoesNotExist:
        messages.warning(request, "No hay lista del día anterior para copiar.")
        return redirect(
            "dia_turno",
            fecha_str=entrenamiento_actual.fecha.isoformat(),
            turno=entrenamiento_actual.turno
        )

    asistencias_ayer = Asistencia.objects.filter(entrenamiento=entrenamiento_ayer)

    copiados = 0
    for asistencia in asistencias_ayer:
        _, created = Asistencia.objects.get_or_create(
            jugador=asistencia.jugador,
            entrenamiento=entrenamiento_actual,
            defaults={"estado": "pendiente"}
        )
        if created:
            copiados += 1

    if copiados:
        messages.success(request, f"Se copiaron {copiados} jugadores del día anterior.")
    else:
        messages.info(request, "La lista ya estaba copiada.")

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento_actual.fecha.isoformat(),
        turno=entrenamiento_actual.turno
    )


@require_POST
def marcar_todos_asistieron(request, entrenamiento_id):
    entrenamiento = get_object_or_404(Entrenamiento, id=entrenamiento_id)
    Asistencia.objects.filter(entrenamiento=entrenamiento).update(estado="asistio")

    messages.success(request, "Todos los jugadores quedaron como asistieron.")
    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno
    )


@require_POST
def quitar_jugador(request, asistencia_id):
    asistencia = get_object_or_404(Asistencia, id=asistencia_id)
    entrenamiento = asistencia.entrenamiento
    asistencia.delete()
    return redirect("dia_turno", fecha_str=entrenamiento.fecha.isoformat(), turno=entrenamiento.turno)


@require_POST
def cambiar_estado(request, asistencia_id):
    asistencia = get_object_or_404(Asistencia, id=asistencia_id)
    estado_nuevo = request.POST.get("estado")

    estados_validos = {"asistio", "ausente", "tarde"}
    if estado_nuevo not in estados_validos:
        return JsonResponse({"ok": False}, status=400)

    if asistencia.estado == estado_nuevo:
        asistencia.estado = "pendiente"
    else:
        asistencia.estado = estado_nuevo

    asistencia.save()

    return JsonResponse({
        "ok": True,
        "estado": asistencia.estado,
    })


def lista_jugadores(request):
    jugadores = Jugador.objects.all()
    return render(request, "asistencia/lista_jugadores.html", {"jugadores": jugadores})


def crear_jugador(request):
    if request.method == "POST":
        form = JugadorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Jugador agregado correctamente.")
            return redirect("lista_jugadores")
    else:
        form = JugadorForm()

    return render(request, "asistencia/form_jugador.html", {
        "form": form,
        "titulo": "Agregar jugador"
    })


def editar_jugador(request, pk):
    jugador = get_object_or_404(Jugador, pk=pk)

    if request.method == "POST":
        form = JugadorForm(request.POST, instance=jugador)
        if form.is_valid():
            form.save()
            messages.success(request, "Jugador editado correctamente.")
            return redirect("lista_jugadores")
    else:
        form = JugadorForm(instance=jugador)

    return render(request, "asistencia/form_jugador.html", {
        "form": form,
        "titulo": "Editar jugador"
    })


def lista_ejercicios(request):
    ejercicios = Ejercicio.objects.all()
    return render(request, "asistencia/lista_ejercicios.html", {"ejercicios": ejercicios})


def crear_ejercicio(request):
    if request.method == "POST":
        form = EjercicioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ejercicio agregado correctamente.")
            return redirect("lista_ejercicios")
    else:
        form = EjercicioForm()

    return render(request, "asistencia/form_ejercicio.html", {
        "form": form,
        "titulo": "Agregar ejercicio"
    })


def editar_ejercicio(request, pk):
    ejercicio = get_object_or_404(Ejercicio, pk=pk)

    if request.method == "POST":
        form = EjercicioForm(request.POST, instance=ejercicio)
        if form.is_valid():
            form.save()
            messages.success(request, "Ejercicio editado correctamente.")
            return redirect("lista_ejercicios")
    else:
        form = EjercicioForm(instance=ejercicio)

    return render(request, "asistencia/form_ejercicio.html", {
        "form": form,
        "titulo": "Editar ejercicio"
    })


def cargar_ejercicios(request):
    jugadores = Jugador.objects.filter(activo=True).order_by("apellido", "nombre")

    jugador_id = request.GET.get("jugador")
    fecha_str = request.GET.get("fecha")

    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    else:
        fecha = timezone.localdate()

    jugador_seleccionado = None
    ejercicios_guardados = []

    ejercicios_por_categoria = {
        "Movilidad": Ejercicio.objects.filter(categoria=Ejercicio.Categoria.MOVILIDAD, activo=True),
        "Reacción": Ejercicio.objects.filter(categoria=Ejercicio.Categoria.REACCION, activo=True),
        "Saque": Ejercicio.objects.filter(categoria=Ejercicio.Categoria.SAQUE, activo=True),
        "Recepción": Ejercicio.objects.filter(categoria=Ejercicio.Categoria.RECEPCION, activo=True),
    }

    if jugador_id:
        jugador_seleccionado = Jugador.objects.filter(id=jugador_id, activo=True).first()
        if jugador_seleccionado:
            ejercicios_guardados = list(
                EjercicioRealizado.objects.filter(
                    jugador=jugador_seleccionado,
                    fecha=fecha
                ).values_list("ejercicio_id", flat=True)
            )

    contexto = {
        "jugadores": jugadores,
        "jugador_seleccionado": jugador_seleccionado,
        "fecha": fecha,
        "ejercicios_por_categoria": ejercicios_por_categoria,
        "ejercicios_guardados": ejercicios_guardados,
        "hoy": timezone.localdate(),
    }
    return render(request, "asistencia/cargar_ejercicios.html", contexto)


@require_POST
def guardar_ejercicios(request):
    jugador_id = request.POST.get("jugador_id")
    fecha_str = request.POST.get("fecha")
    ejercicio_ids = request.POST.getlist("ejercicios")

    jugador = get_object_or_404(Jugador, id=jugador_id, activo=True)

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        fecha = timezone.localdate()

    EjercicioRealizado.objects.filter(
        jugador=jugador,
        fecha=fecha
    ).delete()

    for ejercicio_id in ejercicio_ids:
        ejercicio = Ejercicio.objects.filter(id=ejercicio_id, activo=True).first()
        if ejercicio:
            EjercicioRealizado.objects.get_or_create(
                jugador=jugador,
                fecha=fecha,
                ejercicio=ejercicio
            )

    messages.success(request, f"Ejercicios guardados para {jugador}.")
    return redirect(f"/ejercicios/cargar/?jugador={jugador.id}&fecha={fecha.isoformat()}")


def seguimiento_semanal(request):
    jugadores = Jugador.objects.filter(activo=True)

    jugador_id = request.GET.get("jugador")
    fecha_str = request.GET.get("fecha")

    if fecha_str:
        try:
            fecha_base = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha_base = timezone.localdate()
    else:
        fecha_base = timezone.localdate()

    inicio_semana = fecha_base - timedelta(days=fecha_base.weekday())
    dias_semana = [inicio_semana + timedelta(days=i) for i in range(5)]

    jugador_seleccionado = None
    filas = []
    resumen = None

    if jugador_id:
        jugador_seleccionado = Jugador.objects.filter(id=jugador_id, activo=True).first()

        if jugador_seleccionado:
            total_dias_programados = 0
            total_asistencias = 0
            total_tardes = 0
            total_ausencias = 0

            for dia in dias_semana:
                asistencias_dia = Asistencia.objects.filter(
                    jugador=jugador_seleccionado,
                    entrenamiento__fecha=dia
                ).select_related("entrenamiento")

                turnos = list(asistencias_dia.values_list("entrenamiento__turno", flat=True))
                estados = list(asistencias_dia.values_list("estado", flat=True))

                if asistencias_dia.exists():
                    total_dias_programados += 1

                if "asistio" in estados or "tarde" in estados:
                    total_asistencias += 1

                if "tarde" in estados:
                    total_tardes += 1

                if "ausente" in estados and "asistio" not in estados and "tarde" not in estados:
                    total_ausencias += 1

                ejercicios_qs = EjercicioRealizado.objects.filter(
                    jugador=jugador_seleccionado,
                    fecha=dia
                ).select_related("ejercicio").order_by("ejercicio__categoria", "ejercicio__nombre")

                ejercicios_por_categoria = {}
                for item in ejercicios_qs:
                    categoria = item.ejercicio.get_categoria_display()
                    ejercicios_por_categoria.setdefault(categoria, []).append(item.ejercicio.nombre)

                if "asistio" in estados:
                    asistencia_texto = "Asistió"
                elif "tarde" in estados:
                    asistencia_texto = "Tarde"
                elif "ausente" in estados:
                    asistencia_texto = "Ausente"
                else:
                    asistencia_texto = "-"

                filas.append({
                    "dia": dia,
                    "asistencia": asistencia_texto,
                    "turnos": ", ".join([str(t) for t in sorted(set(turnos))]) if turnos else "-",
                    "ejercicios_por_categoria": ejercicios_por_categoria,
                })

            porcentaje = round((total_asistencias / total_dias_programados) * 100, 1) if total_dias_programados else 0

            resumen = {
                "total_dias_programados": total_dias_programados,
                "total_asistencias": total_asistencias,
                "total_tardes": total_tardes,
                "total_ausencias": total_ausencias,
                "porcentaje": porcentaje,
            }

    contexto = {
        "jugadores": jugadores,
        "jugador_seleccionado": jugador_seleccionado,
        "fecha_base": fecha_base,
        "filas": filas,
        "resumen": resumen,
    }
    return render(request, "asistencia/seguimiento_semanal.html", contexto)


def reportes(request):
    hoy = timezone.localdate()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    datos = []
    for jugador in Jugador.objects.filter(activo=True):
        sem = Asistencia.objects.filter(
            jugador=jugador,
            entrenamiento__fecha__range=[inicio_semana, hoy]
        )
        mes = Asistencia.objects.filter(
            jugador=jugador,
            entrenamiento__fecha__range=[inicio_mes, hoy]
        )

        sem_total = sem.count()
        sem_ok = sem.filter(Q(estado="asistio") | Q(estado="tarde")).count()
        sem_pct = round((sem_ok / sem_total) * 100, 1) if sem_total else 0

        mes_total = mes.count()
        mes_ok = mes.filter(Q(estado="asistio") | Q(estado="tarde")).count()
        mes_pct = round((mes_ok / mes_total) * 100, 1) if mes_total else 0

        datos.append({
            "jugador": jugador,
            "sem_total": sem_total,
            "sem_ok": sem_ok,
            "sem_pct": sem_pct,
            "mes_total": mes_total,
            "mes_ok": mes_ok,
            "mes_pct": mes_pct,
        })

    return render(request, "asistencia/reportes.html", {"datos": datos, "hoy": hoy})