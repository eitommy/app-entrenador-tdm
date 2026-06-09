from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Jugador, Ejercicio, Entrenamiento


class RegistroEntrenadorForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=100)
    last_name = forms.CharField(label="Apellido", max_length=100)
    email = forms.EmailField(label="Email", required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "password1", "password2"]


class JugadorForm(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ["nombre", "apellido", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del jugador", "autocomplete": "off"}),
            "apellido": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido del jugador", "autocomplete": "off"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = ["categoria", "nombre", "activo"]
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-select", "autocomplete": "off"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del ejercicio", "autocomplete": "off"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class EntrenamientoInfoForm(forms.ModelForm):
    class Meta:
        model = Entrenamiento
        fields = ["observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones del turno..."
            }),
        }