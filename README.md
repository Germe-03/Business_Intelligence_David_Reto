# Business Intelligence – Flughafen Dashboard

BI-Projekt von David & Reto | Flughafen Zürich Datenanalyse & Vorhersage-Dashboard

## Setup

### 1. Repository klonen
```bash
git clone <repo-url>
cd gpa_bis
```

### 2. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 3. Datenbank manuell hinzufügen

Die Datenbankdateien sind **nicht im Repository enthalten** (zu gross für Git).

Ordnerstruktur manuell anlegen:
```
Data/
├── flughafendb_large/     ← Inhalt des MySQL-Dumps hier einfügen
└── external/              ← CSV-Dateien hier ablegen
```

Die Daten erhältst du vom Dozenten oder direkt von David/Reto.

### 4. Dashboard starten
```bash
streamlit run dashboard/app.py
```

## Projektstruktur

```
├── Data/               # Lokale Daten (nicht im Git)
├── dashboard/          # Streamlit-App (Runway, BI, OSINT, KI - Multipage)
├── src/                # Clean-Architecture-Code der Runway-Empfehlung
├── tests/              # pytest (unit / integration / e2e)
├── docs/               # Detailregeln (Clean Arch, TDD, MMI, Schema)
├── skills/             # On-demand-Anleitungen (etl, analysis, data-quality, dashboard, ml)
└── models/             # ML-Modelle (aktuell leer)
```

Siehe [AGENTS.md](AGENTS.md) für die Rollen der einzelnen Komponenten und [CLAUDE.md](CLAUDE.md) für den vollständigen Projektkontext.
