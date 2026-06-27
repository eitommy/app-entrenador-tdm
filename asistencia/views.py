from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction

from .forms import (EjercicioForm, EntrenamientoInfoForm, JugadorForm, PerfilForm, RegistroEntrenadorForm
,TrabajoTurnoForm, ObservacionJugadorForm, MotivoAusenciaForm, SetPartidoFormSet,PartidoTurnoForm)
from .models import Asistencia, Ejercicio, EjercicioRealizado, Entrenamiento, Jugador, TrabajoTurno, ObservacionJugador,PartidoTurno


def obtener_o_crear_entrenamiento(fecha, turno):
    entrenamiento, _ = Entrenamiento.objects.get_or_create(fecha=fecha, turno=turno)
    return entrenamiento


def nombre_entrenador(entrenamiento):
    if entrenamiento.entrenador:
        return entrenamiento.entrenador.get_full_name() or entrenamiento.entrenador.username
    return "Sin entrenador"


def asignar_entrenador_si_vacio(entrenamiento, user):
    if user.is_authenticated and entrenamiento.entrenador is None:
        entrenamiento.entrenador = user
        entrenamiento.save()


def registro(request):
    if request.method == "POST":
        form = RegistroEntrenadorForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cuenta creada correctamente.")
            return redirect("inicio")
    else:
        form = RegistroEntrenadorForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def inicio(request):
    fecha_str = request.GET.get("fecha")

    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    else:
        fecha = timezone.localdate()

    turnos_info = []
    total_cargados_dia = 0
    total_marcados_dia = 0

    for turno in [1, 2, 3]:
        entrenamiento = obtener_o_crear_entrenamiento(fecha, turno)

        cantidad_jugadores = Asistencia.objects.filter(entrenamiento=entrenamiento).count()
        cantidad_marcados = Asistencia.objects.filter(entrenamiento=entrenamiento).exclude(
            estado="pendiente"
        ).count()

        total_cargados_dia += cantidad_jugadores
        total_marcados_dia += cantidad_marcados

        turnos_info.append({
            "turno": turno,
            "cantidad_jugadores": cantidad_jugadores,
            "cantidad_marcados": cantidad_marcados,
            "entrenador": nombre_entrenador(entrenamiento),
            "observaciones": entrenamiento.observaciones,
        })

    contexto = {
        "fecha": fecha,
        "hoy": timezone.localdate(),
        "ayer": fecha - timedelta(days=1),
        "maniana": fecha + timedelta(days=1),
        "turnos_info": turnos_info,
        "total_jugadores": Jugador.objects.filter(activo=True).count(),
        "total_ejercicios": Ejercicio.objects.filter(activo=True).count(),
        "total_cargados_dia": total_cargados_dia,
        "total_marcados_dia": total_marcados_dia,
    }
    return render(request, "asistencia/inicio.html", contexto)


@login_required
def ir_a_fecha_asistencia(request):
    fecha_str = request.GET.get("fecha")
    turno = request.GET.get("turno", 1)

    if not fecha_str:
        fecha_str = timezone.localdate().isoformat()

    return redirect("dia_turno", fecha_str=fecha_str, turno=int(turno))


