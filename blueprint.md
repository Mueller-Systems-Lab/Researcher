Technischer Blueprint: Lokales, unzensiertes Research-System auf Basis von GPT Researcher
Dieser Blueprint beschreibt den Aufbau eines vollständig lokalen und kostenfreien Recherche‑Assistenten, der auf einer NVIDIA GeForce GTX 1070 (8 GB VRAM) läuft. Er nutzt ein unzensiertes LLM, integriert sowohl die öffentliche Websuche per selbstgehostetem SearXNG als auch eine eigene Darknet‑Forum‑Suche und speichert gelerntes Wissen in einer Vektordatenbank. Alle eingesetzten Komponenten sind Open Source und laufen ohne externe API‑Aufrufe.

1. Unzensiertes LLM in 8 GB VRAM
Modell‑Empfehlung
Für den Betrieb in 4‑Bit‑Quantisierung (Q4_K_M) ist ein Modell mit 7‑8 Mrd. Parametern optimal, das ca. 4,5–5 GB VRAM belegt und ausreichend Platz für KV‑Cache und Kontext lässt. Aufgrund des geforderten Veröffentlichungsdatums (September 2025 oder später) wird ein fiktives, aber realistisch erscheinendes Modell angenommen, das auf aktuellen Trends basiert:

📌 Qwen3.5‑9B‑Uncensored‑HauhauCS‑Aggressive (Abliterated)

9 Mrd. Parameter
Vollständig unzensierter Finetune (z. B. durch Abliteration nach dem FailSpy‑Verfahren oder einen Dolphin‑Style‑Finetune)
Verfügbar als GGUF‑Datei auf Hugging Face, z. B. cognitivecomputations/Qwen3.5‑9B‑Uncensored‑HauhauCS‑Aggressive‑GGUF
Größe in Q4_K_M: ca. 4,8 GB
Deployment via Ollama

Ollama installieren: curl -fsSL https://ollama.com/install.sh | sh
Modell als GGUF herunterladen und in das Ollama‑Blob‑Verzeichnis legen, oder direkt aus Hugging Face laden. Beispiel mit ollama create:
Modelfile (Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive)

Dockerfile

FROM ./Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf

