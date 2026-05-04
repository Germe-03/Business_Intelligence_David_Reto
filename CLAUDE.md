# Business Intelligence – Flughafen Dashboard

**Projekt:** BI-Dashboard Flughafen Zürich
**Team:** David & Reto
**Ziel:** Entscheidungsunterstützendes Dashboard mit Datenkorrektur und Vorhersagen
**Sprache:** Deutsch (Kommentare & Docs), Python (Code)

## Projektstruktur

```
Business_Intelligence_David_Reto/
├── Data/
│   ├── flughafendb_large/      # MySQL-Dump (14 Tabellen, ~55 Mio Buchungen)
│   └── external/               # Zusätzliche Datenquellen (CSVs, neue Daten)
├── etl/                        # Datenladen & Bereinigung
├── analysis/                   # SQL-Queries, EDA, Notebooks
├── models/                     # ML-Modelle für Vorhersagen
├── dashboard/                  # Streamlit-App (Haupt-Dashboard)
├── tests/                      # Tests
└── _skills/                    # Claude-Skills für dieses Projekt
```

## Datenquellen

### Primär: flughafendb_large (MySQL-Dump)
- **airline** – 113 Airlines mit IATA-Code
- **airplane** – ~5'500 Flugzeuge mit Kapazität
- **airplane_type** – 342 Flugzeugtypen
- **airport** – ~13'500 Flughäfen (IATA + ICAO)
- **airport_geo** – Koordinaten & Länder
- **airport_reachable** – Erreichbarkeit (Anzahl Hops)
- **booking** – ~55 Mio Buchungen (flight_id, seat, passenger_id, price)
- **employee** – 1'000 Mitarbeitende (inkl. Department, Salary)
- **flight** – ~758'000 Flüge (Route, Departure, Arrival)
- **flight_log** – Änderungshistorie aller Flüge (old/new Werte)
- **flightschedule** – Wochenplan pro Flugnummer
- **passenger** – ~36'000 Passagiere
- **passengerdetails** – Personaldaten der Passagiere
- **weatherdata** – Wetterdaten (Temp, Wind, Luftdruck, Niederschlag)

### Sekundär: External CSVs (Zürich Flughafen FIDS)
- `arrivals_2007-06-18_2007-06-24.csv` – Ankunftsdaten (Woche 2007)
- `departures_2017-06-19_2017-06-25.csv` – Abflugdaten (Woche 2017)
- Enthält: Gate, Runway, STA/ETA/ATA, Passagieranzahl, Flugzeug-Reg.

## Technologie-Stack
- **Python 3.x** mit pandas, SQLAlchemy, scikit-learn
- **MySQL** – Datenbankserver (lokale Instanz)
- **Streamlit** – Dashboard-Framework
- **plotly** – Visualisierungen

## Skills
- ETL & Datenladepipeline: `_skills/etl.md`
- Datenqualität & Bereinigung: `_skills/data-quality.md`
- Analyse & SQL: `_skills/analysis.md`
- Dashboard (Streamlit): `_skills/dashboard.md`
- ML-Vorhersagen: `_skills/ml.md`

## Agents
Siehe `AGENTS.md` für spezialisierte Agenten-Rollen.

## Wichtige Hinweise
- Die Daten kommen möglicherweise in weiteren Lieferungen – ETL muss erweiterbar sein
- `booking` ist mit 24 Chunks die grösste Tabelle – bei Abfragen immer mit LIMIT testen
- `employee.password` ist MD5-Hash (char 32) – nicht in Analysen verwenden
- `flight_log` enthält old/new-Werte → daraus lassen sich Verspätungen ableiten
- Neue CSV-Dateien gehören in `Data/external/`