@login_required
def dia_turno(request, fecha_str, turno):
    fecha = datetime.strptime(
        fecha_str,
        "%Y-%m-%d",
    ).date()

    turno = int(turno)

    entrenamiento = obtener_o_crear_entrenamiento(
        fecha,
        turno,
    )

    asistencias = list(
        Asistencia.objects
        .filter(entrenamiento=entrenamiento)
        .select_related("jugador")
    )

    jugadores_disponibles = (
        Jugador.objects
        .filter(activo=True)
        .exclude(
            id__in=[
                asistencia.jugador_id
                for asistencia in asistencias
            ]
        )
        .order_by(
            "apellido",
            "nombre",
        )
    )

    jugadores_ids = [
        asistencia.jugador_id
        for asistencia in asistencias
    ]

    ejercicios_por_jugador = (
        EjercicioRealizado.objects
        .filter(
            jugador_id__in=jugadores_ids,
            fecha=fecha,
        )
        .values("jugador_id")
        .annotate(total=Count("id"))
    )

    ejercicios_contador = {
        item["jugador_id"]: item["total"]
        for item in ejercicios_por_jugador
    }

    for asistencia in asistencias:
        asistencia.ejercicios_cargados = (
            ejercicios_contador.get(
                asistencia.jugador_id,
                0,
            )
        )

        asistencia.observaciones_turno = (
            ObservacionJugador.objects
            .filter(
                jugador=asistencia.jugador,
                entrenamiento=entrenamiento,
            )
            .select_related("creada_por")
            .order_by("-creada_el")
        )

    trabajos_turno = (
        TrabajoTurno.objects
        .filter(entrenamiento=entrenamiento)
        .select_related(
            "jugador_1",
            "jugador_2",
        )
        .order_by(
            "cambio",
            "id",
        )
    )

    jugadores_ocupados_por_cambio = {}

    for trabajo in trabajos_turno:
        cambio_clave = str(trabajo.cambio)

        if cambio_clave not in jugadores_ocupados_por_cambio:
            jugadores_ocupados_por_cambio[
                cambio_clave
            ] = []

        jugadores_ocupados_por_cambio[
            cambio_clave
        ].append(
            trabajo.jugador_1_id
        )

        if trabajo.jugador_2_id:
            jugadores_ocupados_por_cambio[
                cambio_clave
            ].append(
                trabajo.jugador_2_id
            )

    cambios_resumen = []

    numeros_cambio = sorted(
        set(
            trabajos_turno.values_list(
                "cambio",
                flat=True,
            )
        )
    )

    for numero_cambio in numeros_cambio:
        trabajos_del_cambio = (
            trabajos_turno.filter(
                cambio=numero_cambio
            )
        )

        jugadores_asignados_ids = set()

        for trabajo in trabajos_del_cambio:
            jugadores_asignados_ids.add(
                trabajo.jugador_1_id
            )

            if trabajo.jugador_2_id:
                jugadores_asignados_ids.add(
                    trabajo.jugador_2_id
                )

        jugadores_pendientes = [
            asistencia.jugador
            for asistencia in asistencias
            if (
                asistencia.jugador_id
                not in jugadores_asignados_ids
            )
        ]

        cantidad_asignados = len(
            jugadores_asignados_ids
        )

        cantidad_total = len(asistencias)

        cambios_resumen.append({
            "numero": numero_cambio,
            "cantidad_asignados": cantidad_asignados,
            "cantidad_total": cantidad_total,
            "jugadores_pendientes": jugadores_pendientes,
            "completo": (
                cantidad_total > 0
                and cantidad_asignados == cantidad_total
            ),
        })

    trabajos_otros_turnos = (
        TrabajoTurno.objects
        .filter(
            entrenamiento__fecha=fecha,
            entrenamiento__turno__lt=turno,
        )
        .select_related(
            "entrenamiento",
            "jugador_1",
            "jugador_2",
        )
        .order_by(
            "entrenamiento__turno",
            "cambio",
            "id",
        )
    )

    partidos_turno = (
        PartidoTurno.objects
        .filter(entrenamiento=entrenamiento)
        .select_related(
            "jugador_1",
            "jugador_2",
        )
        .prefetch_related("sets")
        .order_by("id")
    )

    # =========================
    # RESUMEN DEL TURNO
    # =========================

    total_jugadores_turno = len(asistencias)

    total_presentes_turno = sum(
        1
        for asistencia in asistencias
        if asistencia.estado == "asistio"
    )

    total_tardes_turno = sum(
        1
        for asistencia in asistencias
        if asistencia.estado == "tarde"
    )

    total_ausentes_turno = sum(
        1
        for asistencia in asistencias
        if asistencia.estado == "ausente"
    )

    total_pendientes_turno = sum(
        1
        for asistencia in asistencias
        if asistencia.estado == "pendiente"
    )

    ausentes_sin_motivo_turno = sum(
        1
        for asistencia in asistencias
        if (
            asistencia.estado == "ausente"
            and not asistencia.motivo_ausencia
        )
    )

    total_trabajos_turno = (
        trabajos_turno.count()
    )

    total_cambios_turno = len(
        cambios_resumen
    )

    cambios_completos_turno = sum(
        1
        for cambio in cambios_resumen
        if cambio["completo"]
    )

    cambios_incompletos_turno = (
        total_cambios_turno
        - cambios_completos_turno
    )

    total_partidos_turno = (
        partidos_turno.count()
    )

    partidos_sin_sets_turno = sum(
        1
        for partido in partidos_turno
        if not partido.sets.all()
    )

    total_observaciones_turno = (
        ObservacionJugador.objects
        .filter(
            entrenamiento=entrenamiento
        )
        .count()
    )

    total_ejercicios_turno = sum(
        ejercicios_contador.values()
    )

    alertas_resumen_turno = []

    if total_jugadores_turno == 0:
        alertas_resumen_turno.append(
            "No hay jugadores cargados."
        )

    if total_pendientes_turno > 0:
        alertas_resumen_turno.append(
            (
                f"Hay {total_pendientes_turno} "
                "jugador(es) con asistencia pendiente."
            )
        )

    if ausentes_sin_motivo_turno > 0:
        alertas_resumen_turno.append(
            (
                f"Hay {ausentes_sin_motivo_turno} "
                "ausencia(s) sin motivo."
            )
        )

    if cambios_incompletos_turno > 0:
        alertas_resumen_turno.append(
            (
                f"Hay {cambios_incompletos_turno} "
                "cambio(s) incompleto(s)."
            )
        )

    if partidos_sin_sets_turno > 0:
        alertas_resumen_turno.append(
            (
                f"Hay {partidos_sin_sets_turno} "
                "partido(s) sin sets."
            )
        )

    if entrenamiento.entrenador is None:
        alertas_resumen_turno.append(
            "El turno no tiene entrenador responsable."
        )

    resumen_turno = {
        "total_jugadores": total_jugadores_turno,
        "presentes": total_presentes_turno,
        "tardes": total_tardes_turno,
        "ausentes": total_ausentes_turno,
        "pendientes": total_pendientes_turno,

        "ausentes_sin_motivo": (
            ausentes_sin_motivo_turno
        ),

        "total_trabajos": total_trabajos_turno,
        "total_cambios": total_cambios_turno,

        "cambios_completos": (
            cambios_completos_turno
        ),

        "cambios_incompletos": (
            cambios_incompletos_turno
        ),

        "total_partidos": total_partidos_turno,

        "partidos_sin_sets": (
            partidos_sin_sets_turno
        ),

        "total_observaciones": (
            total_observaciones_turno
        ),

        "total_ejercicios": (
            total_ejercicios_turno
        ),

        "alertas": alertas_resumen_turno,

        "listo_para_finalizar": (
            total_jugadores_turno > 0
            and total_pendientes_turno == 0
            and ausentes_sin_motivo_turno == 0
            and cambios_incompletos_turno == 0
            and partidos_sin_sets_turno == 0
            and entrenamiento.entrenador is not None
        ),
    }

    contexto = {
        "entrenamiento": entrenamiento,

        "entrenamiento_form": (
            EntrenamientoInfoForm(
                instance=entrenamiento
            )
        ),

        "trabajo_form": (
            TrabajoTurnoForm(
                entrenamiento=entrenamiento
            )
        ),

        "trabajos_turno": trabajos_turno,

        "jugadores_ocupados_por_cambio": (
            jugadores_ocupados_por_cambio
        ),

        "cambios_resumen": cambios_resumen,

        "trabajos_otros_turnos": (
            trabajos_otros_turnos
        ),

        "nombre_entrenador": (
            nombre_entrenador(
                entrenamiento
            )
        ),

        "asistencias": asistencias,

        "jugadores_disponibles": (
            jugadores_disponibles
        ),

        "partidos_turno": partidos_turno,

        "resumen_turno": resumen_turno,

        "fecha": fecha,
        "turno": turno,
        "ayer": fecha - timedelta(days=1),
        "maniana": fecha + timedelta(days=1),
        "hoy": timezone.localdate(),
    }

    return render(
        request,
        "asistencia/dia_turno.html",
        contexto,
    )
    
@login_required
def editar_trabajo_turno(request, trabajo_id):
    trabajo = get_object_or_404(
        TrabajoTurno,
        id=trabajo_id,
    )

    entrenamiento = trabajo.entrenamiento

    if request.method == "POST":
        form = TrabajoTurnoForm(
            request.POST,
            instance=trabajo,
            entrenamiento=entrenamiento,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Trabajo actualizado correctamente.",
            )

            return redirect(
                "dia_turno",
                fecha_str=entrenamiento.fecha.isoformat(),
                turno=entrenamiento.turno,
            )
    else:
        form = TrabajoTurnoForm(
            instance=trabajo,
            entrenamiento=entrenamiento,
        )

    return render(
        request,
        "asistencia/editar_trabajo_turno.html",
        {
            "form": form,
            "trabajo": trabajo,
            "entrenamiento": entrenamiento,
        },
    )



