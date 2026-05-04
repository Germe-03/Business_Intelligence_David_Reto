# AGENTS.md – Flughafen BI Dashboard

## WHY
Entscheidungsunterstützendes Dashboard: Welche Piste (Runway) soll bei gegebenem Wetter
für welchen Flugzeugtyp genutzt werden? Datengrundlage: Flughafen-DB (MySQL-Dump)
und Zürich FIDS-Daten (CSV).

## WHAT
- **Sprache:** Python 3.12
- **Architektur:** Clean Architecture (Domain → Application → Interfaces → Infrastructure)
- **ORM:** SQLAlchemy
- **Dashboard:** Streamlit + Plotly
- **ML:** scikit-learn (RandomForest)
- **Tests:** pytest (Unit → Integration → E2E)

## HOW

### Architektur-Regel (Dependency Rule)
Abhängigkeiten zeigen **immer nach innen**:
`Infrastructure → Interfaces → Application → Domain`
Domain kennt keine äusseren Schichten.

### Befehle
```bash
pip install -r requirements.txt          # Setup
streamlit run dashboard/app.py           # Dashboard starten
pytest tests/unit/                       # Unit Tests
pytest tests/integration/                # Integration Tests
pytest tests/e2e/                        # E2E Tests
```

### TDD-Workflow (Red–Green–Refactor)
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
- Architektur-Detail: `docs/CLEAN_ARCH.md`
- Datenbankschema: `docs/DATA_SCHEMA.md`
- TDD-Regeln: `docs/TDD.md`
