import requests
from django.conf import settings


def fetch_omdb_ratings(imdb_id: str):
    """
    Recupera i rating della critica da OMDb usando l'imdb_id.
    Restituisce un dizionario con critic_rating (scala 0-10),
    critic_source e critic_votes (se disponibile), altrimenti None.
    """
    api_key = getattr(settings, "OMDB_API_KEY", None)
    if not api_key or not imdb_id:
        return None

    try:
        resp = requests.get(
            "http://www.omdbapi.com/",
            params={"apikey": api_key, "i": imdb_id},
            timeout=5,
        )
        resp.raise_for_status()
    except Exception:
        return None

    data = resp.json()
    if data.get("Response") != "True":
        return None

    metascore = data.get("Metascore")
    critic_rating = None
    if metascore and str(metascore).isdigit():
        critic_rating = float(metascore) / 10  # converti 0-100 -> 0-10

    return {
        "critic_rating": critic_rating,
        "critic_source": "Metascore" if critic_rating is not None else None,
        "critic_votes": None,  # OMDb non fornisce un conteggio per la critica
    }