@login_required
@require_POST
def agregar_trabajo_turno(request, entrenamiento_id):
    entrenamiento = get_object_or_404(
        Entrenamiento,
        id=entrenamiento_id,
    )

    form = TrabajoTurnoForm(
        request.POST,
        entrenamiento=entrenamiento,
    )

    if form.is_valid():
        trabajo = form.save(commit=False)
        trabajo.entrenamiento = entrenamiento
        trabajo.save()

        messages.success(
            request,
            f"Trabajo agregado correctamente al cambio {trabajo.cambio}.",
        )
    else:
        errores = []

        for lista_errores in form.errors.values():
            for error in lista_errores:
                errores.append(str(error))

        if errores:
            messages.error(
                request,
                "No se pudo agregar el trabajo: " + " ".join(errores),
            )
        else:
            messages.error(
                request,
                "No se pudo agregar el trabajo. Revisá los datos ingresados.",
            )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )
    
@login_required
def crear_partido_turno(request, entrenamiento_id):
    entrenamiento = get_object_or_404(
        Entrenamiento,
        id=entrenamiento_id,
    )

    if request.method == "POST":
        partido_form = PartidoTurnoForm(
            request.POST,
            entrenamiento=entrenamiento,
        )

        partido_temporal = PartidoTurno(
            entrenamiento=entrenamiento
        )

        sets_formset = SetPartidoFormSet(
            request.POST,
            instance=partido_temporal,
            prefix="sets",
        )

        if partido_form.is_valid() and sets_formset.is_valid():
            with transaction.atomic():
                partido = partido_form.save(commit=False)
                partido.entrenamiento = entrenamiento
                partido.save()

                sets_formset.instance = partido

                sets_guardados = sets_formset.save(
                    commit=False
                )

                numero_set = 1

                for set_partido in sets_guardados:
                    set_partido.partido = partido
                    set_partido.numero = numero_set
                    set_partido.save()

                    numero_set += 1

                for set_eliminado in sets_formset.deleted_objects:
                    if set_eliminado.pk:
                        set_eliminado.delete()

            messages.success(
                request,
                (
                    f"Partido guardado: "
                    f"{partido.jugador_1} "
                    f"{partido.resultado_general} "
                    f"{partido.jugador_2}."
                ),
            )

            return redirect(
                "dia_turno",
                fecha_str=entrenamiento.fecha.isoformat(),
                turno=entrenamiento.turno,
            )
    else:
        partido_form = PartidoTurnoForm(
            entrenamiento=entrenamiento,
        )

        partido_temporal = PartidoTurno(
            entrenamiento=entrenamiento
        )

        sets_formset = SetPartidoFormSet(
            instance=partido_temporal,
            prefix="sets",
        )

    return render(
        request,
        "asistencia/crear_partido_turno.html",
        {
            "entrenamiento": entrenamiento,
            "partido_form": partido_form,
            "sets_formset": sets_formset,
        },
    )


@login_required
@require_POST
def eliminar_trabajo_turno(request, trabajo_id):
    trabajo = get_object_or_404(
        TrabajoTurno,
        id=trabajo_id,
    )

    entrenamiento = trabajo.entrenamiento
    numero_cambio = trabajo.cambio

    trabajo.delete()

    messages.success(
        request,
        f"Trabajo del cambio {numero_cambio} eliminado correctamente.",
    )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )


@login_required
@require_POST
def tomar_turno(request, entrenamiento_id):
    entrenamiento = get_object_or_404(
        Entrenamiento,
        id=entrenamiento_id,
    )

    if entrenamiento.entrenador is None:
        entrenamiento.entrenador = request.user
        entrenamiento.save()
        messages.success(
            request,
            "Tomaste este turno correctamente.",
        )

    elif entrenamiento.entrenador == request.user:
        messages.info(
            request,
            "Este turno ya está asignado a vos.",
        )

    else:
        messages.warning(
            request,
            "Este turno ya fue tomado por otro entrenador.",
        )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )


@login_required
@require_POST
def guardar_info_entrenamiento(request, entrenamiento_id):
    entrenamiento = get_object_or_404(Entrenamiento, id=entrenamiento_id)
    form = EntrenamientoInfoForm(request.POST, instance=entrenamiento)

    if form.is_valid():
        form.save()
        messages.success(request, "Observaciones guardadas correctamente.")
    else:
        messages.error(request, "No se pudieron guardar las observaciones.")

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )
    
@login_required
@require_POST
def finalizar_turno(request, entrenamiento_id):
    entrenamiento = get_object_or_404(
        Entrenamiento,
        id=entrenamiento_id,
    )

    if entrenamiento.finalizado:
        messages.info(
            request,
            "Este turno ya está finalizado.",
        )

        return redirect(
            "dia_turno",
            fecha_str=entrenamiento.fecha.isoformat(),
            turno=entrenamiento.turno,
        )

    errores = []

    asistencias = (
        Asistencia.objects
        .filter(entrenamiento=entrenamiento)
        .select_related("jugador")
    )

    # Debe haber jugadores cargados
    if not asistencias.exists():
        errores.append(
            "El turno no tiene jugadores cargados."
        )

    # Jugadores sin asistencia marcada
    jugadores_pendientes = [
        str(asistencia.jugador)
        for asistencia in asistencias
        if asistencia.estado == "pendiente"
    ]

    if jugadores_pendientes:
        errores.append(
            "Falta marcar la asistencia de: "
            + ", ".join(jugadores_pendientes)
            + "."
        )

    # Ausentes sin motivo
    ausentes_sin_motivo = [
        str(asistencia.jugador)
        for asistencia in asistencias
        if (
            asistencia.estado == "ausente"
            and not asistencia.motivo_ausencia
        )
    ]

    if ausentes_sin_motivo:
        errores.append(
            "Falta cargar el motivo de ausencia de: "
            + ", ".join(ausentes_sin_motivo)
            + "."
        )

    # Debe haber entrenador responsable
    if entrenamiento.entrenador is None:
        errores.append(
            "El turno no tiene un entrenador responsable."
        )

    # Revisar cambios incompletos
    jugadores_que_entrenaron_ids = set(
        asistencias
        .filter(
            Q(estado="asistio")
            | Q(estado="tarde")
        )
        .values_list(
            "jugador_id",
            flat=True,
        )
    )

    trabajos = (
        TrabajoTurno.objects
        .filter(entrenamiento=entrenamiento)
        .select_related(
            "jugador_1",
            "jugador_2",
        )
    )

    numeros_cambio = sorted(
        set(
            trabajos.values_list(
                "cambio",
                flat=True,
            )
        )
    )

    for numero_cambio in numeros_cambio:
        trabajos_del_cambio = trabajos.filter(
            cambio=numero_cambio
        )

        jugadores_asignados_ids = set()

        for trabajo in trabajos_del_cambio:
            jugadores_asignados_ids.add(
                trabajo.jugador_1_id
            )

            if trabajo.jugador_2_id:
                jugadores_asignados_ids.add(
                    trabajo.jugador_2_id
                )

        jugadores_faltantes_ids = (
            jugadores_que_entrenaron_ids
            - jugadores_asignados_ids
        )

        if jugadores_faltantes_ids:
            jugadores_faltantes = (
                Jugador.objects
                .filter(id__in=jugadores_faltantes_ids)
                .order_by(
                    "apellido",
                    "nombre",
                )
            )

            errores.append(
                f"El cambio {numero_cambio} está incompleto. "
                f"Faltan: "
                + ", ".join(
                    str(jugador)
                    for jugador in jugadores_faltantes
                )
                + "."
            )

    # Revisar partidos sin sets
    partidos_sin_sets = (
        PartidoTurno.objects
        .filter(entrenamiento=entrenamiento)
        .annotate(cantidad_sets=Count("sets"))
        .filter(cantidad_sets=0)
        .select_related(
            "jugador_1",
            "jugador_2",
        )
    )

    for partido in partidos_sin_sets:
        errores.append(
            f"El partido {partido.jugador_1} vs "
            f"{partido.jugador_2} no tiene sets cargados."
        )

    if errores:
        for error in errores:
            messages.error(
                request,
                error,
            )

        messages.warning(
            request,
            "El turno no pudo finalizarse. Revisá los datos indicados.",
        )

        return redirect(
            "dia_turno",
            fecha_str=entrenamiento.fecha.isoformat(),
            turno=entrenamiento.turno,
        )

    entrenamiento.finalizado = True
    entrenamiento.finalizado_el = timezone.now()
    entrenamiento.finalizado_por = request.user

    if entrenamiento.entrenador is None:
        entrenamiento.entrenador = request.user

    entrenamiento.save(
        update_fields=[
            "finalizado",
            "finalizado_el",
            "finalizado_por",
            "entrenador",
        ]
    )

    messages.success(
        request,
        "Turno finalizado correctamente.",
    )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )


