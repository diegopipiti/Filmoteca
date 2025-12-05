from django.db import models

# Create your models here.

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Movie(models.Model):
    titolo = models.CharField(max_length=200)
    anno = models.IntegerField(null=True, blank=True, verbose_name="Anno")
    genere = models.CharField(max_length=100, blank=True)
    regista = models.CharField(max_length=100, blank=True)
    trama = models.TextField("Trama", blank=True)
    trama = models.TextField("Trama", blank=True)
    visto = models.BooleanField(default=False)

    dimensione_file_mb = models.FloatField(
        null=True, blank=True, help_text="Dimensione in MB"
    )
    codifica = models.CharField(max_length=50, blank=True)  # es. x264, x265
    estensione = models.CharField(max_length=10, blank=True)  # es. .mkv, .mp4
    percorso = models.CharField(max_length=500)  # path completo sul disco

    locandina_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL dell'immagine della locandina (opzionale)",
    )

    voto = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], null=True, blank=True
    )

    recensione = models.TextField(blank=True, null=True, verbose_name="Recensione")
    ultima_visione = models.DateField(
        blank=True, null=True, verbose_name="Data ultima visione"
    )

    def __str__(self):
        return f"{self.titolo} ({self.anno})"
