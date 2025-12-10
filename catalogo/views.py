import os
import platform
import subprocess
from .forms import MovieForm
import re
import requests
from django.db.models import Q
import random
from typing import Optional, Tuple
import sys
from collections import defaultdict
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Movie
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .tmdb import fetch_movie_data_from_tmdb, apply_tmdb_data
from .utils import guess_title_and_year


VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".mpg", ".mpeg"]

# Regex per intercettare anni plausibili (1900–2039, puoi restringerla se vuoi)
YEAR_RE = re.compile(r"(19[0-9]{2}|20[0-3][0-9])")


# Sezione Helper------------------------------
def group_movies_by_genre(movies, max_per_genre: int = 24):
    """
    Restituisce una lista di sezioni già pronte per il template
    (comprese “Top rated” e “Continua a guardare” se presenti).
    """
    sezioni = []

    # Top rated (voto >= 8)
    top_rated = Movie.objects.filter(voto__gte=8).order_by("-voto", "-id")[
        :max_per_genre
    ]
    if top_rated:
        sezioni.append(
            {
                "titolo": "Film 4 stelle e oltre",
                "movies": top_rated,
                "special": True,
                "slug": "top-rated",
            }
        )

    # Continua a guardare (ultima_visione recente)
    continua_qs = Movie.objects.filter(ultima_visione__isnull=False).order_by(
        "-ultima_visione"
    )[:12]
    if continua_qs:
        sezioni.append(
            {
                "titolo": "Continua a guardare",
                "movies": continua_qs,
                "special": True,
                "slug": "continua-a-guardare",
            }
        )

    # Raggruppamento per genere (dall’elenco movies passato)
    gruppi = defaultdict(list)
    for m in movies:
        raw_genere = (m.genere or "").strip()
        main_genre = raw_genere.split(",")[0].strip() if raw_genere else "Senza genere"
        gruppi[main_genre].append(m)

    for genere, lista in sorted(gruppi.items(), key=lambda x: x[0]):
        sezioni.append(
            {
                "titolo": genere,
                "movies": lista[:max_per_genre],
                "special": False,
                "slug": None,
            }
        )

    return sezioni


def get_random_movie_with_poster():
    qs = Movie.objects.exclude(locandina_url__isnull=True).exclude(
        locandina_url__exact=""
    )
    if not qs.exists():
        return None
    return random.choice(list(qs))


# ---------------------------------------------


def build_movie_filters(request):
    """
    Applica i filtri letti dalla querystring e restituisce
    la queryset filtrata e il dizionario dei filtri per il template.
    """
    qs = Movie.objects.all()

    titolo = request.GET.get("titolo", "")
    anno_da = request.GET.get("anno_da", "")
    anno_a = request.GET.get("anno_a", "")
    genere = request.GET.get("genere", "")
    regista = request.GET.get("regista", "")
    visto = request.GET.get("visto", "")  # "", "si", "no"
    voto_da = request.GET.get("voto_da", "")
    voto_a = request.GET.get("voto_a", "")
    codifica = request.GET.get("codifica", "")
    estensione = request.GET.get("estensione", "")
    dim_da = request.GET.get("dim_da", "")
    dim_a = request.GET.get("dim_a", "")
    percorso = request.GET.get("percorso", "")

    if titolo:
        qs = qs.filter(titolo__icontains=titolo)
    if anno_da:
        qs = qs.filter(anno__gte=anno_da)
    if anno_a:
        qs = qs.filter(anno__lte=anno_a)
    if genere:
        qs = qs.filter(genere__icontains=genere)
    if regista:
        qs = qs.filter(regista__icontains=regista)
    if visto == "si":
        qs = qs.filter(visto=True)
    elif visto == "no":
        qs = qs.filter(visto=False)
    if voto_da:
        qs = qs.filter(voto__gte=voto_da)
    if voto_a:
        qs = qs.filter(voto__lte=voto_a)
    if codifica:
        qs = qs.filter(codifica__icontains=codifica)
    if estensione:
        qs = qs.filter(estensione__icontains=estensione)
    if dim_da:
        qs = qs.filter(dimensione_file_mb__gte=dim_da)
    if dim_a:
        qs = qs.filter(dimensione_file_mb__lte=dim_a)
    if percorso:
        qs = qs.filter(percorso__icontains=percorso)

    filtri = {
        "titolo": titolo,
        "anno_da": anno_da,
        "anno_a": anno_a,
        "genere": genere,
        "regista": regista,
        "visto": visto,
        "voto_da": voto_da,
        "voto_a": voto_a,
        "codifica": codifica,
        "estensione": estensione,
        "dim_da": dim_da,
        "dim_a": dim_a,
        "percorso": percorso,
    }
    return qs, filtri