@login_required
@require_POST
def reabrir_turno(request, entrenamiento_id):
    entrenamiento = get_object_or_404(
        Entrenamiento,
        id=entrenamiento_id,
    )

    if not entrenamiento.finalizado:
        messages.info(
            request,
            "Este turno ya está abierto.",
        )

        return redirect(
            "dia_turno",
            fecha_str=entrenamiento.fecha.isoformat(),
            turno=entrenamiento.turno,
        )

    entrenamiento.finalizado = False
    entrenamiento.finalizado_el = None
    entrenamiento.finalizado_por = None

    entrenamiento.save(
        update_fields=[
            "finalizado",
            "finalizado_el",
            "finalizado_por",
        ]
    )

    messages.success(
        request,
        "El turno fue reabierto correctamente.",
    )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )

@login_required
@require_POST
def guardar_observacion_jugador(request, asistencia_id):
    asistencia = get_object_or_404(
        Asistencia.objects.select_related(
            "jugador",
            "entrenamiento",
        ),
        id=asistencia_id,
    )

    entrenamiento = asistencia.entrenamiento
    jugador = asistencia.jugador

    form = ObservacionJugadorForm(request.POST)

    if form.is_valid():
        observacion = form.save(commit=False)
        observacion.jugador = jugador
        observacion.entrenamiento = entrenamiento
        observacion.creada_por = request.user
        observacion.save()

        messages.success(
            request,
            f"Observación guardada para {jugador}.",
        )
    else:
        errores = []

        for lista_errores in form.errors.values():
            for error in lista_errores:
                errores.append(str(error))

        messages.error(
            request,
            (
                "No se pudo guardar la observación: "
                + " ".join(errores)
            ),
        )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )




@login_required
@require_POST
def agregar_jugador(request, entrenamiento_id):
    entrenamiento = get_object_or_404(Entrenamiento, id=entrenamiento_id)
    jugador_id = request.POST.get("jugador_id")

    if not jugador_id:
        messages.info(request, "Seleccioná un jugador para agregar al turno.")
        return redirect(
            "dia_turno",
            fecha_str=entrenamiento.fecha.strftime("%Y-%m-%d"),
            turno=entrenamiento.turno
        )

    jugador = get_object_or_404(Jugador, id=jugador_id, activo=True)

    asistencia, creado = Asistencia.objects.get_or_create(
        entrenamiento=entrenamiento,
        jugador=jugador,
        defaults={"estado": "pendiente"}
    )

    if creado:
        messages.success(
            request,
            f"{jugador} fue cargado correctamente al Turno {entrenamiento.turno}."
        )
    else:
        messages.info(
            request,
            f"{jugador} ya está cargado en el Turno {entrenamiento.turno}."
        )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.strftime("%Y-%m-%d"),
        turno=entrenamiento.turno
    )


@login_required
@require_POST
def copiar_lista_ayer(request, entrenamiento_id):
    entrenamiento = get_object_or_404(Entrenamiento, id=entrenamiento_id)

    entrenamiento_anterior = (
        Entrenamiento.objects
        .filter(
            fecha__lt=entrenamiento.fecha,
            turno=entrenamiento.turno,
            asistencias__isnull=False
        )
        .annotate(total_jugadores=Count("asistencias"))
        .filter(total_jugadores__gt=0)
        .order_by("-fecha")
        .first()
    )

    if not entrenamiento_anterior:
        messages.info(request, "No se encontró una lista anterior para copiar.")
        return redirect("dia_turno", fecha_str=entrenamiento.fecha.strftime("%Y-%m-%d"), turno=entrenamiento.turno)

    asistencias_anteriores = Asistencia.objects.filter(
        entrenamiento=entrenamiento_anterior
    ).select_related("jugador")

    jugadores_copiados = 0

    for asistencia_anterior in asistencias_anteriores:
        _, creado = Asistencia.objects.get_or_create(
            entrenamiento=entrenamiento,
            jugador=asistencia_anterior.jugador,
            defaults={"estado": "pendiente"}
        )

        if creado:
            jugadores_copiados += 1

    if jugadores_copiados > 0:
        messages.success(
            request,
            f"Lista anterior copiada correctamente. Se agregaron {jugadores_copiados} jugador/es."
        )
    else:
        messages.info(
            request,
            "La lista anterior ya estaba cargada en este turno."
        )

    return redirect("dia_turno", fecha_str=entrenamiento.fecha.strftime("%Y-%m-%d"), turno=entrenamiento.turno)


@login_required
@require_POST
def marcar_todos_asistieron(request, entrenamiento_id):
    entrenamiento = get_object_or_404(Entrenamiento, id=entrenamiento_id)
    asignar_entrenador_si_vacio(entrenamiento, request.user)

    Asistencia.objects.filter(entrenamiento=entrenamiento).update(estado="asistio")

    messages.success(request, "Todos los jugadores quedaron como asistieron.")
    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )


