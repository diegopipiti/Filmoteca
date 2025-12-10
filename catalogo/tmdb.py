import requests
from django.conf import settings
from typing import Optional

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


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

            genres = detail_data.get("genres") or []
            if genres:
                genres_str = ", ".join(g.get("name") for g in genres if g.get("name"))

            credits = detail_data.get("credits") or {}
            crew = credits.get("crew") or []
            for person in crew:
                if person.get("job") == "Director":
                    director_name = person.get("name")
                    break

            if not overview_it:
                overview_it = detail_data.get("overview") or ""
        except Exception:
            pass

    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

    year_val: Optional[int] = None
    if release_date and len(release_date) >= 4:
        try:
            year_val = int(release_date[:4])
        except ValueError:
            year_val = None

    vote_average = movie.get("vote_average")
    vote_count = movie.get("vote_count")

    imdb_id = None
    if movie_id:
        try:
            ext = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/external_ids",
                params={"api_key": api_key},
                timeout=5,
            )
            ext.raise_for_status()
            imdb_id = ext.json().get("imdb_id")
        except Exception:
            imdb_id = None

    return {
        "poster_url": poster_url,
        "overview": (overview_it.strip() or None),
        "year": year_val,
        "director": director_name,
        "genres": genres_str,
        "public_rating": vote_average,
        "public_votes": vote_count,
        "imdb_id": imdb_id,
    }


# catalogo/tmdb.py
def apply_tmdb_data(movie, data: dict, overwrite: bool = True) -> list[str]:
    """
    Applica i campi TMDB al model Movie.
    Se overwrite è True, sovrascrive anche i valori esistenti.
    Ritorna la lista dei campi modificati.
    """
    changed = []

    poster_url = data.get("poster_url")
    overview = data.get("overview")
    year_val = data.get("year")
    director_name = data.get("director")
    genres_str = data.get("genres")

    if poster_url and (overwrite or not movie.locandina_url):
        movie.locandina_url = poster_url
        changed.append("locandina_url")

    public_rating = data.get("public_rating")
    public_votes = data.get("public_votes")

    if public_rating is not None and (overwrite or movie.public_rating is None):
        movie.public_rating = public_rating
        changed.append("public_rating")

    if public_votes is not None and (overwrite or movie.public_votes is None):
        movie.public_votes = public_votes
        changed.append("public_votes")

    if overview and (overwrite or not movie.trama):
        movie.trama = overview
        changed.append("trama")

    if year_val and (overwrite or not movie.anno):
        movie.anno = year_val
        changed.append("anno")

    if director_name and (overwrite or not movie.regista):
        movie.regista = director_name
        changed.append("regista")

    if genres_str and (overwrite or not movie.genere):
        movie.genere = genres_str
        changed.append("genere")

    # Ottiene il voto della critica e l'ID IMDB
    imdb_id = data.get("imdb_id")
    if imdb_id and (overwrite or not movie.imdb_id):
        movie.imdb_id = imdb_id
        changed.append("imdb_id")

    critic_rating = data.get("critic_rating")
    critic_source = data.get("critic_source")
    critic_votes = data.get("critic_votes")
    if critic_rating is not None and (overwrite or movie.critic_rating is None):
        movie.critic_rating = critic_rating
        changed.append("critic_rating")
    if critic_source and (overwrite or not movie.critic_source):
        movie.critic_source = critic_source
        changed.append("critic_source")
    if critic_votes is not None and (overwrite or movie.critic_votes is None):
        movie.critic_votes = critic_votes
        changed.append("critic_votes")

    return changed
