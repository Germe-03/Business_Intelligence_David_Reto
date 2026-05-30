# Clean Architecture - Projektspezifisch

Gilt für den **Runway-Bereich** (`src/`). Die BI/OSINT/KI-Module in
`dashboard/bi/` und `dashboard/osint/` folgen Clean Architecture bewusst nicht -
sie fragen DuckDB direkt aus dem View-Code ab.

## Schichten & Verantwortlichkeiten

### Domain (`src/domain/`)
- Entities / Value Objects: `Runway`, `WeatherCondition`, `AircraftLimits`, `RunwaySuitability`
- Regel-Engine `evaluate_runway` (Wind-Komponenten, Aircraft-Limits, Penalties, Status)
- **Keine** Imports von SQLAlchemy, pandas, Streamlit

### Application (`src/application/`)
- Use Cases: `RecommendRunway`, `BuildOperationalContext`, `LoadOperationalSelectionOptions`
- Repository-Ports als `typing.Protocol` (z.B. `OperationalContextRepository`)
- Erklärungs-Bausteine: `RunwayDecisionContext`, `build_runway_explanation_prompt`, `build_fallback_explanation`
- Kennt nur `domain/`

### Interfaces (`src/interfaces/`)
- Streamlit-Controller, der Domain-Ergebnisse für die UI aufbereitet (`RunwayDecisionController` + View-Dataclasses)
- Kennt `application/` und `domain/`

### Infrastructure (`src/infrastructure/`)
- `DumpOperationalContextRepository`: liest die `.tsv.zst`-Dumps mit pandas (`compression='zstd'`), chunkweise, `@lru_cache`
- `meteoswiss_weather`: Live-Wetter über MeteoSchweiz STAC (Station KLO)
- `ollama_explainer`: lokale LLM-Erklärung mit regelbasiertem Fallback
- Kennt alle inneren Schichten

## Dependency Rule
```
Infrastructure  ->  Interfaces  ->  Application  ->  Domain
(darf importieren)                                  (kennt niemanden)
```
