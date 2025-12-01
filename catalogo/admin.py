from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("titolo", "anno", "genere", "regista", "visto", "voto")
    list_filter = (
        "genere",
        "regista",
        "visto",
        "codifica",
        "estensione",
        "anno",
        "voto",
    )
    search_fields = ("titolo", "regista", "genere", "percorso")