def movie_list(request):

    qs, filtri = build_movie_filters(request)
    qs = qs.order_by("titolo")

    # --- PAGINAZIONE ---
    paginator = Paginator(qs, 24)  # 24 film per pagina
    page_number = request.GET.get("page")  # numero pagina da URL ?page=2

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # mantieni i filtri nei link di paginazione
    querydict = request.GET.copy()
    querydict.pop("page", None)
    base_query = querydict.urlencode()

    # 🔥 Film random con locandina per l'header
    all_with_poster = Movie.objects.exclude(locandina_url__isnull=True).exclude(
        locandina_url__exact=""
    )
    random_movie = random_movie = get_random_movie_with_poster()

    return render(
        request,
        "catalogo/movie_list.html",
        {
            "active_page": "all_movies",
            "movies": page_obj,
            "filtri": filtri,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "base_query": base_query,
            "random_movie": random_movie,
        },
    )


def movie_play(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    file_path = movie.percorso  # percorso completo sul disco

    if not file_path:
        messages.error(request, "Nessun percorso file è stato salvato per questo film.")
        return redirect("movie_list")

    file_path = os.path.normpath(file_path)

    if not os.path.exists(file_path):
        messages.error(
            request, f"Il file non è stato trovato nel percorso salvato:\n{file_path}"
        )
        return redirect("movie_list")

    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["cmd", "/c", "start", "", file_path], shell=True)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])

        # QUI NON METTIAMO NESSUN MESSAGGIO DI SUCCESSO

    except Exception as e:
        messages.error(request, f"Errore nell'aprire il file:\n{e}")

    # Torna alla pagina precedente (di solito la lista) oppure alla lista
    next_url = request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("movie_list")


def scan_folder(request):
    """Scansiona una cartella e aggiunge i file video al catalogo (con tentativo di anno dal nome)."""
    if request.method != "POST":
        return redirect("movie_list")

    base_dir = request.POST.get("base_dir", "").strip()

    if not base_dir:
        messages.error(request, "Devi specificare una cartella da scansionare.")
        return redirect("movie_list")

    if not os.path.isdir(base_dir):
        messages.error(
            request, f"La cartella '{base_dir}' non esiste o non è accessibile."
        )
        return redirect("movie_list")

    count_total = 0
    count_new = 0

    for root, dirs, files in os.walk(base_dir):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                count_total += 1
                full_path = os.path.join(root, name)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)

                # usa la funzione helper per capire titolo e anno
                titolo, anno_trovato = guess_title_and_year(name)

                # se non trova anno, metti un default (es. 2000)
                anno = anno_trovato

                movie, created = Movie.objects.get_or_create(
                    percorso=full_path,
                    defaults={
                        "titolo": titolo,
                        "anno": anno,
                        "genere": "",
                        "regista": "",
                        "dimensione_file_mb": round(size_mb, 1),
                        "estensione": ext,
                        "codifica": "",
                    },
                )
                if created:
                    count_new += 1

    if count_total == 0:
        messages.info(request, "Nessun file video trovato nella cartella.")
    else:
        messages.success(
            request,
            f"Trovati {count_total} file video, aggiunti {count_new} nuovi film al catalogo.",
        )

    return redirect("movie_list")


