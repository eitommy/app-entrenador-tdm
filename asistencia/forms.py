from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import inlineformset_factory

from .models import (
    Jugador,
    Ejercicio,
    Entrenamiento,
    Entrenador,
    TrabajoTurno,
    Asistencia,
    ObservacionJugador,
    PartidoTurno,
    SetPartido,
)
class RegistroEntrenadorForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombre",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Nombre",
            "autocomplete": "off",
        })
    )

    last_name = forms.CharField(
        label="Apellido",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Apellido",
            "autocomplete": "off",
        })
    )

    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email",
            "autocomplete": "off",
        })
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Usuario",
            "autocomplete": "off",
        })

        self.fields["password1"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Contraseña",
            "autocomplete": "new-password",
        })

        self.fields["password2"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Repetir contraseña",
            "autocomplete": "new-password",
        })


class PerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Email",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre",
                "autocomplete": "off",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Apellido",
                "autocomplete": "off",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email",
                "autocomplete": "off",
            }),
        }


class JugadorForm(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ["nombre", "apellido", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre del jugador",
                "autocomplete": "off",
            }),
            "apellido": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Apellido del jugador",
                "autocomplete": "off",
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }


class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = ["categoria", "nombre", "activo"]
        widgets = {
            "categoria": forms.Select(attrs={
                "class": "form-select",
                "autocomplete": "off",
            }),
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre del ejercicio",
                "autocomplete": "off",
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }


class EntrenamientoInfoForm(forms.ModelForm):
    class Meta:
        model = Entrenamiento
        fields = [
            "entrenador_responsable",
            "observaciones",
        ]

        labels = {
            "entrenador_responsable": "Entrenador responsable",
            "observaciones": "Observaciones",
        }

        widgets = {
            "entrenador_responsable": forms.Select(attrs={
                "class": "form-select",
            }),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones del turno...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["entrenador_responsable"].required = False
        self.fields["entrenador_responsable"].queryset = (
            Entrenador.objects
            .filter(activo=True)
            .order_by("apellido", "nombre")
        )

        self.fields["entrenador_responsable"].empty_label = (
            "Seleccionar entrenador"
        )
        
    class EntrenadorForm(forms.ModelForm):
        class Meta:
            model = Entrenador
            fields = [
            "nombre",
            "apellido",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre",
                "autocomplete": "off",
            }),
            "apellido": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Apellido",
                "autocomplete": "off",
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()

        if not nombre:
            raise forms.ValidationError(
                "El nombre del entrenador es obligatorio."
            )

        return nombre

    def clean_apellido(self):
        return self.cleaned_data.get("apellido", "").strip()
    
class NoEntrenamientoForm(forms.ModelForm):
    class Meta:
        model = Entrenamiento
        fields = [
            "no_se_entreno",
            "motivo_no_entrenamiento",
            "detalle_no_entrenamiento",
        ]

        labels = {
            "no_se_entreno": "No se entrenó",
            "motivo_no_entrenamiento": "Motivo",
            "detalle_no_entrenamiento": "Detalle opcional",
        }

        widgets = {
            "no_se_entreno": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "motivo_no_entrenamiento": forms.Select(attrs={
                "class": "form-select",
            }),
            "detalle_no_entrenamiento": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: feriado nacional, torneo, club cerrado...",
                "autocomplete": "off",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        no_se_entreno = cleaned_data.get("no_se_entreno")
        motivo = cleaned_data.get("motivo_no_entrenamiento")

        if no_se_entreno and not motivo:
            self.add_error(
                "motivo_no_entrenamiento",
                "Seleccioná un motivo.",
            )

        return cleaned_data
        
class EntrenadorForm(forms.ModelForm):
    class Meta:
        model = Entrenador
        fields = [
            "nombre",
            "apellido",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre",
                "autocomplete": "off",
            }),
            "apellido": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Apellido",
                "autocomplete": "off",
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()

        if not nombre:
            raise forms.ValidationError(
                "El nombre del entrenador es obligatorio."
            )

        return nombre

    def clean_apellido(self):
        return self.cleaned_data.get("apellido", "").strip()

