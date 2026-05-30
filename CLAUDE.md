# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Flughafen BI Dashboard - Decision-Support- und Analyse-Tool für den Flughafen Zürich (ZRH). Es vereint zwei Welten: eine **Runway-Empfehlung** (welche Piste bei gegebenem Wetter und Flugzeugtyp?) nach Clean Architecture und ein **BI-/OSINT-/KI-Dashboard** direkt auf Streamlit + DuckDB. Diese Trennung ist der wichtigste Kontext - Details unten.

`AGENTS.md`, `README.md` und `docs/` geben kompakten Zusatzkontext. Bei Widerspruch zwischen Doku und Code gilt der Code.

## Befehle

```bash
pip install -r requirements.txt                 # Setup (Python 3.11, .venv vorhanden)
streamlit run dashboard/app.py                  # Dashboard starten (Multipage, Seiten in dashboard/pages/)
pytest tests/unit/                              # Unit Tests (schnell, kein IO)
pytest tests/integration/                       # Integration Tests (angelegt, aktuell leer)
pytest tests/e2e/                               # E2E Tests (angelegt, aktuell leer)
pytest tests/unit/test_runway_recommendation.py::test_recommends_runway_with_strongest_headwind   # Einzelner Test
pytest --cov=src                                # Coverage
```

Kein Linter/Formatter im Repo konfiguriert; pytest ist die einzige Tooling-Wahrheit. Optional: lokales LLM via Ollama (`http://localhost:11434`) für Runway-Erklärungen.

## Zwei getrennte Welten (wichtigster Kontext)

1. **Runway-Empfehlung** - Clean Architecture in `src/` (Domain -> Application -> Interfaces -> Infrastructure), pandas-basierter Datenzugriff, Domain/Application unit-getestet. UI: `dashboard/runway_view.py`.
2. **BI / OSINT / KI** - pragmatische Streamlit-Module in `dashboard/bi/` und `dashboard/osint/`, die DuckDB **direkt aus dem View-Code** abfragen. Keine Clean-Arch-Schichten, keine Tests.

Nicht vermischen: BI-Code nicht in `src/` zwingen oder in Clean-Arch refactoren; die Runway-Domain nicht mit DuckDB/pandas/Streamlit verunreinigen.

## App-Struktur (Multipage)

`dashboard/app.py` ist der Einstieg und rendert die Runway-Seite; die echte Navigation liegt in `dashboard/pages/`:
`1_runway_recommendation` (Runway), `2_bi_dashboard` (BI mit fünf Analyse-Tabs), `3_ki_analyst` (NL-Abfrage), `4_osint_live` (OpenSky), `5_osint_map` (Folium-Routen), `6_osint_kepler` (Kepler.gl).

## Architektur Welt 1: Runway-Empfehlung (Dependency Rule: nach innen)

```
Infrastructure  ->  Interfaces  ->  Application  ->  Domain
```

1. `dashboard/runway_view.py` rendert das UI und ruft `RunwayDecisionController` (via `@st.cache_resource`).
2. `src/interfaces/runway_controller.py` baut aus UI-Inputs `WeatherCondition` und delegiert an `RecommendRunway`.
3. `src/application/recommend_runway.py` iteriert über `ZRH_TAKEOFF_RUNWAYS` und sortiert nach `evaluate_runway`-Score.
4. `src/domain/runway.py` ist die Regel-Engine: Wind-Komponentenzerlegung (Head-/Cross-/Tailwind), Aircraft-Limits (`light/medium/heavy`), Penalties (Sicht, Gewitter, Niederschlag, Böen), Status `RECOMMENDED/CAUTION/NOT_SUITABLE`. **Pure Python, keine Imports von SQLAlchemy/Streamlit/pandas.**
5. Parallel lädt `runway_view` über `BuildOperationalContext` und `LoadOperationalSelectionOptions` den DB-Kontext (Wetterhistorie, Aircraft-Profil, Traffic-Load, Booking-Load) aus `DumpOperationalContextRepository` (`src/infrastructure/dump_operational_context.py`): pandas `read_csv(compression="zstd")`, chunkweise, `@lru_cache`.
6. Live-Wetter: `src/infrastructure/meteoswiss_weather.py` (`fetch_live_weather`, Station KLO) belegt die Sidebar-Eingaben vor.
7. Optional: `OllamaRunwayExplainer` baut aus `RunwayDecisionContext` einen Prompt (`build_runway_explanation_prompt`); fehlt Ollama/Modell, liefert `build_fallback_explanation` deterministischen Text. Das Modell wird automatisch als zuletzt installiertes lokales Ollama-Modell gewählt.

Repository-Ports sind `typing.Protocol` in `application/` (z.B. `OperationalContextRepository`), Implementierungen in `infrastructure/`. (`meteoswiss_weather` und `ollama_explainer` werden direkt aufgerufen, ohne Port.)

## Architektur Welt 2: BI / OSINT / KI (Streamlit + DuckDB)