@login_required
@require_POST
def quitar_jugador(request, asistencia_id):
    asistencia = get_object_or_404(
        Asistencia,
        id=asistencia_id,
    )

    entrenamiento = asistencia.entrenamiento
    jugador = asistencia.jugador

    asignar_entrenador_si_vacio(
        entrenamiento,
        request.user,
    )

    trabajos_eliminados, _ = (
        TrabajoTurno.objects
        .filter(entrenamiento=entrenamiento)
        .filter(
            Q(jugador_1=jugador)
            | Q(jugador_2=jugador)
        )
        .delete()
    )

    asistencia.delete()

    if trabajos_eliminados > 0:
        messages.success(
            request,
            (
                f"{jugador} fue quitado del turno y también se eliminaron "
                f"sus trabajos o parejas cargadas."
            ),
        )
    else:
        messages.success(
            request,
            f"{jugador} fue quitado del turno.",
        )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )


@login_required
@require_POST
def cambiar_estado(request, asistencia_id):
    asistencia = get_object_or_404(Asistencia, id=asistencia_id)
    asignar_entrenador_si_vacio(asistencia.entrenamiento, request.user)

    estado_nuevo = request.POST.get("estado")
    estados_validos = {"asistio", "ausente", "tarde"}

    if asistencia.estado == estado_nuevo:
      asistencia.estado = "pendiente"
    else:
      asistencia.estado = estado_nuevo

    if asistencia.estado != "ausente":
      asistencia.motivo_ausencia = ""
    asistencia.detalle_ausencia = ""

    asistencia.save()

    return JsonResponse({
        "ok": True,
        "estado": asistencia.estado,
    })
    
@login_required
@require_POST
def guardar_motivo_ausencia(request, asistencia_id):
    asistencia = get_object_or_404(
        Asistencia.objects.select_related(
            "jugador",
            "entrenamiento",
        ),
        id=asistencia_id,
    )

    form = MotivoAusenciaForm(
        request.POST,
        instance=asistencia,
    )

    if asistencia.estado != "ausente":
        messages.error(
            request,
            "Solo podés cargar un motivo cuando el jugador está ausente.",
        )
    elif form.is_valid():
        form.save()

        messages.success(
            request,
            f"Motivo de ausencia guardado para {asistencia.jugador}.",
        )
    else:
        errores = []

        for lista_errores in form.errors.values():
            for error in lista_errores:
                errores.append(str(error))

        messages.error(
            request,
            "No se pudo guardar el motivo: " + " ".join(errores),
        )

    return redirect(
        "dia_turno",
        fecha_str=asistencia.entrenamiento.fecha.isoformat(),
        turno=asistencia.entrenamiento.turno,
    )


@login_required
def lista_jugadores(request):
    jugadores = Jugador.objects.all()
    return render(request, "asistencia/lista_jugadores.html", {"jugadores": jugadores})


@login_required
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
        "titulo": "Agregar jugador",
    })


@login_required
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
        "titulo": "Editar jugador",
    })


@login_required
def lista_ejercicios(request):
    ejercicios = Ejercicio.objects.all()
    return render(request, "asistencia/lista_ejercicios.html", {"ejercicios": ejercicios})


@login_required
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
        "titulo": "Agregar ejercicio",
    })


@login_required
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
        "titulo": "Editar ejercicio",
    })


@login_required
def cargar_ejercicios(request):
    jugadores = Jugador.objects.filter(activo=True).order_by("apellido", "nombre")

    jugador_id = request.GET.get("jugador")
    fecha_str = request.GET.get("fecha")
    turno_str = request.GET.get("turno")

    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    else:
        fecha = timezone.localdate()

    turno = None
    if turno_str:
        try:
            turno_int = int(turno_str)
            if turno_int in [1, 2, 3]:
                turno = turno_int
        except ValueError:
            turno = None

    jugador_seleccionado = None
    ejercicios_guardados = []

    ejercicios_por_categoria = {
        "Movilidad": Ejercicio.objects.filter(
            categoria=Ejercicio.Categoria.MOVILIDAD,
            activo=True,
        ),
        "Reacción": Ejercicio.objects.filter(
            categoria=Ejercicio.Categoria.REACCION,
            activo=True,
        ),
        "Saque": Ejercicio.objects.filter(
            categoria=Ejercicio.Categoria.SAQUE,
            activo=True,
        ),
        "Recepción": Ejercicio.objects.filter(
            categoria=Ejercicio.Categoria.RECEPCION,
            activo=True,
        ),
    }

    if jugador_id:
        jugador_seleccionado = Jugador.objects.filter(id=jugador_id, activo=True).first()
        if jugador_seleccionado:
            ejercicios_guardados = list(
                EjercicioRealizado.objects.filter(
                    jugador=jugador_seleccionado,
                    fecha=fecha,
                ).values_list("ejercicio_id", flat=True)
            )

    contexto = {
        "jugadores": jugadores,
        "jugador_seleccionado": jugador_seleccionado,
        "fecha": fecha,
        "hoy": timezone.localdate(),
        "turno": turno,
        "ejercicios_por_categoria": ejercicios_por_categoria,
        "ejercicios_guardados": ejercicios_guardados,
    }
    return render(request, "asistencia/cargar_ejercicios.html", contexto)


@login_required
@require_POST
def guardar_ejercicios(request):
    jugador_id = request.POST.get("jugador_id")
    fecha_str = request.POST.get("fecha")
    turno_str = request.POST.get("turno")
    ejercicio_ids = request.POST.getlist("ejercicios")

    jugador = get_object_or_404(Jugador, id=jugador_id, activo=True)

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        fecha = timezone.localdate()

    turno = None
    if turno_str:
        try:
            turno_int = int(turno_str)
            if turno_int in [1, 2, 3]:
                turno = turno_int
        except ValueError:
            turno = None

    EjercicioRealizado.objects.filter(
        jugador=jugador,
        fecha=fecha,
    ).delete()

    for ejercicio_id in ejercicio_ids:
        ejercicio = Ejercicio.objects.filter(id=ejercicio_id, activo=True).first()
        if ejercicio:
            EjercicioRealizado.objects.get_or_create(
                jugador=jugador,
                fecha=fecha,
                ejercicio=ejercicio,
            )

    messages.success(request, f"Ejercicios guardados para {jugador}.")

    url = f"/ejercicios/cargar/?jugador={jugador.id}&fecha={fecha.isoformat()}"
    if turno:
        url += f"&turno={turno}"

    return redirect(url)


