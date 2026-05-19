# SKILL: Testing und Regression

## Trigger
Immer laden, wenn ein neues Feature implementiert wird, bestehendes Verhalten geaendert wird,
ein Bugfix gemacht wird oder ein Refactor Logik beruehrt. Dieser Skill wird zusaetzlich zum
fachlichen Skill geladen, z.B. Dashboard + Testing oder ML + Testing.

## Ziel
Tests sollen schnell zeigen, ob alte Features noch funktionieren oder ob durch eine Aenderung
etwas kaputt gemacht wurde. Sie sind ein Sicherheitsnetz fuer Regressionen, nicht nur ein
Nachweis, dass neuer Code einmal laeuft.

## Grundregeln
- Schnelle Tests zuerst: gezielte Unit-Tests, danach der passende groessere Testumfang.
- Neue Logik bekommt mindestens einen Test fuer den normalen Fall und einen relevanten Randfall.
- Tests muessen deterministisch sein: kein Live-Netzwerk in Unit-Tests, keine Uhrzeit ohne Fixierung,
  keine echte DB in Unit-Tests.
- Externe APIs mit kleinen Beispielantworten testen; Live-Calls nur als manuelle oder Integration-Pruefung.
- Tests sollen Verhalten pruefen, nicht private Implementierungsdetails.
- Wenn ein Test nicht sinnvoll automatisierbar ist, den manuellen Pruefschritt konkret dokumentieren.

## Testauswahl nach Schicht
- `src/domain/`: Unit-Tests ohne IO. Regeln, Grenzwerte und Fehlfaelle direkt testen.
- `src/application/`: Unit-Tests mit Fake-Repositories oder Protocol-Stubs.
- `src/infrastructure/`: Parser und Mapping mit Fixtures testen; echte DB/API nur Integration.
- `dashboard/`: Streamlit `AppTest` als Smoke-Test verwenden; wichtige UI-Zustaende pruefen.
- `tests/e2e/`: Nur fuer zentrale Nutzerfluesse oder wenn mehrere Schichten gemeinsam brechen koennen.

## Schneller Standard-Check
```bash
python -m py_compile <geaenderte python dateien>
pytest tests/unit/
```

## Erweiterter Check
```bash
pytest tests/integration/
pytest tests/e2e/
```

Nur laufen lassen, wenn die Aenderung DB, CSV-Lader, Streamlit-Flows oder mehrere Schichten
beruehrt und die benoetigten lokalen Daten/Services verfuegbar sind.

## Abschluss
Im finalen Bericht immer nennen:
- welche Tests neu oder angepasst wurden
- welche Befehle gelaufen sind
- welche Pruefung nicht moeglich war und warum
