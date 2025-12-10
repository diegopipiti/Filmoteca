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


VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".mpg", ".mpeg"]

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# Regex per intercettare anni plausibili (1900–2039, puoi restringerla se vuoi)
YEAR_RE = re.compile(r"(19[0-9]{2}|20[0-3][0-9])")

# Token "rumore" tipici dei nomi file: lingue, codec, qualità, gruppi release, ecc.
NOISE_TOKENS = {
    "italian",
    "italiano",
    "eng",
    "english",
    "multi",
    "sub",
    "subs",
    "ac3",
    "dts",
    "xvid",
    "divx",
    "h264",
    "x264",
    "h265",
    "x265",
    "dvdrip",
    "bdrip",
    "webrip",
    "webdl",
    "bluray",
    "hdrip",
    "cam",
    "limited",
    "uncut",
    "extended",
    "remastered",
    "1080p",
    "720p",
    "2160p",
    "4k",
    "uhd",
    "gbm",
    "i_n_r_g",
    "ita",
    "proper",
    "repack",
}


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


def fetch_movie_data_from_tmdb(
    title: str, year: Optional[int] = None
) -> Optional[dict]:
    """
    Chiede a TMDB i dati di un film e restituisce un dizionario con:
      - poster_url
      - overview (trama)
      - year
      - director
      - genres (stringa tipo "Drammatico, Thriller")

    Se non trova niente o c'è un errore, restituisce None.
    """
    api_key = getattr(settings, "TMDB_API_KEY", None)
    if not api_key or api_key == "INSERISCI_LA_TUA_API_KEY_QUI":
        return None

    # 1) Cerca il film per titolo (e opzionalmente anno)
    params = {
        "api_key": api_key,
        "query": title,
        "include_adult": "false",
        "language": "it-IT",
    }
    if year:
        params["year"] = year

    try:
        resp = requests.get(TMDB_SEARCH_URL, params=params, timeout=5)
        resp.raise_for_status()
    except Exception:
        return None

    data = resp.json()
    results = data.get("results") or []
    if not results:
        return None

    movie = results[0]
    movie_id = movie.get("id")
    poster_path = movie.get("poster_path")
    release_date = movie.get("release_date") or ""
    overview_it = movie.get("overview") or ""

    director_name = None
    genres_str = None

    # 2) Chiede dettagli + credits per avere regista e generi
    if movie_id:
        try:
            detail_resp = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}",
                params={
                    "api_key": api_key,
                    "language": "it-IT",
                    "append_to_response": "credits",
                },
                timeout=5,
            )
            detail_resp.raise_for_status()
            detail_data = detail_resp.json()

            # generi
            genres = detail_data.get("genres") or []
            if genres:
                genres_str = ", ".join(g.get("name") for g in genres if g.get("name"))

            # regista dai credits
            credits = detail_data.get("credits") or {}
            crew = credits.get("crew") or []
            for person in crew:
                if person.get("job") == "Director":
                    director_name = person.get("name")
                    break

            # se l'overview dal search era vuota, prova con quella dei dettagli
            if not overview_it:
                overview_it = detail_data.get("overview") or ""

        except Exception:
            # se fallisce questa chiamata, pazienza, useremo solo i dati base
            pass

    # calcolo poster_url completo
    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

    # estrazione anno da release_date (formato "YYYY-MM-DD")
    year_val: Optional[int] = None
    if release_date and len(release_date) >= 4:
        try:
            year_val = int(release_date[:4])
        except ValueError:
            year_val = None

    result = {
        "poster_url": poster_url,
        "overview": (overview_it.strip() or None),
        "year": year_val,
        "director": director_name,
        "genres": genres_str,
    }
    return result


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
    random_movie = (
        random.choice(list(all_with_poster)) if all_with_poster.exists() else None
    )

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


