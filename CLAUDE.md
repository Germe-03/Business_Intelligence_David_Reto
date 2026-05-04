# Flughafen BI Dashboard – Claude Kontext

Siehe AGENTS.md für Architektur-Regeln, Befehle und Skill-Verweise.

## Projektstruktur (Clean Architecture)
```
src/
├── domain/          # Entities: Flight, Weather, Runway, Aircraft (keine Abhängigkeiten)
├── application/     # Use Cases: RunwayRecommendation, DelayAnalysis + Repository Ports
├── interfaces/      # Adapters: Streamlit-Controller, Repository-Implementierungen
└── infrastructure/  # SQLAlchemy Engine, CSV-Loader, ML-Modell-Adapter

dashboard/           # Streamlit App (Presentation Layer)
tests/
├── unit/            # Domain Entities & Use Cases (kein DB, kein IO)
├── integration/     # Repository Ports mit echter DB
└── e2e/             # Vollständige Workflows
skills/              # On-demand Skills (nur laden wenn Task passt)
docs/                # Architektur- und Schema-Dokumentation
Data/                # Lokale Daten (gitignored)
```

## Datenquellen
- `Data/flughafendb_large/` – MySQL-Dump (14 Tabellen, .tsv.zst Format)
- `Data/external/` – Zürich FIDS CSVs (Semikolon-getrennt)
  - `arrivals_*.csv`: Spalten FLC, FLN, ORG, STA, ETA, ATA, TYS, PAX, RWY, REG
  - `departures_*.csv`: Spalten FLC, FLN, DES, STD, ETD, ATD, TYS, PAX, RWY, REG

## Wichtige Constraints
- `booking` hat 24 Chunks – bei Tests immer nur 1 Chunk laden
- Domain-Schicht darf **nie** SQLAlchemy, Streamlit oder pandas importieren
- Neue Datendateien gehören in `Data/external/`
