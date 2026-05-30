# AGENTS.md - Flughafen BI Dashboard

## WHY
Analyse- und Decision-Support-Dashboard für den Flughafen Zürich (ZRH).
Zwei Bereiche: (1) Runway-Empfehlung - welche Piste bei gegebenem Wetter und
Flugzeugtyp? - und (2) BI/OSINT/KI-Auswertungen über Flugbetrieb, Buchungen,
Umsatz und Wetter. Datengrundlage: Flughafen-DB (MySQL-Dump als `.tsv.zst`):
Flüge/Buchungen aus Sommer 2015, `weatherdata` reicht 2005-2015 - plus
Live-Quellen (MeteoSchweiz, OpenSky).

## WHAT
- **Sprache:** Python 3.11 (lokales `.venv` vorhanden)
- **Runway-Empfehlung:** Clean Architecture (Domain -> Application -> Interfaces -> Infrastructure), Datenzugriff via pandas + zstd
- **BI/OSINT/KI:** Streamlit-Module, die DuckDB direkt über die `.tsv.zst`-Dumps abfragen
- **UI:** Streamlit (Multipage) + Plotly; Karten via Folium / Kepler.gl / pydeck
- **LLM:** lokal Ollama (Runway-Erklärung, mit Fallback) und optional OpenAI/Anthropic (KI-Analyst)
- **Tests:** pytest (Unit-Tests decken den Runway-`src/`-Pfad ab)

Hinweis: `sqlalchemy`, `pymysql`, `scikit-learn` und `joblib` stehen in
`requirements.txt`, werden im Code aber aktuell nicht genutzt.

## HOW

### Architektur-Regel (nur Runway-Bereich, `src/`)
Abhängigkeiten zeigen **immer nach innen**:
`Infrastructure -> Interfaces -> Application -> Domain`.
Domain kennt keine äusseren Schichten. Die BI/OSINT/KI-Module in `dashboard/bi/`
und `dashboard/osint/` folgen dieser Regel bewusst nicht - sie fragen DuckDB
direkt aus dem View-Code ab.

### Befehle
```bash
pip install -r requirements.txt          # Setup
streamlit run dashboard/app.py           # Dashboard starten (Multipage)
pytest tests/unit/                       # Unit Tests
pytest tests/integration/                # Integration Tests (aktuell leer)
pytest tests/e2e/                        # E2E Tests (aktuell leer)
```

### TDD-Workflow (Red-Green-Refactor)
1. Test schreiben (schlägt fehl)
2. Minimaler Code der Test besteht
3. Refactor

## SKILLS (on-demand)
| Task | Skill |
|---|---|
| Daten laden (.tsv.zst, CSV) | `skills/etl/SKILL.md` |
| Datenqualität prüfen & bereinigen | `skills/data-quality/SKILL.md` |
| SQL-Abfragen & EDA | `skills/analysis/SKILL.md` |
| Dashboard bauen/erweitern | `skills/dashboard/SKILL.md` |
| ML-Modell trainieren | `skills/ml/SKILL.md` |

## DOCS
- Vollständiger Projektkontext: `CLAUDE.md`
- Architektur-Detail: `docs/CLEAN_ARCH.md`
- Datenbankschema: `docs/DATA_SCHEMA.md`
- TDD-Regeln: `docs/TDD.md`
- MMI / UX-Prinzipien: `docs/MMI_PRINCIPLES.md`

## MMI-REGEL (immer gültig)
Beim Schreiben von Dashboard-Code (`dashboard/`) gilt:
ISO 9241 einhalten -> `docs/MMI_PRINCIPLES.md` laden.
