from django.contrib import admin

from .models import Director, Film, Genre


@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'director', 'watched', 'rating')
    list_filter = ('watched', 'genres', 'year')
    search_fields = ('title', 'director__name')
    autocomplete_fields = ('director', 'genres')
    ordering = ('-created_at',)