- `dashboard/bi/data_layer.py`: DuckDB in-memory, ein `CREATE VIEW` pro Tabelle über die `.tsv.zst`-Files (`read_csv(..., compression='zstd')`). Connection ist `@st.cache_resource`-geteilt, `query_df` ist `@st.cache_data`. Booking via Glob `@*` = **alle 24 Chunks**, gestreamt (nicht in RAM geladen). Spalten sind in `_COLUMN_TYPES` hartcodiert; `from`/`to` heissen hier `from_id`/`to_id`. Fehlt eine Datei oder ist sie leer, fällt das Modul auf eine leere View zurück.
- `dashboard/bi/filters.py`: `BIFilter` -> SQL-WHERE-Fragmente, für alle Tabs gleich.
- `dashboard/bi/views.py`: fünf Analyse-Tabs (Übersicht/Betrieb/Umsatz/Wetter/Analyse).
- `dashboard/bi/ai_agent.py` (KI-Analyst): NL -> LLM generiert **eine** SQL (`_sanitize_sql`: nur SELECT/WITH, kein DDL/DML) -> DuckDB -> LLM erklärt das Ergebnis. Provider OpenAI **oder** Anthropic; den API-Key gibt der Nutzer in der Sidebar ein, er lebt nur im Session-State und wird nicht persistiert.
- `dashboard/osint/`: OpenSky-Live (`opensky.py`, 30s-Cache), Folium-Routenkarte und Kepler.gl-Heatmap (`views.py`, mit pydeck-Fallback). Optionale Pakete (folium, keplergl) degradieren mit Hinweis statt Crash.

## Daten

- `Data/flughafendb_large/` - MySQL-Dump als `.tsv.zst` (Tab-getrennt, `header=False`, `nullstr=\N`). **Flüge/Buchungen: Sommer 2015 (Juni-September); `weatherdata` reicht dagegen von 2005 bis 2015.** ZRH = `airport_id 13591`. `flight_log` ist im Dump leer.
- Datei-Konvention: Einzeltabellen `flughafendb_large@<table>@@0.tsv.zst` (doppeltes `@@`); ohne Chunk-Suffix `airport_geo`, `airport_reachable`, `flight_log`; `booking` in 24 Chunks `flughafendb_large@booking@<N>.tsv.zst` (`N=0..23`). Jede `.tsv.zst` hat eine `.idx`-Datei.
- Spaltennamen: pandas-Pfad liest sie aus `flughafendb_large@<table>.json` (`options.columns`), DuckDB-Pfad hat sie in `_COLUMN_TYPES` hartcodiert.
- **Zwei Datenzugriffe mit unterschiedlichen Spaltennamen:** pandas-Pfad (Runway) behält roh `from`/`to` und liest nur Booking-Chunk 0; DuckDB-Pfad (BI/OSINT/KI) nutzt `from_id`/`to_id` und streamt alle Chunks. SQL/Logik nicht zwischen den Pfaden kopieren.
- `Data/external/` - Zürcher FIDS-CSVs (semikolongetrennt, Schema in `docs/DATA_SCHEMA.md`); aktuell leer und im Code nicht verdrahtet.
- `Data/` ist gitignored. ZRH-Startbahnen für die Empfehlung: `28/280°`, `32/320°`, `34/340°`; vollständiges Mapping in `docs/DATA_SCHEMA.md`.

## Externe Dienste

- **MeteoSchweiz STAC** (Open Data, Station KLO) - Live-Wetter für die Runway-Seite.
- **OpenSky Network** - Live-Flugpositionen rund um ZRH (anonym gedrosselt, optionaler Login).
- **OpenAI / Anthropic** - nur KI-Analyst, Key vom Nutzer (Session-State).
- **Ollama** (`localhost:11434`) - nur lokale Runway-Erklärung, mit Fallback.

## Constraints

- Domain-Schicht (`src/domain/`) darf **nie** SQLAlchemy, Streamlit oder pandas importieren.
- Booking-Regel ist pfadabhängig: im pandas-Pfad **nur Chunk 0** (`@booking@0`, sonst werden ~55 Mio. Zeilen geladen); der DuckDB-Pfad streamt bewusst alle Chunks via `@*`-Glob - das **nicht** auf Chunk 0 "korrigieren".
- Dashboard-Code (`dashboard/`) muss ISO 9241 einhalten: `docs/MMI_PRINCIPLES.md` vor UI-Änderungen lesen (Labels mit Einheiten, keine DB-IDs sichtbar, konsistente Farben/Status).
- TDD (Red -> Green -> Refactor), Unit-Tests ohne IO mit Fake-Repos via Port-Protocols. **Tests decken nur den Runway-`src/`-Pfad ab; `dashboard/bi` und `dashboard/osint` (DuckDB) sind ungetestet.** `tests/integration` und `tests/e2e` sind leer.
- Neue externe Datendateien gehören nach `Data/external/`, nicht ins Repo.