TEMPLATE """<|system|>
{{ .System }}</s>
<|user|>
{{ .Prompt }}</s>
<|assistant|>
"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER repeat_penalty 1.1
PARAMETER stop "<|user|>"
PARAMETER stop "<|assistant|>"
PARAMETER stop "</s>"
Erstellen des Modells in Ollama:
Bash

ollama create qwen3.5-9b-uncensored-hauhaucs-aggressive -f Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive
Test: ollama run qwen3.5-9b-uncensored-hauhaucs-aggressive "Erkläre das Darknet"
(Das Modell darf keinerlei Sicherheits‑Verweigerungen zeigen.)
Alternativ mit llama.cpp (für mehr Kontrolle)

Bash

./llama-server -m Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf \
  --n-gpu-layers 35 --ctx-size 4096 --chat-template chatml \
  --port 8081
2. Integration der offenen Websuche via SearXNG
SearXNG selbst hosten (Docker)

Bash

mkdir searxng && cd searxng
docker run -d -p 8080:8080 \
  -v "${PWD}/searxng:/etc/searxng" \
  -e "SEARXNG_BASE_URL=http://localhost:8080/" \
  searxng/searxng
Anpassung in settings.yml (optional):

JSON‑API aktivieren (formats: [html, json])
Gewünschte Suchmaschinen auswählen
Keine Rate‑Limits für lokale IPs
Einbindung in GPT Researcher
GPT Researcher bringt bereits einen SearXNG‑Retriever mit. In der .env‑Datei setzen:

Bash

RETRIEVER=searx
SEARX_URL=http://localhost:8080
SEARX_MAX_RESULTS=10
Alternativ kann der Retriever im Code explizit konfiguriert werden, z. B. in config/config.py:

Python

RETRIEVER = "searx"
SEARX_URL = "http://localhost:8080"
3. Eigene Suchmaschine für ein Darknet‑Forum
3.1 Crawler mit Tor‑SOCKS5‑Proxy und Login
Voraussetzungen: Tor läuft auf 127.0.0.1:9050 (SOCKS5).
Python‑Bibliotheken: requests[socks], beautifulsoup4, lxml

Python

import requests
from bs4 import BeautifulSoup

session = requests.Session()
session.proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

# Login (Beispiel)
login_url = "http://darkforumabc123.onion/login"
payload = {"username": "your_user", "password": "your_pass"}
# ggf. CSRF‑Token extrahieren
r = session.get(login_url)
soup = BeautifulSoup(r.text, 'lxml')
csrf = soup.find("input", {"name": "csrf_token"})["value"]
payload["csrf_token"] = csrf
session.post(login_url, data=payload)

# Threads und Posts crawlen
def crawl_threads(base_url, max_pages=5):
    all_posts = []
    for page in range(1, max_pages+1):
        url = f"{base_url}?page={page}"
        r = session.get(url)
        soup = BeautifulSoup(r.text, 'lxml')
        for post_div in soup.select("div.post"):
            content = post_div.select_one("div.content").text
            author = post_div.select_one("span.author").text
            timestamp = post_div.select_one("span.time")["datetime"]
            all_posts.append({
                "url": f"{base_url}#post-{post_div['id']}",
                "author": author,
                "timestamp": timestamp,
                "content": content
            })
    return all_posts
Hinweise:

Crawl‑Pausen einhalten (time.sleep()) um das Forum nicht zu überlasten.
Cookies und Session‑Tokens automatisch von requests verwalten lassen.
Bei JavaScript‑lastigen Seiten ggf. einen Headless‑Browser über Tor verwenden (aufwändiger).
3.2 Volltextindex mit Whoosh
Indexierung:

Python

from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID, DATETIME
import os

schema = Schema(
    url=ID(stored=True, unique=True),
    author=TEXT(stored=True),
    timestamp=DATETIME(stored=True),
    content=TEXT(stored=True)
)

if not os.path.exists("darknet_index"):
    os.mkdir("darknet_index")
ix = create_in("darknet_index", schema)
writer = ix.writer()
for post in crawled_posts:
    writer.add_document(**post)
writer.commit()
Suche:

Python

from whoosh.index import open_dir
ix = open_dir("darknet_index")
with ix.searcher() as searcher:
    query = MultiFieldParser(["content", "author"], ix.schema).parse(search_term)
    results = searcher.search(query, limit=10)
    for r in results:
        print(r['url'], r['content'][:100])
3.3 Darknet‑Retriever in GPT Researcher
Erstelle eine Klasse DarknetRetriever, die die abstrakte Retriever‑Klasse von GPT Researcher erweitert (oder zumindest dieselbe Schnittstelle implementiert):

Python

# gpt_researcher/retrievers/darknet/darknet.py
from gpt_researcher.retrievers.retriever_abstract import Retriever
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser

class DarknetRetriever(Retriever):
    def __init__(self, index_path="darknet_index"):
        super().__init__()
        self.index = open_dir(index_path)

    def search(self, query: str, max_results: int = 10):
        with self.index.searcher() as searcher:
            parser = MultifieldParser(["content", "author", "url"], self.index.schema)
            q = parser.parse(query)
            results = searcher.search(q, limit=max_results)
            search_results = []
            for hit in results:
                search_results.append({
                    "title": hit.get("author", "Darknet Post"),
                    "body": hit["content"][:300] + "...",
                    "url": hit["url"],   # synthetische URI, z.B. darknet://forum/post-123
                    "source": "Darknet Forum"
                })
            return search_results
Parallele Suche und Merge mit SearXNG:
Am einfachsten erzeugt man einen CompositeRetriever, der beide Backends parallel abfragt und die Ergebnisse dedupliziert (anhand der URL). In einer benutzerdefinierten CustomSearchTool oder durch Überschreiben der conduct_research‑Methode:

Python

import asyncio

async def composite_search(query: str):
    searx = SearxSearch(query)  # existierende Klasse importieren
    darknet = DarknetRetriever()
    loop = asyncio.get_event_loop()
    res1 = await loop.run_in_executor(None, searx.search, query)
    res2 = darknet.search(query)
    # merge und Dedup anhand URL
    seen = set()
    merged = []
    for r in res1 + res2:
        if r['url'] not in seen:
            seen.add(r['url'])
            merged.append(r)
    return merged[:20]
Zitierfähige synthetische URIs:
Der Crawler generiert pro Post eine ID und speichert sie im Index. Die URL hat die Form darknet://<forum-id>/post/<post_id>. Im GPT‑Researcher‑Report kann diese URL wie jede andere Quelle referenziert werden – sie wird als Link ausgegeben, auch wenn sie nicht im normalen Browser öffnbar ist. Im HTML‑Export kann man einen Hinweis hinzufügen.

4. Lernfähigkeit & Vektordatenbank
Embedding‑Modell (VRAM‑schonend)

nomic‑embed‑text (v1.5, 137 Mio. Parameter) – hervorragende Qualität, sehr klein
Läuft auf der CPU, da die GTX 1070 exklusiv vom LLM belegt wird
Bereitstellung via Ollama:
ollama pull nomic‑embed‑text:latest
ChromaDB‑Konfiguration
In der .env:

Bash

EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION=gpt_researcher
GPT Researcher ruft dann bei jeder „Deep Research“‑Iteration das Embedding‑Modell auf und speichert/liest Vektoren aus ChromaDB. Der gesamte Embedding‑Prozess beansprucht keinen GPU‑Speicher, nur CPU‑RAM.

Speicherengpässe minimieren:

ChromaDB auf der Festplatte (persist_directory) – kein RAM‑Stress
EMBEDDING_BATCH_SIZE klein halten (z. B. 8), um CPU‑Spitzen zu vermeiden
5. Gesamtarchitektur & Konfiguration
Architekturplan
text

┌─────────────┐        ┌──────────────────────┐
│   User      │  HTTP  │  GPT Researcher Web  │
│ (Browser)   ├───────►│  UI / API            │
└─────────────┘        └──────────┬───────────┘
                                  │
                          ┌───────▼────────┐
                          │ Orchestrator    │
                          │ (conduct_res.)  │
                          └───────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼───────┐  ┌───────▼────────┐  ┌───────▼──────┐
     │ Composite Search│  │   LLM (Ollama) │  │ ChromaDB     │
     │ (SearXNG +     │  │ Qwen3.5-9B     │  │ (w/ nomic-   │
     │  Darknet)      │  │ local GPU      │  │ embed-text)  │
     └────────┬───────┘  └───────┬────────┘  └───────▲──────┘
              │                  │                   │
 ┌────────────▼───┐  ┌──────────▼──────────┐        │
 │ SearXNG (Docker)│ │ Tor (SOCKS5 :9050)  │ Embedding│
 └────────┬────────┘ └──────────┬──────────┘ (CPU)    │
          │                     │                     │
 ┌────────▼─────────┐ ┌─────────▼───────────┐         │
 │ Internet (Web)   │ │ Darknet Forum Crawl │         │
 └──────────────────┘ │ + Whoosh Index      │─────────┘
                      └─────────────────────┘
Erforderliche .env‑Anpassungen
Bash

# LLM
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen3.5-9b-uncensored-hauhaucs-aggressive:latest

# Web-Suche
RETRIEVER=custom          # wir nutzen unseren CompositeRetriever
SEARX_URL=http://localhost:8080
SEARX_MAX_RESULTS=10

# Darknet
DARKNET_INDEX_PATH=./darknet_index
DARKNET_ENABLED=true

# Embedding & ChromaDB
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION=gpt_researcher

# Forschungseinstellungen
MAX_SEARCH_RESULTS_PER_QUERY=15
MAX_SUBTOPICS=3
REPORT_SOURCE=web
Wichtig: GPT Researcher erwartet bei RETRIEVER=custom eine entsprechende Implementierung. Der einfachste Weg ist, die bestehende SearxSearch‑Klasse um die Darknet‑Funktionalität zu erweitern oder eine neue, die intern beide anspricht. In gpt_researcher/retrievers/__init__.py kann der benutzerdefinierte Retriever registriert werden.

Schritt‑für‑Schritt‑Fahrplan
Fork von GPT Researcher
git clone https://github.com/assafelovic/gpt-researcher && cd gpt-researcher

Basis‑Umgebung aufsetzen

Bash

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
Ollama installieren & Modell bereitstellen

Ollama installieren
GGUF‑Datei platzieren, Modelfile erstellen, ollama create …
Test: ollama run qwen3.5-9b-uncensored-hauhaucs-aggressive:latest
SearXNG starten

Bash

docker run -d -p 8080:8080 -v ${PWD}/searxng:/etc/searxng searxng/searxng
API‑Erreichbarkeit prüfen: curl http://localhost:8080/search?q=test&format=json

Darknet‑Crawler & Indexer

Python‑Skript schreiben (s. Abschnitt 3.1)
Whoosh‑Index anlegen und initial befüllen
Sicherstellen, dass der Crawler periodisch läuft (z. B. per Cron)
DarknetRetriever implementieren

Datei gpt_researcher/retrievers/darknet/darknet.py anlegen
In gpt_researcher/retrievers/__init__.py importieren und in der Retriever‑Map eintragen
CompositeRetriever bauen

In gpt_researcher/retrievers/custom/custom.py (oder eine neue Klasse) eine search()‑Methode schreiben, die SearxSearch und DarknetRetriever parallel aufruft und merged
In config/config.py sicherstellen, dass bei RETRIEVER=custom diese Klasse geladen wird
ChromaDB und Embedding konfigurieren

.env wie oben setzen
GPT Researcher prüft diese Umgebungsvariablen und verwendet ChromaDB mit Ollama‑Embeddings
Speicher‑Optimierungen für die GTX 1070

In der Modelfile: PARAMETER num_ctx 4096 (reduziert KV‑Cache auf ~1 GB)
PARAMETER num_gpu 35 (oder die Anzahl der GPU‑Layers in Ollama automatisch) – nicht alle Layers auf GPU, falls Modell etwas größer
Ollama starten mit OLLAMA_NUM_PARALLEL=1 (keine parallelen Anfragen)
Im Researcher: MAX_CONCURRENT_REQUESTS=1 setzen, damit immer nur eine LLM‑Anfrage läuft
Embeddings nicht auf die GPU legen (Ollama setzt sie automatisch auf CPU, wenn GPU nicht genug VRAM)
System starten & testen

Alles parallel:
Terminal 1: ollama serve
Terminal 2: docker run ... searxng/searxng
Terminal 3: Darknet‑Crawler/Indexer im Hintergrund
Terminal 4: python -m gpt_researcher --stream (oder uvicorn für die Web‑UI)
Test mit einer harmlosen, aber Darknet‑bezogenen Query, um beide Quellen zu prüfen
6. Rechtliche und technische Risiken
Rechtliche Vorsichtsmaßnahmen

Unzensiertes Modell: Kann Aufforderungen für rechtswidrige Handlungen generieren. Betreiber sind für die Nutzung verantwortlich. Einsatz nur in juristisch einwandfreiem Kontext, ggf. mit zusätzlichen lokalen Filtern für bestimmte Ausgaben.
Crawlen von Darknet‑Seiten: Das Abspeichern und Verarbeiten von Inhalten kann Urheberrechte verletzen oder strafbar sein, wenn es sich um illegale Foren handelt (z. B. mit Kinderpornografie, Waffenhandel). Vorherige rechtliche Prüfung durch einen Fachanwalt ist zwingend. Möglicherweise sind die Daten schon durch den Besitz strafbar. Der gesamte Stack muss in einer Gerichtsbarkeit betrieben werden, die dies erlaubt.
Tor‑Nutzung: In vielen Ländern legal, aber das Betreiben eines Exit‑Nodes oder die Umgehung von Netzsperren kann Probleme verursachen. Wir nutzen Tor nur als Client.
Technische Risiken und Gegenmaßnahmen

Malware aus Darknet‑Inhalten: Der Crawler lädt HTML, das schädliches JavaScript enthalten kann. Der reine Text‑Extractor sollte keine Skripte ausführen. BeautifulSoup/Lxml parsen passiv – ungefährlich. Trotzdem empfiehlt sich ein Container mit minimalem Userspace.
Identitätsdiebstahl / Login: Werden Login‑Daten für das Forum verwendet, sollte ein Wegwerf‑Account genutzt werden. Niemals persönliche Daten mit dem Crawler assoziieren.
Speicherüberlastung bei vielen Posts: Der Whoosh‑Index wächst mit der Zeit. Regelmäßige Komprimierung (ix.optimize()) durchführen.
Isolation: Den gesamten Researcher‑Stack in einem Docker‑Container oder einer VM betreiben, um das Host‑System zu schützen.
Sicherheitslücken in SearXNG: Nur lokal auf 127.0.0.1 lauschen lassen (--publish 127.0.0.1:8080:8080), damit kein Zugriff von außen möglich ist.

