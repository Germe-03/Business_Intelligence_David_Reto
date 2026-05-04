# TDD-Regeln

## Red–Green–Refactor
1. **Red** – Test schreiben der fehlschlägt
2. **Green** – Minimaler Code der Test besteht
3. **Refactor** – Code aufräumen ohne Tests zu brechen

## Testing Pyramid
```
        [E2E]           tests/e2e/      – Vollständige Streamlit-Workflows
       [Integration]    tests/integration/ – Repository Ports mit echter DB
      [Unit]            tests/unit/     – Domain Entities & Use Cases (kein IO)
```

## Regeln
- Unit Tests: **kein** DB-Zugriff, **kein** File-IO → Fake-Repositories via Port-ABCs
- Integration Tests: echte DB-Verbindung, echter CSV-Loader
- E2E Tests: Streamlit app läuft, Eingabe → Output korrekt

## Befehle
```bash
pytest tests/unit/           # schnell, kein IO
pytest tests/integration/    # braucht DB
pytest tests/e2e/            # braucht laufende App
pytest --cov=src             # Coverage Report
```
