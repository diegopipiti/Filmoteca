from django.db import models


class Director(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Regista'
        verbose_name_plural = 'Registi'

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Genere'
        verbose_name_plural = 'Generi'

    def __str__(self):
        return self.name


class Film(models.Model):
    title = models.CharField(max_length=255)
    year = models.PositiveIntegerField(null=True, blank=True)
    director = models.ForeignKey(
        Director, on_delete=models.CASCADE, related_name='films', null=True, blank=True
    )
    genres = models.ManyToManyField(Genre, related_name='films')
    watched = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    poster_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Film'
        verbose_name_plural = 'Film'

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title
