from django import forms
from .models import Movie


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = [
            "titolo",
            "anno",
            "genere",
            "regista",
            "trama",
            "visto",
            "dimensione_file_mb",
            "codifica",
            "estensione",
            "percorso",
            "locandina_url",
            "voto",
            "recensione",
            "ultima_visione",
        ]
        widgets = {
            "visto": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
