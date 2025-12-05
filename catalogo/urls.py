from django.urls import path
from . import views

urlpatterns = [
    path("generi/", views.movie_by_genre, name="movie_by_genre"),
    path("", views.movie_list, name="movie_list"),
    path("play/<int:pk>/", views.movie_play, name="movie_play"),
    path("movie/<int:pk>/", views.movie_detail, name="movie_detail"),
    path("movie/<int:pk>/edit/", views.movie_edit, name="movie_edit"),
    path("movie/<int:pk>/delete/", views.movie_delete, name="movie_delete"),
    path(
        "movie/<int:pk>/update_poster/",
        views.update_movie_poster,
        name="update_movie_poster",
    ),
    path("scan/", views.scan_folder, name="scan_folder"),
    path("update_posters/", views.update_posters, name="update_posters"),
]