def _apri_file(path: str):
    """Apri il file video con il player predefinito del sistema operativo."""
    sistema = platform.system()
    if sistema == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sistema == "Darwin":  # macOS
        subprocess.Popen(["open", path])
    else:  # Linux
        subprocess.Popen(["xdg-open", path])


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
    """
    Prova a recuperare locandina, trama, anno, regista e genere
    da TMDB per i film che non hanno ancora questi dati completi.
    """
    if request.method != "POST":
        return redirect("movie_list")

    # puoi decidere qui il criterio di selezione:
    # - solo quelli senza locandina
    # - oppure tutti i film
    # per non fare troppe chiamate, restiamo sui film senza locandina
    # Aggiorna solo i film che NON hanno ancora la trama
    movies = Movie.objects.filter(Q(trama__isnull=True) | Q(trama__exact=""))

    count_checked = 0
    count_updated = 0

    for movie in movies:
        count_checked += 1
        data = fetch_movie_data_from_tmdb(movie.titolo, movie.anno)
        if not data:
            continue

        changed_fields = []

        poster_url = data.get("poster_url")
        overview = data.get("overview")
        year_val = data.get("year")
        director_name = data.get("director")
        genres_str = data.get("genres")

        # aggiorna SOLO se il campo è vuoto, per non sovrascrivere
        if poster_url and not movie.locandina_url:
            movie.locandina_url = poster_url
            changed_fields.append("locandina_url")

        if overview and not movie.trama:
            movie.trama = overview
            changed_fields.append("trama")

        if year_val and not movie.anno:
            movie.anno = year_val
            changed_fields.append("anno")

        if director_name and not movie.regista:
            movie.regista = director_name
            changed_fields.append("regista")

        if genres_str and not movie.genere:
            movie.genere = genres_str
            changed_fields.append("genere")

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

    # Adatta questi campi a come hai strutturato la risposta TMDB
    poster_url = tmdb_data.get("poster_url")
    trama = tmdb_data.get("overview") or tmdb_data.get("trama")
    anno = tmdb_data.get("year") or tmdb_data.get("anno")
    regista = tmdb_data.get("director") or tmdb_data.get("regista")
    genere = tmdb_data.get("genres") or tmdb_data.get("genere")

    if poster_url:
        movie.locandina_url = poster_url
    if trama:
        movie.trama = trama
    if anno:
        movie.anno = anno
    if regista:
        movie.regista = regista
    if genere:
        # se genres è una lista, uniscila
        if isinstance(genere, (list, tuple)):
            movie.genere = ", ".join(genere)
        else:
            movie.genere = genere

    movie.save()

    messages.success(request, f"Metadati aggiornati per '{movie.titolo}'.")
    return redirect("movie_list")


