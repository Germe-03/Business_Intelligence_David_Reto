# Business Intelligence – Flughafen Dashboard

BI-Projekt von David & Reto | Flughafen Zürich Datenanalyse & Vorhersage-Dashboard

## Setup

### 1. Repository klonen
```bash
git clone <repo-url>
cd Business_Intelligence_David_Reto
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
├── etl/                # Datenladen & Bereinigung
├── analysis/           # SQL-Queries & EDA
├── models/             # ML-Modelle
├── dashboard/          # Streamlit-App
└── _skills/            # Dokumentation & Anleitungen
```

Siehe [AGENTS.md](AGENTS.md) für die Rollen der einzelnen Komponenten und [CLAUDE.md](CLAUDE.md) für den vollständigen Projektkontext.
