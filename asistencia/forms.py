from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Jugador, Ejercicio, Entrenamiento


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
        fields = ["observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones del turno...",
            }),
        }