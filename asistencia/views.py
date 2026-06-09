from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EjercicioForm, EntrenamientoInfoForm, JugadorForm, RegistroEntrenadorForm
from .models import Asistencia, Ejercicio, EjercicioRealizado, Entrenamiento, Jugador


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
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    turno = int(turno)

    entrenamiento = obtener_o_crear_entrenamiento(fecha, turno)

    asistencias = list(
        Asistencia.objects.filter(entrenamiento=entrenamiento)
        .select_related("jugador")
    )

    jugadores_disponibles = Jugador.objects.filter(activo=True).exclude(
        id__in=[asistencia.jugador_id for asistencia in asistencias]
    )

    jugadores_ids = [asistencia.jugador_id for asistencia in asistencias]

    ejercicios_por_jugador = (
        EjercicioRealizado.objects
        .filter(jugador_id__in=jugadores_ids, fecha=fecha)
        .values("jugador_id")
        .annotate(total=Count("id"))
    )

    ejercicios_contador = {
        item["jugador_id"]: item["total"]
        for item in ejercicios_por_jugador
    }

    for asistencia in asistencias:
        asistencia.ejercicios_cargados = ejercicios_contador.get(asistencia.jugador_id, 0)

    contexto = {
        "entrenamiento": entrenamiento,
        "entrenamiento_form": EntrenamientoInfoForm(instance=entrenamiento),
        "nombre_entrenador": nombre_entrenador(entrenamiento),
        "asistencias": asistencias,
        "jugadores_disponibles": jugadores_disponibles,
        "fecha": fecha,
        "turno": turno,
        "ayer": fecha - timedelta(days=1),
        "maniana": fecha + timedelta(days=1),
        "hoy": timezone.localdate(),
    }
    return render(request, "asistencia/dia_turno.html", contexto)


@login_required
@require_POST
def tomar_turno(request, entrenamiento_id):
    entrenamiento = get_object_or_404(Entrenamiento, id=entrenamiento_id)

    if entrenamiento.entrenador is None:
        entrenamiento.entrenador = request.user
        entrenamiento.save()
        messages.success(request, "Tomaste este turno correctamente.")
    elif entrenamiento.entrenador == request.user:
        messages.info(request, "Este turno ya está asignado a vos.")
    else:
        messages.warning(request, "Este turno ya fue tomado por otro entrenador.")

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
    asistencia = get_object_or_404(Asistencia, id=asistencia_id)
    entrenamiento = asistencia.entrenamiento
    asignar_entrenador_si_vacio(entrenamiento, request.user)

    asistencia.delete()
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
    jugadores = Jugador.objects.filter(activo=True).order_by("apellido", "nombre")

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
    fin_semana = inicio_semana + timedelta(days=4)
    dias_semana = [inicio_semana + timedelta(days=i) for i in range(5)]

    semana_anterior = inicio_semana - timedelta(days=7)
    semana_siguiente = inicio_semana + timedelta(days=7)

    jugador_seleccionado = None
    filas = []
    resumen = None

    if jugador_id:
        jugador_seleccionado = Jugador.objects.filter(id=jugador_id, activo=True).first()

        if jugador_seleccionado:
            total_dias_programados = 0
            total_presentes = 0
            total_tardes = 0
            total_ausencias = 0
            total_ejercicios = 0

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
                    asistencias_dia.values_list("entrenamiento__turno", flat=True)
                )

                estados = list(
                    asistencias_dia.values_list("estado", flat=True)
                )

                if asistencias_dia.exists():
                    total_dias_programados += 1

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
                else:
                    asistencia_texto = "Sin actividad"
                    asistencia_clase = "light text-dark"
                    

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
                    categoria = item.ejercicio.get_categoria_display()
                    ejercicios_por_categoria.setdefault(categoria, []).append(
                        item.ejercicio.nombre
                    )

                cantidad_ejercicios = ejercicios_qs.count()
                total_ejercicios += cantidad_ejercicios

                filas.append({
                    "dia": dia,
                    "asistencia_texto": asistencia_texto,
                    "asistencia_clase": asistencia_clase,
                    "turnos": ", ".join([str(t) for t in sorted(set(turnos))]) if turnos else "-",
                    "ejercicios_por_categoria": ejercicios_por_categoria,
                    "cantidad_ejercicios": cantidad_ejercicios,
                })

            porcentaje = round(
                (total_presentes / total_dias_programados) * 100,
                1,
            ) if total_dias_programados else 0

            resumen = {
                "total_dias_programados": total_dias_programados,
                "total_presentes": total_presentes,
                "total_tardes": total_tardes,
                "total_ausencias": total_ausencias,
                "total_ejercicios": total_ejercicios,
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

    return render(request, "asistencia/seguimiento_semanal.html", contexto)


@login_required
def reportes(request):
    hoy = timezone.localdate()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    datos = []

    for jugador in Jugador.objects.filter(activo=True):
        asistencias_semana = Asistencia.objects.filter(
            jugador=jugador,
            entrenamiento__fecha__range=[inicio_semana, hoy],
        )

        asistencias_mes = Asistencia.objects.filter(
            jugador=jugador,
            entrenamiento__fecha__range=[inicio_mes, hoy],
        )

        semana_total = asistencias_semana.count()
        semana_presentes = asistencias_semana.filter(
            Q(estado="asistio") | Q(estado="tarde")
        ).count()
        semana_ausentes = asistencias_semana.filter(estado="ausente").count()
        semana_porcentaje = round((semana_presentes / semana_total) * 100, 1) if semana_total else 0

        mes_total = asistencias_mes.count()
        mes_presentes = asistencias_mes.filter(
            Q(estado="asistio") | Q(estado="tarde")
        ).count()
        mes_ausentes = asistencias_mes.filter(estado="ausente").count()
        mes_porcentaje = round((mes_presentes / mes_total) * 100, 1) if mes_total else 0

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

            "mes_total": mes_total,
            "mes_presentes": mes_presentes,
            "mes_ausentes": mes_ausentes,
            "mes_porcentaje": mes_porcentaje,

            "estado_clase": estado_clase,
            "estado_texto": estado_texto,
        })

    return render(request, "asistencia/reportes.html", {
        "datos": datos,
        "hoy": hoy,
        "inicio_semana": inicio_semana,
        "inicio_mes": inicio_mes,
    })


@login_required
def acerca(request):
    return render(request, "asistencia/acerca.html")
