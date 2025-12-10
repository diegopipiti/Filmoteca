import requests
from django.conf import settings


def fetch_omdb_ratings(imdb_id: str):
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
    # Metascore (0-100) → possiamo riportarlo /10
    metascore = data.get("Metascore")
    critic_rating = float(metascore) / 10 if metascore and metascore.isdigit() else None
    critic_source = "Metascore" if critic_rating else None
    return {
        "critic_rating": critic_rating,
        "critic_source": critic_source,
        "critic_votes": None,
    }