@login_required
def seguimiento_semanal(request):
    jugadores = Jugador.objects.filter(
        activo=True
    ).order_by(
        "apellido",
        "nombre",
    )

    jugador_id = request.GET.get("jugador")
    fecha_str = request.GET.get("fecha")

    if fecha_str:
        try:
            fecha_base = datetime.strptime(
                fecha_str,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            fecha_base = timezone.localdate()
    else:
        fecha_base = timezone.localdate()

    inicio_semana = fecha_base - timedelta(
        days=fecha_base.weekday()
    )

    fin_semana = inicio_semana + timedelta(days=4)

    dias_semana = [
        inicio_semana + timedelta(days=i)
        for i in range(5)
    ]

    semana_anterior = inicio_semana - timedelta(days=7)
    semana_siguiente = inicio_semana + timedelta(days=7)

    jugador_seleccionado = None
    filas = []
    resumen = None

    if jugador_id:
        jugador_seleccionado = Jugador.objects.filter(
            id=jugador_id,
            activo=True,
        ).first()

        if jugador_seleccionado:
            total_dias_programados = 0
            total_presentes = 0
            total_tardes = 0
            total_ausencias = 0
            total_ejercicios = 0
            total_trabajos = 0
            total_partidos = 0
            total_partidos_ganados = 0
            total_partidos_perdidos = 0

            for dia in dias_semana:
                asistencias_dia = (
                    Asistencia.objects
                    .filter(
                        jugador=jugador_seleccionado,
                        entrenamiento__fecha=dia,
                    )
                    .select_related("entrenamiento")
                )

                turnos = list(
                    asistencias_dia.values_list(
                        "entrenamiento__turno",
                        flat=True,
                    )
                )

                estados = list(
                    asistencias_dia.values_list(
                        "estado",
                        flat=True,
                    )
                )

                if asistencias_dia.exists():
                    total_dias_programados += 1

                ejercicios_qs = (
                    EjercicioRealizado.objects
                    .filter(
                        jugador=jugador_seleccionado,
                        fecha=dia,
                    )
                    .select_related("ejercicio")
                    .order_by(
                        "ejercicio__categoria",
                        "ejercicio__nombre",
                    )
                )

                ejercicios_por_categoria = {}

                for item in ejercicios_qs:
                    categoria = (
                        item.ejercicio.get_categoria_display()
                    )

                    ejercicios_por_categoria.setdefault(
                        categoria,
                        [],
                    ).append(
                        item.ejercicio.nombre
                    )

                cantidad_ejercicios = ejercicios_qs.count()
                total_ejercicios += cantidad_ejercicios

                trabajos_qs = (
                    TrabajoTurno.objects
                    .filter(
                        entrenamiento__fecha=dia,
                    )
                    .filter(
                        Q(jugador_1=jugador_seleccionado)
                        | Q(jugador_2=jugador_seleccionado)
                    )
                    .select_related(
                        "entrenamiento",
                        "jugador_1",
                        "jugador_2",
                    )
                    .order_by(
                        "entrenamiento__turno",
                        "cambio",
                        "id",
                    )
                )

                trabajos_dia = []

                for trabajo in trabajos_qs:
                    if trabajo.tipo == TrabajoTurno.Tipo.PAREJA:
                        if (
                            trabajo.jugador_1_id
                            == jugador_seleccionado.id
                        ):
                            companero = trabajo.jugador_2
                        else:
                            companero = trabajo.jugador_1

                        descripcion = f"Con {companero}"
                    else:
                        descripcion = trabajo.get_tipo_display()

                    trabajos_dia.append({
                        "turno": trabajo.entrenamiento.turno,
                        "cambio": trabajo.cambio,
                        "tipo": trabajo.tipo,
                        "tipo_texto": trabajo.get_tipo_display(),
                        "descripcion": descripcion,
                        "detalle": trabajo.detalle,
                    })

                cantidad_trabajos = len(trabajos_dia)
                total_trabajos += cantidad_trabajos

                partidos_qs = (
                    PartidoTurno.objects
                    .filter(
                        entrenamiento__fecha=dia,
                    )
                    .filter(
                        Q(jugador_1=jugador_seleccionado)
                        | Q(jugador_2=jugador_seleccionado)
                    )
                    .select_related(
                        "entrenamiento",
                        "jugador_1",
                        "jugador_2",
                    )
                    .prefetch_related("sets")
                    .order_by(
                        "entrenamiento__turno",
                        "id",
                    )
                )

                partidos_dia = []

                for partido in partidos_qs:
                    if (
                        partido.jugador_1_id
                        == jugador_seleccionado.id
                    ):
                        rival = partido.jugador_2

                        sets_propios = (
                            partido.sets_jugador_1
                        )

                        sets_rival = (
                            partido.sets_jugador_2
                        )

                        sets_resultados = [
                            (
                                f"{set_partido.puntos_jugador_1}-"
                                f"{set_partido.puntos_jugador_2}"
                            )
                            for set_partido
                            in partido.sets.all()
                        ]

                    else:
                        rival = partido.jugador_1

                        sets_propios = (
                            partido.sets_jugador_2
                        )

                        sets_rival = (
                            partido.sets_jugador_1
                        )

                        sets_resultados = [
                            (
                                f"{set_partido.puntos_jugador_2}-"
                                f"{set_partido.puntos_jugador_1}"
                            )
                            for set_partido
                            in partido.sets.all()
                        ]

                    if partido.ganador == jugador_seleccionado:
                        resultado_clase = "success"
                        resultado_texto = "Victoria"
                        total_partidos_ganados += 1

                    elif partido.ganador:
                        resultado_clase = "danger"
                        resultado_texto = "Derrota"
                        total_partidos_perdidos += 1

                    else:
                        resultado_clase = "secondary"
                        resultado_texto = "Sin definir"

                    partidos_dia.append({
                        "turno": partido.entrenamiento.turno,
                        "rival": rival,
                        "resultado": (
                            f"{sets_propios}-{sets_rival}"
                        ),
                        "resultado_clase": resultado_clase,
                        "resultado_texto": resultado_texto,
                        "sets": sets_resultados,
                        "detalle": partido.detalle,
                    })

                cantidad_partidos = len(partidos_dia)
                total_partidos += cantidad_partidos

                if "asistio" in estados:
                    asistencia_texto = "Asistió"
                    asistencia_clase = "success"
                    total_presentes += 1

                elif "tarde" in estados:
                    asistencia_texto = "Tarde"
                    asistencia_clase = "warning text-dark"
                    total_presentes += 1
                    total_tardes += 1

                elif "ausente" in estados:
                    asistencia_texto = "Ausente"
                    asistencia_clase = "danger"
                    total_ausencias += 1

                elif asistencias_dia.exists():
                    asistencia_texto = "Sin marcar"
                    asistencia_clase = "secondary"

                elif (
                    cantidad_ejercicios > 0
                    or cantidad_trabajos > 0
                    or cantidad_partidos > 0
                ):
                    asistencia_texto = "Sin asistencia"
                    asistencia_clase = "secondary"

                else:
                    asistencia_texto = "Sin actividad"
                    asistencia_clase = "light text-dark"

                filas.append({
                    "dia": dia,
                    "asistencia_texto": asistencia_texto,
                    "asistencia_clase": asistencia_clase,
                    "turnos": (
                        ", ".join(
                            str(turno_item)
                            for turno_item
                            in sorted(set(turnos))
                        )
                        if turnos
                        else "-"
                    ),
                    "ejercicios_por_categoria": (
                        ejercicios_por_categoria
                    ),
                    "cantidad_ejercicios": (
                        cantidad_ejercicios
                    ),
                    "trabajos_dia": trabajos_dia,
                    "cantidad_trabajos": cantidad_trabajos,
                    "partidos_dia": partidos_dia,
                    "cantidad_partidos": cantidad_partidos,
                })

            porcentaje = (
                round(
                    (
                        total_presentes
                        / total_dias_programados
                    ) * 100,
                    1,
                )
                if total_dias_programados
                else 0
            )

            resumen = {
                "total_dias_programados": (
                    total_dias_programados
                ),
                "total_presentes": total_presentes,
                "total_tardes": total_tardes,
                "total_ausencias": total_ausencias,
                "total_ejercicios": total_ejercicios,
                "total_trabajos": total_trabajos,
                "total_partidos": total_partidos,
                "total_partidos_ganados": (
                    total_partidos_ganados
                ),
                "total_partidos_perdidos": (
                    total_partidos_perdidos
                ),
                "porcentaje": porcentaje,
            }

    contexto = {
        "jugadores": jugadores,
        "jugador_seleccionado": jugador_seleccionado,
        "fecha_base": fecha_base,
        "inicio_semana": inicio_semana,
        "fin_semana": fin_semana,
        "semana_anterior": semana_anterior,
        "semana_siguiente": semana_siguiente,
        "filas": filas,
        "resumen": resumen,
    }

    return render(
        request,
        "asistencia/seguimiento_semanal.html",
        contexto,
    )
    

@login_required
def historial_jugador(request, jugador_id):
    jugador = get_object_or_404(
        Jugador,
        id=jugador_id,
    )

    fecha_desde_str = request.GET.get("desde")
    fecha_hasta_str = request.GET.get("hasta")

    hoy = timezone.localdate()

    fecha_desde = hoy - timedelta(days=30)
    fecha_hasta = hoy

    if fecha_desde_str:
        try:
            fecha_desde = datetime.strptime(
                fecha_desde_str,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            pass

    if fecha_hasta_str:
        try:
            fecha_hasta = datetime.strptime(
                fecha_hasta_str,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            pass

    if fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    asistencias = (
        Asistencia.objects
        .filter(
            jugador=jugador,
            entrenamiento__fecha__range=[
                fecha_desde,
                fecha_hasta,
            ],
        )
        .select_related(
            "entrenamiento",
            "entrenamiento__entrenador",
        )
        .order_by(
            "-entrenamiento__fecha",
            "entrenamiento__turno",
        )
    )

    ejercicios = (
        EjercicioRealizado.objects
        .filter(
            jugador=jugador,
            fecha__range=[
                fecha_desde,
                fecha_hasta,
            ],
        )
        .select_related("ejercicio")
        .order_by(
            "-fecha",
            "ejercicio__categoria",
            "ejercicio__nombre",
        )
    )

    trabajos = (
        TrabajoTurno.objects
        .filter(
            entrenamiento__fecha__range=[
                fecha_desde,
                fecha_hasta,
            ],
        )
        .filter(
            Q(jugador_1=jugador)
            | Q(jugador_2=jugador)
        )
        .select_related(
            "entrenamiento",
            "jugador_1",
            "jugador_2",
        )
        .order_by(
            "-entrenamiento__fecha",
            "entrenamiento__turno",
            "cambio",
        )
    )

    observaciones = (
        ObservacionJugador.objects
        .filter(
            jugador=jugador,
            entrenamiento__fecha__range=[
                fecha_desde,
                fecha_hasta,
            ],
        )
        .select_related(
            "entrenamiento",
            "creada_por",
        )
        .order_by("-creada_el")
    )

    partidos = (
        PartidoTurno.objects
        .filter(
            entrenamiento__fecha__range=[
                fecha_desde,
                fecha_hasta,
            ],
        )
        .filter(
            Q(jugador_1=jugador)
            | Q(jugador_2=jugador)
        )
        .select_related(
            "entrenamiento",
            "jugador_1",
            "jugador_2",
        )
        .prefetch_related("sets")
        .order_by(
            "-entrenamiento__fecha",
            "entrenamiento__turno",
        )
    )

    total_partidos = partidos.count()

    total_partidos_ganados = sum(
        1
        for partido in partidos
        if partido.ganador == jugador
    )

    total_partidos_perdidos = sum(
        1
        for partido in partidos
        if partido.ganador
        and partido.ganador != jugador
    )

    total_asistencias = asistencias.count()

    total_presentes = asistencias.filter(
        Q(estado="asistio")
        | Q(estado="tarde")
    ).count()

    total_tardes = asistencias.filter(
        estado="tarde"
    ).count()

    total_ausencias = asistencias.filter(
        estado="ausente"
    ).count()

    porcentaje_asistencia = (
        round(
            (
                total_presentes
                / total_asistencias
            ) * 100,
            1,
        )
        if total_asistencias
        else 0
    )

    contexto = {
        "jugador": jugador,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,

        "asistencias": asistencias,
        "ejercicios": ejercicios,
        "trabajos": trabajos,
        "observaciones": observaciones,
        "partidos": partidos,

        "total_asistencias": total_asistencias,
        "total_presentes": total_presentes,
        "total_tardes": total_tardes,
        "total_ausencias": total_ausencias,
        "porcentaje_asistencia": porcentaje_asistencia,

        "total_partidos": total_partidos,
        "total_partidos_ganados": total_partidos_ganados,
        "total_partidos_perdidos": total_partidos_perdidos,
    }

    return render(
        request,
        "asistencia/historial_jugador.html",
        contexto,
    )


@login_required
def reportes(request):
    hoy = timezone.localdate()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    datos = []

    for jugador in Jugador.objects.filter(activo=True):
        asistencias_semana = Asistencia.objects.filter(
            jugador=jugador,
            entrenamiento__fecha__range=[
                inicio_semana,
                hoy,
            ],
        )

        asistencias_mes = Asistencia.objects.filter(
            jugador=jugador,
            entrenamiento__fecha__range=[
                inicio_mes,
                hoy,
            ],
        )

        # Datos semanales
        semana_total = asistencias_semana.count()

        semana_presentes = asistencias_semana.filter(
            Q(estado="asistio")
            | Q(estado="tarde")
        ).count()

        semana_ausentes = asistencias_semana.filter(
            estado="ausente"
        ).count()

        semana_porcentaje = (
            round(
                (
                    semana_presentes
                    / semana_total
                ) * 100,
                1,
            )
            if semana_total
            else 0
        )

        # Datos mensuales
        mes_total = asistencias_mes.count()

        mes_presentes = asistencias_mes.filter(
            Q(estado="asistio")
            | Q(estado="tarde")
        ).count()

        ausencias_mes = asistencias_mes.filter(
            estado="ausente"
        )

        mes_ausentes = ausencias_mes.count()

        mes_ausencias_justificadas = (
            ausencias_mes
            .exclude(motivo_ausencia="")
            .exclude(motivo_ausencia="sin_aviso")
            .count()
        )

        mes_ausencias_sin_aviso = ausencias_mes.filter(
            Q(motivo_ausencia="sin_aviso")
            | Q(motivo_ausencia="")
        ).count()

        motivo_mas_frecuente = (
            ausencias_mes
            .exclude(motivo_ausencia="")
            .values("motivo_ausencia")
            .annotate(total=Count("id"))
            .order_by("-total")
            .first()
        )

        if motivo_mas_frecuente:
            motivo_codigo = motivo_mas_frecuente[
                "motivo_ausencia"
            ]

            motivo_mas_frecuente_texto = dict(
                Asistencia.MotivoAusencia.choices
            ).get(
                motivo_codigo,
                motivo_codigo,
            )
        else:
            motivo_mas_frecuente_texto = "-"

        mes_porcentaje = (
            round(
                (
                    mes_presentes
                    / mes_total
                ) * 100,
                1,
            )
            if mes_total
            else 0
        )

        if mes_porcentaje >= 80:
            estado_clase = "success"
            estado_texto = "Buena asistencia"

        elif mes_porcentaje >= 50:
            estado_clase = "warning"
            estado_texto = "Asistencia media"

        else:
            estado_clase = "danger"
            estado_texto = "Baja asistencia"

        datos.append({
            "jugador": jugador,

            "semana_total": semana_total,
            "semana_presentes": semana_presentes,
            "semana_ausentes": semana_ausentes,
            "semana_porcentaje": semana_porcentaje,
            "mes_ausencias_justificadas": mes_ausencias_justificadas,
            "mes_ausencias_sin_aviso": mes_ausencias_sin_aviso,
            "motivo_mas_frecuente": motivo_mas_frecuente_texto,

            "mes_total": mes_total,
            "mes_presentes": mes_presentes,
            "mes_ausentes": mes_ausentes,
            "mes_porcentaje": mes_porcentaje,

            "mes_ausencias_justificadas": (
                mes_ausencias_justificadas
            ),
            "mes_ausencias_sin_aviso": (
                mes_ausencias_sin_aviso
            ),
            "motivo_mas_frecuente": (
                motivo_mas_frecuente_texto
            ),

            "estado_clase": estado_clase,
            "estado_texto": estado_texto,
        })

    return render(
        request,
        "asistencia/reportes.html",
        {
            "datos": datos,
            "hoy": hoy,
            "inicio_semana": inicio_semana,
            "inicio_mes": inicio_mes,
        },
    )


@login_required
def acerca(request):
    return render(request, "asistencia/acerca.html")

@login_required
def perfil(request):
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("perfil")
    else:
        form = PerfilForm(instance=request.user)

    return render(request, "asistencia/perfil.html", {
        "form": form,
    })
    
@login_required
@require_POST
def eliminar_observacion_jugador(request, observacion_id):
    observacion = get_object_or_404(
        ObservacionJugador,
        id=observacion_id,
    )

    entrenamiento = observacion.entrenamiento
    jugador = observacion.jugador

    observacion.delete()

    messages.success(
        request,
        f"Observación eliminada de {jugador}.",
    )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )
    
@login_required
def editar_observacion_jugador(request, observacion_id):
    observacion = get_object_or_404(
        ObservacionJugador,
        id=observacion_id,
    )

    entrenamiento = observacion.entrenamiento

    if request.method == "POST":
        form = ObservacionJugadorForm(
            request.POST,
            instance=observacion,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Observación actualizada correctamente.",
            )

            return redirect(
                "dia_turno",
                fecha_str=entrenamiento.fecha.isoformat(),
                turno=entrenamiento.turno,
            )
    else:
        form = ObservacionJugadorForm(
            instance=observacion,
        )

    return render(
        request,
        "asistencia/editar_observacion_jugador.html",
        {
            "form": form,
            "observacion": observacion,
            "entrenamiento": entrenamiento,
        },
    )
    
@login_required
def editar_partido_turno(request, partido_id):
    partido = get_object_or_404(
        PartidoTurno.objects.select_related("entrenamiento"),
        id=partido_id,
    )

    entrenamiento = partido.entrenamiento

    if request.method == "POST":
        partido_form = PartidoTurnoForm(
            request.POST,
            instance=partido,
            entrenamiento=entrenamiento,
        )

        sets_formset = SetPartidoFormSet(
            request.POST,
            instance=partido,
            prefix="sets",
        )

        if partido_form.is_valid() and sets_formset.is_valid():
            with transaction.atomic():
                partido = partido_form.save()
                sets = sets_formset.save(commit=False)

                numero_set = 1

                for set_partido in sets:
                    set_partido.partido = partido
                    set_partido.numero = numero_set
                    set_partido.save()
                    numero_set += 1

                for set_eliminado in sets_formset.deleted_objects:
                    set_eliminado.delete()

            messages.success(
                request,
                "El partido se actualizó correctamente.",
            )

            return redirect(
                "dia_turno",
                fecha_str=entrenamiento.fecha.isoformat(),
                turno=entrenamiento.turno,
            )

    else:
        partido_form = PartidoTurnoForm(
            instance=partido,
            entrenamiento=entrenamiento,
        )

        sets_formset = SetPartidoFormSet(
            instance=partido,
            prefix="sets",
        )

    return render(
        request,
        "asistencia/editar_partido_turno.html",
        {
            "partido": partido,
            "entrenamiento": entrenamiento,
            "partido_form": partido_form,
            "sets_formset": sets_formset,
        },
    )


@login_required
@require_POST
def eliminar_partido_turno(request, partido_id):
    partido = get_object_or_404(
        PartidoTurno.objects.select_related("entrenamiento"),
        id=partido_id,
    )

    entrenamiento = partido.entrenamiento

    partido.delete()

    messages.success(
        request,
        "El partido se eliminó correctamente.",
    )

    return redirect(
        "dia_turno",
        fecha_str=entrenamiento.fecha.isoformat(),
        turno=entrenamiento.turno,
    )