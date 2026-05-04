# Clean Architecture – Projektspezifisch

## Schichten & Verantwortlichkeiten

### Domain (`src/domain/`)
- Business Entities: `Flight`, `Weather`, `Runway`, `Aircraft`
- Repository Ports (ABCs): `RunwayRepository`, `WeatherRepository`
- **Keine** Imports von SQLAlchemy, pandas, Streamlit

### Application (`src/application/`)
- Use Cases: `RecommendRunway`, `AnalyzeDelay`, `LoadWeatherData`
- Orchestriert Domain Entities via Repository Ports
- Kennt nur `domain/`

### Interfaces (`src/interfaces/`)
- Konkrete Repository-Implementierungen (SQLAlchemy, CSV)
- Streamlit-Controller (Daten aufbereiten für UI)
- Kennt `application/` und `domain/`

### Infrastructure (`src/infrastructure/`)
- SQLAlchemy Engine & Session
- ML-Modell laden/speichern
- CSV-Loader für externe Daten
- Kennt alle inneren Schichten

## Dependency Rule
```
Infrastructure  →  Interfaces  →  Application  →  Domain
(darf importieren)               (darf importieren)  (kennt niemanden)
```
