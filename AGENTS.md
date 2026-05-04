# AGENTS – Spezialisierte Rollen im BI-Projekt

Dieses Dokument definiert die Agenten-Rollen für das Flughafen-BI-Projekt.
Jeder Agent hat eine klare Verantwortung, bevorzugte Tools und Eingabe/Ausgabe-Schnittstellen.

---

## Agent 1: ETL-Agent
**Verantwortung:** Daten aus der Datenbank und externen Quellen laden und in ein einheitliches Format bringen.

**Eingabe:**
- `Data/flughafendb_large/` – MySQL-Dump (.tsv.zst Dateien)
- `Data/external/` – CSV-Dateien (Zürich FIDS, zukünftige Quellen)

**Ausgabe:**
- Bereinigte DataFrames / SQLite-Tabellen bereit für Analyse und Dashboard
- Fehlerlog bei Ladeproblemen

**Zuständige Dateien:**
- `etl/loader.py` – Lädt .tsv.zst Dateien und CSVs
- `etl/cleaner.py` – Erste Bereinigung (Typen, Encoding, Nullwerte)

**Skill:** `_skills/etl.md`

---

## Agent 2: Data-Quality-Agent
**Verantwortung:** Datenqualitätsprobleme erkennen, dokumentieren und beheben.

**Prüfungen:**
- Fehlende Werte (NULL, NA, leere Strings)
- Duplikate (z.B. Passagier mit gleichem passportno)
- Ausreisser (z.B. Preise < 0, unrealistische ZIP-Codes)
- Referenzielle Integrität (FK-Verletzungen zwischen Tabellen)
- Zeitlogik (departure muss vor arrival liegen)
- Kapazitätsprüfung (Buchungen > airplane.capacity)

**Eingabe:** Bereinigte DataFrames vom ETL-Agent
**Ausgabe:** Quality-Report (pro Tabelle: Anzahl Issues, behobene/offene Probleme)

**Zuständige Dateien:**
- `etl/quality.py`

**Skill:** `_skills/data-quality.md`

---

## Agent 3: Analyse-Agent
**Verantwortung:** SQL-Abfragen und explorative Datenanalyse (EDA) durchführen, um Muster zu erkennen.

**Kernfragen:**
- Welche Routes haben die höchste Auslastung?
- Welche Airlines haben die meisten Flugänderungen (flight_log)?
- Wie korreliert Wetter mit Flugänderungen?
- Welche Passagiere sind Vielfliegter?
- Umsatz pro Airline / Route / Zeitraum?

**Eingabe:** Saubere Datenbank
**Ausgabe:** DataFrames, Charts (plotly), Summary-Tabellen

**Zuständige Dateien:**
- `analysis/eda.py`
- `analysis/queries.sql`

**Skill:** `_skills/analysis.md`

---

## Agent 4: ML-Agent
**Verantwortung:** Vorhersagemodelle trainieren und evaluieren.

**Vorhersage-Ziele:**
1. **Flugverspätung** (Klassifikation: verspätet ja/nein) – aus flight_log + weatherdata
2. **Buchungsauslastung** (Regression: % Auslastung) – aus flight + booking + airplane
3. **Passagierpreis** (Regression: erwarteter Preis) – aus Route + Airline + Wochentag

**Modelle:**
- Baseline: Lineare/Logistische Regression
- Erweitert: Random Forest, Gradient Boosting

**Eingabe:** Feature-DataFrames vom Analyse-Agent
**Ausgabe:** Trainierte Modelle (.pkl), Metriken (Accuracy, RMSE, R²)

**Zuständige Dateien:**
- `models/train.py`
- `models/predict.py`
- `models/evaluate.py`

**Skill:** `_skills/ml.md`

---

## Agent 5: Dashboard-Agent
**Verantwortung:** Streamlit-Dashboard aufbauen und pflegen.

**Dashboard-Seiten:**
1. **Übersicht** – KPIs: Gesamtflüge, Buchungen, Umsatz, Top-Airlines
2. **Routen-Analyse** – Karte (airport_geo), Auslastung pro Route
3. **Verspätungsanalyse** – Flugänderungen aus flight_log, Wetterkorrelation
4. **Passagiere** – Herkunftsland, Altersverteilung, Vielfliegter
5. **Vorhersage** – Eingabe: Route + Datum → Modell-Output

**Eingabe:** Analyse-Ergebnisse + ML-Modelle
**Ausgabe:** Laufende Streamlit-App auf localhost

**Zuständige Dateien:**
- `dashboard/app.py`
- `dashboard/pages/` – eine Datei pro Seite

**Skill:** `_skills/dashboard.md`

---

## Zusammenspiel der Agenten

```
Data/flughafendb_large/  ──►  [ETL-Agent]  ──►  [Data-Quality-Agent]
Data/external/           ──►                           │
                                                       ▼
                                              [Analyse-Agent]
                                               │           │
                                               ▼           ▼
                                          [ML-Agent]  [Dashboard-Agent]
                                               │           │
                                               └─────┬─────┘
                                                     ▼
                                              Streamlit-Dashboard
```
