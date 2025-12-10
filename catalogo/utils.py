import re
import os
from typing import Optional, Tuple

VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".mpg", ".mpeg"]
YEAR_RE = re.compile(r"(19[0-9]{2}|20[0-3][0-9])")
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

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


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
