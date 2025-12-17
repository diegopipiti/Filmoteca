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
            "public_rating",
            "public_votes",
            "stato",
            "note",
        ]
        widgets = {
            "visto": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
