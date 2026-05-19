# TDD-Regeln

## Ziel von Tests
Tests ermoeglichen einen schnellen Regression-Check: Nach einer Aenderung soll sofort sichtbar
sein, ob alte Features noch funktionieren oder ob etwas kaputt gemacht wurde. Tests sind damit
ein Sicherheitsnetz fuer das Dashboard, die Entscheidungslogik und die Datenanbindung.

## Red-Green-Refactor
1. **Red** - Test schreiben, der fehlschlaegt
2. **Green** - Minimalen Code schreiben, damit der Test besteht
3. **Refactor** - Code aufraeumen, ohne Tests zu brechen

## Testing Pyramid
```
        [E2E]           tests/e2e/          - Vollstaendige Streamlit-Workflows
       [Integration]    tests/integration/  - Repository Ports mit echter DB/API/CSV
      [Unit]            tests/unit/         - Domain Entities & Use Cases ohne IO
```

## Regeln
- Unit-Tests: kein DB-Zugriff, kein File-IO, kein Live-Netzwerk.
- Application-Tests: Fake-Repositories via Port-Protocols verwenden.
- Infrastructure-Tests: Parser und Mapping mit kleinen Fixtures pruefen.
- Dashboard-Tests: Streamlit `AppTest` fuer Smoke-Checks und wichtige UI-Zustaende verwenden.
- E2E-Tests: nur fuer zentrale Nutzerfluesse, weil sie langsamer und fragiler sind.

## Schneller Regression-Check
```bash
python -m py_compile <geaenderte python dateien>
pytest tests/unit/
```

## Erweiterter Check
```bash
pytest tests/integration/
pytest tests/e2e/
pytest --cov=src
```

Der erweiterte Check ist Pflicht, wenn DB-Zugriff, CSV-Lader, Streamlit-Workflows oder mehrere
Schichten gemeinsam betroffen sind und die lokalen Daten/Services verfuegbar sind.
