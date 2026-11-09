from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Animal, EventoAnimal, Finca, Propietario, ReporteNovedad

User = get_user_model()

MAX_FOTO_MB = 5


class RegistroForm(UserCreationForm):
    """Registro de un productor nuevo (RF01)."""

    first_name = forms.CharField(label="Nombre completo", max_length=100)
    email = forms.EmailField(label="Correo electrónico")

    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")
        labels = {"username": "Usuario"}

    def clean_email(self):
        correo = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=correo).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        return correo


class PropietarioForm(forms.ModelForm):
    class Meta:
        model = Propietario
        fields = ["nombre", "contacto", "autoriza_datos"]
        help_texts = {
            "autoriza_datos": "Marque esta casilla solo si la persona aceptó que se guarden sus datos "
            "para este sistema (Ley 1581 de 2012).",
        }

    def clean_autoriza_datos(self):
        if not self.cleaned_data.get("autoriza_datos"):
            raise forms.ValidationError("Se necesita la autorización de la persona para guardar sus datos.")
        return True


class FincaForm(forms.ModelForm):
    class Meta:
        model = Finca
        fields = ["nombre", "vereda", "propietario", "area_hectareas"]

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Cada productor solo puede escoger sus propios propietarios.
        self.fields["propietario"].queryset = Propietario.objects.filter(usuario=usuario)


class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = [
            "finca", "codigo", "chapeta_oficial", "alias", "sexo", "raza",
            "fecha_nacimiento", "hierro", "senales_particulares", "foto",
        ]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "senales_particulares": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["finca"].queryset = Finca.objects.filter(usuario=usuario)
        self.fields["codigo"].error_messages["unique"] = "Ya hay un animal con ese código. Use otro."

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto and hasattr(foto, "size") and foto.size > MAX_FOTO_MB * 1024 * 1024:
            raise forms.ValidationError(f"La foto no debe pasar de {MAX_FOTO_MB} MB.")
        return foto


class EventoForm(forms.ModelForm):
    class Meta:
        model = EventoAnimal
        fields = ["tipo", "fecha", "observacion"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class EstadoForm(forms.Form):
    estado = forms.ChoiceField(choices=Animal.ESTADOS, label="Nuevo estado")
    observacion = forms.CharField(label="Observación", max_length=255, required=False)


class ReporteForm(forms.ModelForm):
    animales = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Animales afectados",
        error_messages={"required": "Escoja al menos un animal."},
    )

    class Meta:
        model = ReporteNovedad
        fields = ["tipo", "fecha", "lugar", "descripcion", "animales"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo animales activos de las fincas del usuario.
        self.fields["animales"].queryset = Animal.objects.filter(
            finca__usuario=usuario, estado="activo"
        ).select_related("finca")