class TrabajoTurnoForm(forms.ModelForm):
    class Meta:
        model = TrabajoTurno
        fields = [
            "cambio",
            "tipo",
            "jugador_1",
            "jugador_2",
            "detalle",
        ]

        labels = {
            "cambio": "Cambio",
            "tipo": "Tipo de trabajo",
            "jugador_1": "Jugador",
            "jugador_2": "Compañero",
            "detalle": "Detalle opcional",
        }

        widgets = {
            "cambio": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "placeholder": "Ejemplo: 1",
            }),
            "tipo": forms.Select(attrs={
                "class": "form-select",
                "id": "id_tipo_trabajo",
            }),
            "jugador_1": forms.Select(attrs={
                "class": "form-select",
            }),
            "jugador_2": forms.Select(attrs={
                "class": "form-select",
                "id": "id_jugador_2",
            }),
            "detalle": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: saque y tercera pelota",
                "autocomplete": "off",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.entrenamiento = kwargs.pop("entrenamiento", None)

        super().__init__(*args, **kwargs)

        self.fields["jugador_2"].required = False
        self.fields["detalle"].required = False

        if not self.entrenamiento:
            return

        asistencias_turno = (
            Asistencia.objects
            .filter(entrenamiento=self.entrenamiento)
            .select_related("jugador")
        )

        jugadores_ids = asistencias_turno.values_list(
            "jugador_id",
            flat=True,
        )

        jugadores_del_turno = (
            Jugador.objects
            .filter(
                id__in=jugadores_ids,
                activo=True,
            )
            .order_by(
                "apellido",
                "nombre",
            )
        )

        self.fields["jugador_1"].queryset = jugadores_del_turno
        self.fields["jugador_2"].queryset = jugadores_del_turno

        if self.is_bound:
            return

        trabajos = TrabajoTurno.objects.filter(
            entrenamiento=self.entrenamiento
        )

        ultimo_cambio = (
            trabajos
            .order_by("-cambio")
            .values_list("cambio", flat=True)
            .first()
        )

        if ultimo_cambio is None:
            cambio_sugerido = 1
        else:
            trabajos_ultimo_cambio = trabajos.filter(
                cambio=ultimo_cambio
            )

            jugadores_asignados_ids = set()

            for trabajo in trabajos_ultimo_cambio:
                jugadores_asignados_ids.add(
                    trabajo.jugador_1_id
                )

                if trabajo.jugador_2_id:
                    jugadores_asignados_ids.add(
                        trabajo.jugador_2_id
                    )

            total_jugadores = asistencias_turno.count()
            total_asignados = len(jugadores_asignados_ids)

            ultimo_cambio_completo = (
                total_jugadores > 0
                and total_asignados == total_jugadores
            )

            if ultimo_cambio_completo:
                cambio_sugerido = ultimo_cambio + 1
            else:
                cambio_sugerido = ultimo_cambio

        self.fields["cambio"].initial = cambio_sugerido

    def clean(self):
        cleaned_data = super().clean()

        cambio = cleaned_data.get("cambio")
        tipo = cleaned_data.get("tipo")
        jugador_1 = cleaned_data.get("jugador_1")
        jugador_2 = cleaned_data.get("jugador_2")

        if not self.entrenamiento:
            return cleaned_data

        if not cambio or not jugador_1:
            return cleaned_data

        if tipo == TrabajoTurno.Tipo.PAREJA:
            if not jugador_2:
                self.add_error(
                    "jugador_2",
                    "Para una pareja tenés que seleccionar un compañero.",
                )
                return cleaned_data

            if jugador_1 == jugador_2:
                self.add_error(
                    "jugador_2",
                    "Un jugador no puede formar pareja consigo mismo.",
                )
                return cleaned_data
        else:
            jugador_2 = None
            cleaned_data["jugador_2"] = None

        trabajos_mismo_cambio = TrabajoTurno.objects.filter(
            entrenamiento=self.entrenamiento,
            cambio=cambio,
        )

        if self.instance and self.instance.pk:
            trabajos_mismo_cambio = trabajos_mismo_cambio.exclude(
                pk=self.instance.pk
            )

        jugador_1_ocupado = trabajos_mismo_cambio.filter(
            Q(jugador_1=jugador_1)
            | Q(jugador_2=jugador_1)
        ).exists()

        if jugador_1_ocupado:
            self.add_error(
                "jugador_1",
                f"{jugador_1} ya tiene una actividad cargada en el cambio {cambio}.",
            )

        if jugador_2:
            jugador_2_ocupado = trabajos_mismo_cambio.filter(
                Q(jugador_1=jugador_2)
                | Q(jugador_2=jugador_2)
            ).exists()

            if jugador_2_ocupado:
                self.add_error(
                    "jugador_2",
                    f"{jugador_2} ya tiene una actividad cargada en el cambio {cambio}.",
                )

        if (
            tipo == TrabajoTurno.Tipo.PAREJA
            and jugador_1
            and jugador_2
        ):
            parejas_existentes = TrabajoTurno.objects.filter(
                entrenamiento=self.entrenamiento,
                tipo=TrabajoTurno.Tipo.PAREJA,
            )

            if self.instance and self.instance.pk:
                parejas_existentes = parejas_existentes.exclude(
                    pk=self.instance.pk
                )

            pareja_duplicada = parejas_existentes.filter(
                (
                    Q(jugador_1=jugador_1)
                    & Q(jugador_2=jugador_2)
                )
                |
                (
                    Q(jugador_1=jugador_2)
                    & Q(jugador_2=jugador_1)
                )
            ).first()

            if pareja_duplicada:
                self.add_error(
                    "jugador_2",
                    (
                        f"La pareja {jugador_1} - {jugador_2} "
                        f"ya fue asignada en el cambio "
                        f"{pareja_duplicada.cambio}."
                    ),
                )

        return cleaned_data


