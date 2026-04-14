from django import forms
from .models import Jugador, Ejercicio


class JugadorForm(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ["nombre", "apellido", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre del jugador",
                "autocomplete": "off"
            }),
            "apellido": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Apellido del jugador",
                "autocomplete": "off"
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }


class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = ["categoria", "nombre", "activo"]
        widgets = {
            "categoria": forms.Select(attrs={
                "class": "form-select",
                "autocomplete": "off"
            }),
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre del ejercicio",
                "autocomplete": "off"
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }