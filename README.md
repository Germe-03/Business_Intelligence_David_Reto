# Business Intelligence – Flughafen Zürich Dashboard

**BI-Projekt von David & Reto**

Ein interaktives Streamlit-Dashboard rund um den Flughafen Zürich (ZRH). Es verbindet
drei Bausteine:

1. **Decision-Support** – ein regelbasiertes Tool, das bei gegebenem Wetter und Flugzeugtyp
   eine **Startbahn-Empfehlung** für Starts ab ZRH gibt.
2. **Business Intelligence** – klassische BI-Auswertungen (Flugbetrieb, Buchungen, Umsatz,
   Wetter, Auslastung) auf einem Flughafen-Datendump (Sommer 2015).
3. **Live- & OSINT-Daten** – aktuelles Wetter (MeteoSchweiz), Live-Flugverkehr (OpenSky)
   und interaktive Karten.

> **Hinweis für die Bewertung:** Die wichtigsten Dinge auf einen Blick finden sich in
> [Was kann das Dashboard?](#-was-kann-das-dashboard-seite-für-seite) und
> [Benötigte API-Keys](#-benötigte-api-keys). Beides lässt sich ohne Code-Lektüre
> nachvollziehen.

---

## Inhalt

- [Schnellstart](#-schnellstart)
- [Was kann das Dashboard? (Seite für Seite)](#-was-kann-das-dashboard-seite-für-seite)
- [Benötigte API-Keys](#-benötigte-api-keys)
- [Wie ist das Projekt aufgebaut?](#-wie-ist-das-projekt-aufgebaut)
- [Datengrundlage](#-datengrundlage)
- [Tests](#-tests)
- [Weiterführende Dokumentation](#-weiterführende-dokumentation)

---

## 🚀 Schnellstart

```bash
# 1. Abhängigkeiten installieren (Python 3.12)
pip install -r requirements.txt

# 2. Daten lokal hinzufügen (siehe Abschnitt "Datengrundlage")
#    Data/flughafendb_large/  und  Data/external/

# 3. Dashboard starten
streamlit run dashboard/app.py
```

Das Dashboard öffnet sich im Browser unter **http://localhost:8501**. Die Navigation
zwischen den Seiten erfolgt über die **linke Seitenleiste**.

> Die Startseite ist direkt die **Runway-Empfehlung** – es gibt bewusst keine
> Begrüssungsseite (Aufgabenangemessenheit, ISO 9241).

---

## 🧭 Was kann das Dashboard? (Seite für Seite)

Alle Seiten sind über die **Seitenleiste links** erreichbar. Hier steht, was jede Seite
zeigt und wo man es findet.

### 1. Runway-Empfehlung (Startseite)
*Seitenleiste: „Runway recommendation"*

Das Kernstück: Welche der ZRH-Startbahnen (**28 / 32 / 34**) eignet sich bei den
aktuellen Bedingungen am besten für einen Start?

- **Eingaben in der Seitenleiste:** Flugzeugtyp, Windgeschwindigkeit, Böen, Windrichtung,
  Sichtweite, Wetterlage, Temperatur, Destination, Abflugstunde, Ansicht (Kompakt/Details).
- **Wetter automatisch vorbelegt:** Über „Wetterzeitpunkt" lassen sich aktuelle
  MeteoSchweiz-Messwerte (Kloten, „Jetzt") oder der lokale Forecast (+1/+2/+3 Stunden)
  laden. Werte bleiben jederzeit manuell überschreibbar (Szenarien).
- **Ergebnis oben:** klare Empfehlung mit Ampelfarbe (grün/orange/rot), Eignungs-Score
  (0–100) und den Windkomponenten **Gegenwind / Seitenwind / Rückenwind**.
- **Im Detailmodus zusätzlich:** Balkendiagramm „Eignung nach Startbahn",
  Kompassrose (Windrichtung vs. Pistenausrichtung), Vergleichstabelle aller Pisten,
  ausformulierte Begründung sowie ein **Datenbank-Kontext** (ähnliche Wetterlagen in
  der Historie, Flugzeugtyp-Profil, Verkehrslast pro Stunde, Auslastung/Booking-Load).
- **KI-Erklärung (Button „Chat" unten rechts):** formuliert die Empfehlung in
  natürlicher Sprache aus – nutzt ein **lokales Ollama-Modell**, fällt ohne Ollama
  automatisch auf eine regelbasierte Erklärung zurück.

> Dies ist ein **Entscheidungsunterstützungs-Tool**, keine operative Freigabe.

### 2. BI-Dashboard
*Seitenleiste: „Bi dashboard"*

Klassische BI-Auswertung mit **gemeinsamen Filtern** in der Seitenleiste
(Datumsbereich, Airline, Flugzeugtyp, Ziel-Flughafen). Fünf Tabs:

| Tab | Inhalt |
|---|---|
| **Übersicht** | Management-KPIs (Flüge, Buchungen, Umsatz, Ø Ticketpreis, Ø Auslastung) plus Trends Flüge/Buchungen/Umsatz pro Tag |
| **Betrieb** | Top-15-Destinationen, Heatmap Wochentag × Stunde, Routen-Weltkarte (Top 25) |
| **Umsatz** | Top-15-Airlines und -Routen nach Umsatz, Passagier-Demografie (Land, Ø Alter, Geschlecht) |
| **Wetter** | Häufigkeit der Wetterlagen, Windrose, Temperatur-/Wind-Tagestrend |
| **Analyse** | Auslastung nach Flugzeugtyp, Flotten-Treemap, Buchungs-Heatmap Wochentag × Stunde |

### 3. KI-Datenanalyst
*Seitenleiste: „Ki analyst"* · **benötigt einen API-Key (siehe unten)**

Fragen in **natürlicher Sprache** stellen (z. B. „Top 5 Routen ab Zürich nach Umsatz im
August 2015"). Ablauf:

1. Das LLM erzeugt eine **SQL-Abfrage** gegen das bekannte Schema.
2. Die Abfrage wird sicherheitsgeprüft (**nur lesend**, kein INSERT/UPDATE/DROP …) und in
   DuckDB ausgeführt.
3. Das LLM formuliert die Antwort auf Deutsch und zeigt die Ergebnistabelle.

Provider (OpenAI **oder** Anthropic), Modell und API-Key werden **in der Seitenleiste**
gesetzt. Vorgeschlagene Beispiel-Fragen erscheinen als Buttons.

### 4. OSINT Live (OpenSky)
*Seitenleiste: „Osint live"*

**Live-Flugverkehr** rund um Zürich (Quelle: OpenSky Network). Karte mit aktuellen
Flugzeugpositionen im wählbaren Radius, Kennzahlen (Flugzeuge im Radius, in der Luft,
am Boden, Länder, Ø Höhe) und Top-Länder. Funktioniert anonym; optionaler OpenSky-Login
für höhere Limits.

### 5. OSINT Map (Folium)
*Seitenleiste: „Osint map"*

Interaktive **Routenkarte** der flugreichsten Verbindungen aus dem Datensatz (Sommer 2015)
mit optionalem **Live-Overlay** der aktuellen Flugzeuge rund um ZRH.

### 6. OSINT Kepler
*Seitenleiste: „Osint kepler"*

3D-Visualisierung der **ZRH-Abflugrouten** (Arcs) plus **Buchungs-Heatmap** mit kepler.gl.
Ist kepler.gl nicht verfügbar, wird automatisch eine pydeck-Ersatzkarte gezeigt.

---

## 🔑 Benötigte API-Keys

Das Dashboard läuft **grösstenteils ohne API-Keys**. Nur der KI-Datenanalyst benötigt
zwingend einen Key. Übersicht:

| Funktion (Seite) | Key nötig? | Woher / Eingabe |
|---|---|---|
| **KI-Datenanalyst** (Ki analyst) | **Ja – erforderlich** | **OpenAI** *oder* **Anthropic** API-Key. Eingabe direkt in der **Seitenleiste der Seite** (Passwortfeld). Wird **nur** im Session-Speicher gehalten, nicht gespeichert. |
| **Wetter** (Runway-Seite) | Nein | MeteoSchweiz Open Data (öffentlich, kein Key). |
| **KI-Erklärung** (Runway-Seite, „Chat") | Nein | Lokales **Ollama** unter `http://localhost:11434` (optional). Ohne Ollama: automatische regelbasierte Erklärung. |
| **OSINT Live / Map** (OpenSky) | Optional | Funktioniert anonym (gedrosselt). Optionaler OpenSky-Benutzername/-Passwort in der Seitenleiste für höhere Limits. |
| **BI-Dashboard, OSINT Kepler** | Nein | Rein auf dem lokalen Datendump. |

**Kurzfassung für die Bewertung:**
- Zum Ausprobieren des KI-Analysten einen eigenen **OpenAI-** oder **Anthropic-Key**
  bereithalten und auf der Seite „Ki analyst" in der Seitenleiste eintragen.
- Standard-Modelle: OpenAI `gpt-4o-mini`, Anthropic `claude-haiku-4-5` (in der Seitenleiste
  umstellbar).
- Optional lokal: **Ollama** (z. B. `ollama pull llama3.2`) für die KI-Erklärung auf der
  Runway-Seite.
- Alle anderen Seiten sind ohne Key voll nutzbar.

---

## 🏗 Wie ist das Projekt aufgebaut?

### Technologie-Stack
- **Sprache:** Python 3.12
- **Dashboard:** Streamlit (Multipage) + Plotly
- **Datenzugriff:** DuckDB (BI-Views direkt auf `.tsv.zst`) und pandas (Runway-Kontext) –
  **kein ORM**, die komprimierten Dumps werden direkt gelesen
- **Karten:** Folium, kepler.gl, pydeck
- **KI:** OpenAI / Anthropic (Cloud, KI-Analyst) und Ollama (lokal, Runway-Erklärung)
- **Tests:** pytest (Unit → Integration → E2E)

### Architektur: Clean Architecture
Die Geschäftslogik der Runway-Empfehlung ist nach **Clean Architecture** geschichtet.
Abhängigkeiten zeigen **immer nach innen** – die Domain kennt keine äusseren Schichten:

```
Infrastructure  →  Interfaces  →  Application  →  Domain
 (DB, Wetter,       (Controller,    (Use Cases,     (reine
  Ollama)            View-Modelle)   Ports)          Regel-Engine)
```

```
src/
├── domain/          # Regel-Engine: Windkomponenten, Limits, Score (pure Python, keine IO-Imports)
├── application/     # Use Cases (RecommendRunway, BuildOperationalContext) + Ports (Protocols)
├── interfaces/      # RunwayDecisionController, View-Modelle für das UI
└── infrastructure/  # Daten-Repos (.tsv.zst), MeteoSchweiz-Client, Ollama-Client
dashboard/           # Streamlit-App (UI), getrennt von der Logik
├── app.py           # Einstieg (rendert die Runway-Seite)
├── pages/           # Die 6 Seiten der Seitenleiste
├── bi/              # BI-Dashboard + KI-Analyst (DuckDB-Layer)
└── osint/           # OpenSky-Client + Kartenansichten
```

**Datenfluss der Runway-Empfehlung (vereinfacht):**
UI-Eingaben (`dashboard/runway_view.py`) → Controller (`src/interfaces`) baut ein
`WeatherCondition` → Use Case (`src/application`) bewertet alle Startbahnen → Regel-Engine
(`src/domain`) berechnet Wind-Komponenten, Limits und Score → Ergebnis zurück ans UI.
Parallel liefert das Infrastructure-Repository den Datenbank-Kontext aus den Dumps.

Mehr Details: [`docs/CLEAN_ARCH.md`](docs/CLEAN_ARCH.md). Entwickelt wurde nach **TDD**
(Red → Green → Refactor, siehe [`docs/TDD.md`](docs/TDD.md)); das UI folgt den
**MMI-/ISO-9241-Prinzipien** aus [`docs/MMI_PRINCIPLES.md`](docs/MMI_PRINCIPLES.md).

---

## 📦 Datengrundlage

Die Datendateien sind **nicht im Repository** (zu gross für Git) und müssen lokal
hinzugefügt werden. Sie erhältst du vom Dozenten oder von David/Reto.

**Wohin?** Lege im **Wurzelverzeichnis des Projekts** (auf gleicher Ebene wie `dashboard/`
und `src/`) einen Ordner `Data/` an und kopiere die Dump-Dateien **direkt** in die
folgenden Unterordner:

```
Business_Intelligence_David_Reto/   ← Projekt-Wurzel (hier liegt auch README.md)
├── dashboard/
├── src/
└── Data/                            ← diesen Ordner selbst anlegen
    ├── flughafendb_large/           ← hier alle .tsv.zst + .json des MySQL-Dumps ablegen
    │   ├── flughafendb_large@flight@@0.tsv.zst
    │   ├── flughafendb_large@booking@0.tsv.zst
    │   ├── flughafendb_large@weatherdata@@0.tsv.zst
    │   ├── ...   (weitere Tabellen)
    │   └── flughafendb_large@<table>.json   (Spaltennamen)
    └── external/                    ← Zürich FIDS CSVs (Ankünfte/Abflüge, semikolon-getrennt)
```

Der Pfad `Data/flughafendb_large/` ist im Code fest erwartet (siehe
`src/infrastructure/dump_operational_context.py` und `dashboard/bi/data_layer.py`) –
also genau so benennen.

- **Datenstand:** Sommer 2015 (Juni–September), Flughafen Zürich (`airport_id = 13591`).
- Spaltennamen stehen in `flughafendb_large@<table>.json` (Schlüssel `options.columns`).
- Die `booking`-Tabelle hat 24 Chunks (~55 Mio. Zeilen); der Runway-Kontext nutzt
  bewusst nur Chunk 0, DuckDB aggregiert für die BI-Views alle Chunks on the fly.

Vollständiges Schema-Mapping: [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md).

---

## ✅ Tests

```bash
pytest tests/unit/          # schnelle Unit-Tests (ohne IO, Fake-Repos)
pytest tests/integration/   # Integrationstests (echte DB/CSV nötig)
pytest tests/e2e/           # End-to-End (Streamlit läuft)
pytest --cov=src            # Coverage
```

Die Unit-Tests laufen ohne die grossen Datendateien.

---

## 📚 Weiterführende Dokumentation

| Thema | Datei |
|---|---|
| Kompakte Projektübersicht (für Agenten/Tools) | [`AGENTS.md`](AGENTS.md) |
| Clean-Architecture-Details | [`docs/CLEAN_ARCH.md`](docs/CLEAN_ARCH.md) |
| Datenbankschema | [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md) |
| TDD-Regeln | [`docs/TDD.md`](docs/TDD.md) |
| MMI / UX-Prinzipien (ISO 9241) | [`docs/MMI_PRINCIPLES.md`](docs/MMI_PRINCIPLES.md) |