class ObservacionJugadorForm(forms.ModelForm):
    class Meta:
        model = ObservacionJugador
        fields = [
            "texto",
        ]

        labels = {
            "texto": "Observación individual",
        }

        widgets = {
            "texto": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Ejemplo: mejorar recepción, trabajar desplazamiento "
                        "lateral o entrenó con molestias."
                    ),
                    "autocomplete": "off",
                }
            ),
        }

    def clean_texto(self):
        texto = self.cleaned_data.get("texto", "").strip()

        if not texto:
            raise forms.ValidationError(
                "Escribí una observación antes de guardarla."
            )

        if len(texto) < 3:
            raise forms.ValidationError(
                "La observación es demasiado corta."
            )

        return texto
    


class MotivoAusenciaForm(forms.ModelForm):
    class Meta:
        model = Asistencia
        fields = [
            "motivo_ausencia",
            "detalle_ausencia",
        ]

        labels = {
            "motivo_ausencia": "Motivo de ausencia",
            "detalle_ausencia": "Detalle opcional",
        }

        widgets = {
            "motivo_ausencia": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "detalle_ausencia": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ejemplo: reposo médico, viaje por torneo "
                        "o examen universitario."
                    ),
                    "autocomplete": "off",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        motivo = cleaned_data.get("motivo_ausencia")
        detalle = cleaned_data.get("detalle_ausencia", "").strip()

        if not motivo:
            self.add_error(
                "motivo_ausencia",
                "Seleccioná el motivo de la ausencia.",
            )

        if motivo == Asistencia.MotivoAusencia.OTRO and not detalle:
            self.add_error(
                "detalle_ausencia",
                "Explicá el motivo cuando seleccionás Otro.",
            )

        cleaned_data["detalle_ausencia"] = detalle

        return cleaned_data

class PartidoTurnoForm(forms.ModelForm):
    class Meta:
        model = PartidoTurno
        fields = [
            "jugador_1",
            "jugador_2",
            "detalle",
        ]

        labels = {
            "jugador_1": "Jugador 1",
            "jugador_2": "Jugador 2",
            "detalle": "Detalle opcional",
        }

        widgets = {
            "jugador_1": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "jugador_2": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "detalle": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: partido final del turno",
                }
            ),
        }

    def __init__(self, *args, entrenamiento=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.entrenamiento = entrenamiento

        jugadores_ids = []

        if entrenamiento:
            jugadores_ids = entrenamiento.asistencias.values_list(
                "jugador_id",
                flat=True,
            )

        jugadores = (
            Jugador.objects
            .filter(
                id__in=jugadores_ids,
                activo=True,
            )
            .order_by(
                "apellido",
                "nombre",
            )
        )

        self.fields["jugador_1"].queryset = jugadores
        self.fields["jugador_2"].queryset = jugadores

    def clean(self):
        cleaned_data = super().clean()

        jugador_1 = cleaned_data.get("jugador_1")
        jugador_2 = cleaned_data.get("jugador_2")

        if jugador_1 and jugador_2 and jugador_1 == jugador_2:
            raise forms.ValidationError(
                "Un jugador no puede jugar contra sí mismo."
            )

        return cleaned_data

class SetPartidoForm(forms.ModelForm):
    class Meta:
        model = SetPartido
        fields = [
            "puntos_jugador_1",
            "puntos_jugador_2",
        ]

        labels = {
            "puntos_jugador_1": "Puntos J1",
            "puntos_jugador_2": "Puntos J2",
        }

        widgets = {
            "puntos_jugador_1": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "puntos_jugador_2": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        puntos_1 = cleaned_data.get("puntos_jugador_1")
        puntos_2 = cleaned_data.get("puntos_jugador_2")

        if puntos_1 is None or puntos_2 is None:
            return cleaned_data

        if puntos_1 == puntos_2:
            raise forms.ValidationError(
                "Un set no puede terminar empatado."
            )

        ganador = max(puntos_1, puntos_2)
        perdedor = min(puntos_1, puntos_2)

        if ganador < 11:
            raise forms.ValidationError(
                "El ganador del set debe llegar al menos a 11 puntos."
            )

        if ganador - perdedor < 2:
            raise forms.ValidationError(
                "El set debe terminar con una diferencia mínima de 2 puntos."
            )

        return cleaned_data

SetPartidoFormSet = inlineformset_factory(
    PartidoTurno,
    SetPartido,
    form=SetPartidoForm,
    extra=5,
    can_delete=True,
    min_num=1,
    validate_min=True,
)