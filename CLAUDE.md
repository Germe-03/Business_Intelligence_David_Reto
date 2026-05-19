# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Flughafen BI Dashboard - Decision-Support-Tool: Welche Piste bei gegebenem Wetter und Flugzeugtyp am Flughafen Zürich? Siehe `AGENTS.md` für die kompakte Projektübersicht und `docs/` für Detailregeln (Clean Arch, TDD, MMI, Schema).

## Befehle

```bash
pip install -r requirements.txt                 # Setup (Python 3.12, .venv vorhanden)
streamlit run dashboard/app.py                  # Dashboard starten
pytest tests/unit/                              # Unit Tests (schnell, kein IO)
pytest tests/integration/                       # Integration Tests (echte DB/CSV)
pytest tests/e2e/                               # E2E Tests (Streamlit läuft)
pytest tests/unit/test_runway_recommendation.py::test_recommends_runway_with_strongest_headwind   # Einzelner Test
pytest --cov=src                                # Coverage
```

Optional: lokales LLM via Ollama (`http://localhost:11434`) für Erklärungen. Fehlt Ollama oder Modell, schaltet `OllamaRunwayExplainer` automatisch auf eine regelbasierte Fallback-Erklärung um (`src/infrastructure/ollama_explainer.py`).

## Architektur (Dependency Rule: nach innen)

```
Infrastructure  →  Interfaces  →  Application  →  Domain
```

Datenfluss für den Haupt-Use-Case (Runway-Empfehlung):

1. `dashboard/runway_view.py` rendert das Streamlit-UI und ruft `RunwayDecisionController` auf (via `@st.cache_resource`).
2. `src/interfaces/runway_controller.py` baut aus UI-Inputs `WeatherCondition` und delegiert an den Use Case.
3. `src/application/recommend_runway.py` (`RecommendRunway`) iteriert über `ZRH_TAKEOFF_RUNWAYS` und sortiert nach `evaluate_runway`-Score.
4. `src/domain/runway.py` ist die Regel-Engine: Wind-Komponentenzerlegung (Head-/Cross-/Tailwind), Aircraft-Limits (`light/medium/heavy`), Penalties (Sicht, Gewitter, Niederschlag), Status `RECOMMENDED/CAUTION/NOT_SUITABLE`. **Pure Python, keine Imports von SQLAlchemy/Streamlit/pandas.**
5. `dashboard/runway_view.py` ruft parallel `BuildOperationalContext` für Wetterhistorie, Aircraft-Profil, Traffic-Load, Booking-Load - geliefert von `DumpOperationalContextRepository` (`src/infrastructure/dump_operational_context.py`), das die `.tsv.zst`-Dumps mit `pandas.read_csv(compression="zstd")` chunkweise liest und mit `@lru_cache` cached.
6. Optional: `OllamaRunwayExplainer` baut aus `RunwayDecisionContext` einen Prompt (`build_runway_explanation_prompt`) und generiert eine Erklärung; bei Fehler liefert `build_fallback_explanation` einen deterministischen Text.

Repository-Ports werden als `typing.Protocol` in `application/` definiert (z.B. `OperationalContextRepository`), Implementierungen liegen in `infrastructure/`.

## Daten

- `Data/flughafendb_large/` - MySQL-Dump als `.tsv.zst`, Spaltennamen in `flughafendb_large@<table>.json` unter `options.columns`. ZRH = `airport_id 13591`.
- `Data/external/` - Zürich FIDS CSVs (Semikolon-getrennt).
  - `arrivals_*.csv`: FLC, FLN, ORG, STA, ETA, ATA, TYS, PAX, RWY, REG
  - `departures_*.csv`: FLC, FLN, DES, STD, ETD, ATD, TYS, PAX, RWY, REG
- `Data/` ist gitignored - Daten kommen vom Dozenten oder David/Reto.
- ZRH Runways (für Empfehlung relevant): `28/280°`, `32/320°`, `34/340°` als Start; siehe `docs/DATA_SCHEMA.md` für vollständiges Mapping.

## Constraints

- `booking` hat 24 Chunks à ~2.3 Mio Zeilen (~55 Mio gesamt) - immer nur Chunk 0 laden (`flughafendb_large@booking@0.tsv.zst`).
- Domain-Schicht (`src/domain/`) darf **nie** SQLAlchemy, Streamlit oder pandas importieren - sonst bricht die Dependency Rule.
- Neue externe Datendateien gehören in `Data/external/`, nicht ins Repo.
- Dashboard-Code (`dashboard/`) muss ISO 9241 einhalten: `docs/MMI_PRINCIPLES.md` konsultieren bevor UI geändert wird (Labels mit Einheiten, keine DB-IDs sichtbar, konsistente Farben).
- TDD: Red → Green → Refactor. Unit-Tests ohne IO, Fake-Repos via Port-Protocols.
