# AGENTS.md - Flughafen BI Dashboard

## WHY
Entscheidungsunterstuetzendes Dashboard: Welche Piste (Runway) soll bei gegebenem Wetter
fuer welchen Flugzeugtyp genutzt werden? Datengrundlage: Flughafen-DB (MySQL-Dump)
und Zuerich FIDS-Daten (CSV).

## WHAT
- **Sprache:** Python 3.12
- **Architektur:** Clean Architecture (Domain -> Application -> Interfaces -> Infrastructure)
- **Datenzugriff:** Direkte Reads der `.tsv.zst`-Dumps via pandas (Runway-Kontext) und DuckDB (BI-Views) - kein ORM
- **Dashboard:** Streamlit + Plotly
- **ML:** scikit-learn (RandomForest) - geplant, noch nicht implementiert
- **Tests:** pytest (Unit -> Integration -> E2E)

## HOW

### Architektur-Regel (Dependency Rule)
Abhaengigkeiten zeigen **immer nach innen**:
`Infrastructure -> Interfaces -> Application -> Domain`
Domain kennt keine aeusseren Schichten.

### Befehle
```bash
pip install -r requirements.txt          # Setup
streamlit run dashboard/app.py           # Dashboard starten
pytest tests/unit/                       # Unit Tests
pytest tests/integration/                # Integration Tests
pytest tests/e2e/                        # E2E Tests
```

### TDD-Workflow (Red-Green-Refactor)
1. Test schreiben (schlaegt fehl)
2. Minimaler Code der Test besteht
3. Refactor

## SKILLS (on-demand)
| Task | Skill |
|---|---|
| Daten laden (.tsv.zst, CSV) | `skills/etl/SKILL.md` |
| Datenqualitaet pruefen & bereinigen | `skills/data-quality/SKILL.md` |
| SQL-Abfragen & EDA | `skills/analysis/SKILL.md` |
| Dashboard bauen/erweitern | `skills/dashboard/SKILL.md` |
| ML-Modell trainieren | `skills/ml/SKILL.md` |
| Neues Feature, Bugfix oder Refactor absichern | `skills/testing/SKILL.md` |

## DOCS
- Architektur-Detail: `docs/CLEAN_ARCH.md`
- Datenbankschema: `docs/DATA_SCHEMA.md`
- TDD-Regeln: `docs/TDD.md`
- MMI / UX-Prinzipien: `docs/MMI_PRINCIPLES.md`

## MMI-REGEL (immer gueltig)
Beim Schreiben von Dashboard-Code (`dashboard/`) gilt:
ISO 9241 einhalten -> `docs/MMI_PRINCIPLES.md` laden.

## TEST-REGEL (immer bei Features)
Wenn ein neues Feature implementiert, bestehendes Verhalten geaendert, ein Bugfix gemacht
oder Logik refactored wird, gilt zusaetzlich:
`skills/testing/SKILL.md` laden und mindestens den schnellen Regression-Check ausfuehren.