def guess_title_and_year(filename: str) -> Tuple[str, Optional[int]]:
    """
    Cerca di dedurre il titolo del film e l'anno da un nome file tipo:
    'Cheri.2009.iTALiAN.LiMITED.AC3.DVDRip.XviD.GBM.avi'

    Ritorna:
        (titolo_pulito, anno_oppure_None)
    """

    # 1) Tieni solo il nome del file senza path
    base = os.path.basename(filename)

    # 2) Togli l'estensione (.mkv, .avi, .mp4, ecc.)
    name, _ext = os.path.splitext(base)

    # 3) Sostituisci puntini/underscore con spazi
    #    es: "Cheri.2009.iTALiAN..." → "Cheri 2009 iTALiAN..."
    name_clean = re.sub(r"[._]+", " ", name).strip()

    # 4) Cerca un anno usando la regex
    match_year = YEAR_RE.search(name_clean)
    anno: Optional[int] = None
    if match_year:
        anno = int(match_year.group(0))
        # prendiamo la parte prima dell'anno come base del titolo
        title_part = name_clean[: match_year.start()]
    else:
        # se non troviamo anno, usiamo tutta la stringa
        title_part = name_clean

    # 5) Spezzettiamo in token (parole)
    tokens = title_part.split()

    cleaned_tokens = []
    for t in tokens:
        t_norm = t.lower()

        # se vediamo un token di "rumore", assumiamo che da lì in poi non sia più titolo
        if t_norm in NOISE_TOKENS:
            break

        # salta cose tipo CD1, CD2, DISC1...
        if re.match(r"cd\d+", t_norm) or re.match(r"disc\d+", t_norm):
            continue

        cleaned_tokens.append(t)

    # 6) Ricostruisci il titolo pulito
    titolo = " ".join(cleaned_tokens).strip()

    # Se per qualche motivo è vuoto, fai un fallback sulla parte prima dell'anno
    if not titolo:
        titolo = title_part.strip()

    # 7) Normalizza la capitalizzazione, se è tutto maiuscolo tipo CHERI → Cheri
    if titolo.isupper():
        titolo = titolo.title()

    return titolo, anno

    gruppi = defaultdict(list)

    for m in movies:
        raw_genere = (m.genere or "").strip()
        if not raw_genere:
            main_genre = "Senza genere"
        else:
            main_genre = raw_genere.split(",")[0].strip()
        gruppi[main_genre].append(m)

    # Optional: limitiamo il numero di film per riga (es. 24)
    MAX_PER_GENRE = 24
    sezioni = []
    for genere, lista in sorted(
        gruppi.items(), key=lambda x: x[0]
    ):  # ordinati alfabeticamente
        sezioni.append(
            {
                "titolo": genere,
                "movies": lista[:MAX_PER_GENRE],
            }
        )

    return render(
        request,
        "catalogo/movie_by_genre.html",
        {
            "sections": sezioni,
        },
    )


def movie_by_genre(request):
    movies = Movie.objects.all().order_by("-id")

    gruppi = defaultdict(list)

    # --- 1. SEZIONE SPECIALE: film con voto >= 8 (4 stelle) ---
    top_rated = Movie.objects.filter(voto__gte=8).order_by("-voto", "-id")
    # Limitiamoli a 24 o al numero che preferisci
    TOP_LIMIT = 24
    top_rated = top_rated[:TOP_LIMIT]

    # --- 2. RAGGRUPPAMENTO PER GENERE ---
    for m in movies:
        raw_genere = (m.genere or "").strip()
        if not raw_genere:
            main_genre = "Senza genere"
        else:
            main_genre = raw_genere.split(",")[0].strip()
        gruppi[main_genre].append(m)

    MAX_PER_GENRE = 24

    sezioni = []

    # Aggiungi PRIMA la categoria speciale ⭐⭐⭐⭐
    if top_rated:
        sezioni.append(
            {
                "titolo": "⭐⭐⭐⭐ Film 4 stelle e oltre",
                "movies": top_rated,
                "special": True,  # per eventuali stili diversi in futuro
            }
        )

    # CONTINUA A GUARDARE (in base a data_ultima_visione)
    continua_qs = Movie.objects.filter(ultima_visione__isnull=False).order_by(
        "-ultima_visione"
    )[
        :12
    ]  # prendi gli ultimi visti

    if continua_qs.exists():
        sezioni.append(
            {
                "titolo": "Continua a guardare",
                "slug": "continua-a-guardare",
                "special": True,
                "movies": continua_qs,
            }
        )

    # Aggiungi tutte le altre categorie normali
    for genere, lista in sorted(gruppi.items(), key=lambda x: x[0]):
        sezioni.append(
            {
                "titolo": genere,
                "movies": lista[:MAX_PER_GENRE],
                "special": False,
            }
        )

    # 🔥 Film random con locandina per l'header
    all_with_poster = Movie.objects.exclude(locandina_url__isnull=True).exclude(
        locandina_url__exact=""
    )
    random_movie = (
        random.choice(list(all_with_poster)) if all_with_poster.exists() else None
    )

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