def movie_detail(request, pk):
    movie = get_object_or_404(Movie, pk=pk)

    # stesso ordinamento della lista (titolo)
    qs = Movie.objects.order_by("titolo").values_list("pk", flat=True)
    ids = list(qs)

    prev_movie = None
    next_movie = None

    if movie.pk in ids:
        idx = ids.index(movie.pk)
        if idx > 0:
            prev_movie = Movie.objects.get(pk=ids[idx - 1])
        if idx < len(ids) - 1:
            next_movie = Movie.objects.get(pk=ids[idx + 1])

    return render(
        request,
        "catalogo/movie_detail.html",
        {
            "movie": movie,
            "prev_movie": prev_movie,
            "next_movie": next_movie,
        },
    )


def movie_edit(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or request.META.get("HTTP_REFERER")
    )
    if next_url and not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = None

    if request.method == "POST":
        form = MovieForm(request.POST, instance=movie)
        if form.is_valid():
            form.save()
            messages.success(request, "Film aggiornato con successo.")
            if next_url:
                return redirect(next_url)
            return redirect("movie_list")
    else:
        form = MovieForm(instance=movie)

    return render(
        request,
        "catalogo/movie_form.html",
        {
            "form": form,
            "movie": movie,
            "next": next_url,
        },
    )


def movie_delete(request, pk):
    movie = get_object_or_404(Movie, pk=pk)

    if request.method == "POST":
        titolo = str(movie)
        movie.delete()
        messages.success(request, f"Film '{titolo}' eliminato.")
        return redirect("movie_list")

    return render(
        request,
        "catalogo/movie_confirm_delete.html",
        {
            "movie": movie,
        },
    )


def update_posters(request):
    if request.method != "POST":
        return redirect("movie_list")

    movies = Movie.objects.filter(Q(trama__isnull=True) | Q(trama__exact=""))

    count_checked = 0
    count_updated = 0

    for movie in movies:
        count_checked += 1
        data = fetch_movie_data_from_tmdb(movie.titolo, movie.anno)
        if not data:
            continue

        changed_fields = apply_tmdb_data(movie, data, overwrite=False)
        if changed_fields:
            movie.save(update_fields=changed_fields)
            count_updated += 1

    if count_checked == 0:
        messages.info(request, "Non ci sono film da aggiornare.")
    else:
        messages.success(
            request,
            f"Controllati {count_checked} film, aggiornati {count_updated} record.",
        )

    return redirect("movie_list")


def update_movie_poster(request, pk):
    """
    Aggiorna locandina e metadati per UN singolo film,
    usando TMDB (stessa logica di update_posters ma one-shot).
    """
    movie = get_object_or_404(Movie, pk=pk)

    # qui usiamo la stessa funzione che usi in update_posters
    # supponiamo che ritorni un dizionario con i dati, oppure None se non trova nulla
    tmdb_data = fetch_movie_data_from_tmdb(movie.titolo, movie.anno)
    if not tmdb_data:
        messages.warning(
            request, f"Nessun risultato trovato su TMDB per '{movie.titolo}'."
        )
        return redirect("movie_list")

    changed = apply_tmdb_data(movie, tmdb_data, overwrite=True)
    if changed:
        movie.save(update_fields=changed)
        messages.success(
            request,
            f"Dati aggiornati da TMDB per {movie.titolo} ({', '.join(changed)}).",
        )
    else:
        messages.info(request, "Nessun campo aggiornato.")

    return redirect("movie_list")


def movie_by_genre(request):
    movies = Movie.objects.all().order_by("-id")
    sezioni = group_movies_by_genre(movies, max_per_genre=24)

    all_with_poster = Movie.objects.exclude(locandina_url__isnull=True).exclude(
        locandina_url__exact=""
    )
    random_movie = get_random_movie_with_poster()

    return render(
        request,
        "catalogo/movie_by_genre.html",
        {
            "active_page": "home",
            "sections": sezioni,
            "random_movie": random_movie,
        },
    )


def random_movie(request):
    ids = list(Movie.objects.values_list("pk", flat=True))
    if not ids:
        messages.error(request, "Nessun film disponibile.")
        return redirect("movie_list")
    pk = random.choice(ids)
    return redirect("movie_detail", pk=pk)
