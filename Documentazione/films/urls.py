from django.urls import path

from .views import FilmListView

urlpatterns = [
    path('', FilmListView.as_view(), name='film-list'),
]
