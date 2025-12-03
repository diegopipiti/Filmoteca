# Catalogo Film (Django + HTMX + Alpine)

Questa base di progetto implementa un catalogo film con Django 5, interazioni dinamiche tramite HTMX e piccoli comportamenti client con Alpine.js. L'obiettivo è gestire titoli, generi, registi, stato di visione e valutazioni, con un focus sulla semplicità e sul mantenimento dei dati in SQLite.

## Stack
- **Backend:** Django 5
- **UI dinamica:** HTMX (per richieste parziali) + Alpine.js (per microinterazioni)
- **Database:** SQLite di default, facilmente sostituibile con Postgres o altro.

## Prerequisiti
- Python 3.11+
- pip
- Facoltativo: virtualenv (`python -m venv .venv`)

Verifica la versione di Python prima di iniziare:

```bash
python --version
# oppure
python3 --version
```
Assicurati che il numero sia **3.11** o superiore.

## Setup rapido
1. Posizionati nella cartella del progetto che contiene `manage.py` (esempio in questo repository: `/workspace/Documentazione/Documentazione`).
2. Crea e attiva un ambiente virtuale (opzionale ma consigliato):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
4. Crea il file `.env` partendo dall'esempio:
   ```bash
   cp .env.example .env
   ```
5. Applica le migrazioni e avvia il server di sviluppo:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

   > Se vedi l'errore `django.db.utils.OperationalError: no such table: films_film`, significa che le migrazioni non sono state applicate: ripeti il comando `python manage.py migrate` dopo aver installato le dipendenze.

Visita `http://127.0.0.1:8000/` per vedere la lista film. L'admin Django è disponibile su `/admin/`.

### Crea un utente amministratore
Per accedere all'admin ed inserire rapidamente film, genera un superuser dopo aver applicato le migrazioni:

```bash
python manage.py createsuperuser
```

Ti verranno chiesti username, email (facoltativo) e password. Poi accedi a `/admin/` con queste credenziali.

### Importa un file XLSX con solo i titoli
Se hai un file Excel che contiene solo i titoli, puoi popolare il database in due modalità:

- **Senza completamento dati (solo titoli):** non serve la chiave OMDb, gli altri campi restano vuoti.
- **Con autocompilazione OMDb:** richiede la chiave API per ottenere anno, regista, generi, trama, poster e rating.

1. Prepara il file XLSX: la prima riga è l'intestazione, serve almeno una colonna `Titolo`/`Title`/`Film` con i nomi dei film (le altre colonne possono mancare).
2. Esegui l'import (da dentro la cartella che contiene `manage.py`):
   ```bash
   # Solo titoli, altri campi vuoti
   python manage.py import_films_xlsx /percorso/del/file.xlsx --titles-only

   # Autocompilazione OMDb (richiede OMDB_API_KEY nel .env)
   python manage.py import_films_xlsx /percorso/del/file.xlsx
   # Aggiungi --watched se vuoi segnare tutti come "visti"
   # python manage.py import_films_xlsx /percorso/del/file.xlsx --watched
   ```

Se usi l'autocompilazione OMDb:

1. Ottieni una chiave API gratuita da [OMDb](http://www.omdbapi.com/apikey.aspx). Ho già inserito la variabile `OMDB_API_KEY` nel tuo `.env` con il segnaposto `INSERISCI_LA_TUA_CHIAVE`: sostituiscilo con la tua chiave, per esempio:
   ```bash
   sed -i "s/INSERISCI_LA_TUA_CHIAVE/la_tua_chiave/" .env
   # in alternativa aggiungi/modifica manualmente la riga
   # OMDB_API_KEY=la_tua_chiave
   ```
2. Il comando verifica subito la chiave OMDb prima di leggere il file: se la chiave è errata/inattiva riceverai un errore immediato (401 Unauthorized) con le istruzioni per sostituirla. Puoi testarla anche manualmente con:
   ```bash
   curl "https://www.omdbapi.com/?t=Matrix&apikey=$OMDB_API_KEY"
   ```

### Dove si trova `requirements.txt`
- Percorso completo nel repository: `/workspace/Documentazione/Documentazione/requirements.txt`.
- Lo trovi nella stessa cartella di `manage.py`, quindi assicurati di essere nella directory `Documentazione/` interna al progetto (quella che contiene `catalogo/`, `films/`, `templates/`).
- Per verificare che il file esista, puoi eseguire `ls requirements.txt` quando ti trovi in quella cartella.

## Dove si trova il progetto nel repository
- Radice del repository: `/workspace/Documentazione/` (qui trovi la cartella `.git` e, se l'hai creato, `.venv/`).
- Codice Django: `/workspace/Documentazione/Documentazione/` (contiene `manage.py`, `catalogo/`, `films/`, `templates/`).
- Da qualsiasi posizione, puoi raggiungere il progetto con:
  ```bash
  cd /workspace/Documentazione/Documentazione
  ls  # dovresti vedere manage.py, catalogo/, films/, templates/
  ```
- Dove risiede il progetto: i file sono nel tuo ambiente locale (il percorso sopra). Se stai usando un container o una VM cloud, la cartella `/workspace/Documentazione/` è montata in quel contesto; puoi verificarlo con `pwd` per vedere il percorso corrente.

## Struttura del progetto
```
.
├── catalogo/           # Configurazione principale Django
├── films/              # App dedicata a film, generi, registi
├── templates/          # Template base e viste HTMX
├── requirements.txt    # Dipendenze
└── README.md           # Questo file
```

## Note su HTMX/Alpine
- **HTMX** è già incluso via middleware in `settings.py` e i template usano `hx-get`/`hx-target` per filtri live.
- **Alpine.js** è incluso da CDN per piccoli toggle lato client (es. apertura filtri o dettagli).

## Prossimi passi
- Aggiungere autenticazione per distinguere utenti diversi.
- Implementare caricamento di locandine su storage esterno o cartella locale.
- Estendere i filtri (per genere, regista, intervallo di anni, voto minimo) usando endpoint HTMX dedicati.
- Coprire con test unitari i modelli e le viste principali.
