# Skill: Datenqualität & Bereinigung

## Zweck
Systematische Prüfung und Behebung von Datenqualitätsproblemen in der Flughafendatenbank.

## Bekannte Qualitätsprobleme (zu prüfen)

### booking
- `price` – Ausreisser (negativ, > 50'000?)
- `seat` – NULL-Werte erlaubt, aber Format prüfen (z.B. "12A")
- Buchungen > Flugzeugkapazität (JOIN mit airplane.capacity)

### employee
- `zip` ist smallint – kann negative oder unrealistische Werte enthalten
- `password` ist MD5-Hash (char 32) – nicht für Analyse verwenden
- `emailaddress` – Format prüfen

### passengerdetails
- `zip` – gleiche Problematik wie employee
- `birthdate` – Alter berechnen, unrealistische Werte prüfen (< 0 oder > 120 Jahre)
- `sex` – nur 'M', 'F' oder NULL erlaubt

### flight
- `departure` muss vor `arrival` liegen
- `from` darf nicht gleich `to` sein

### flight_log
- Zeitstempel-Konsistenz (log_date, departure_old/new)
- Daraus Verspätung berechnen: `departure_new - departure_old`

### weatherdata
- `temp` – Plausibilitätsprüfung (-60 bis +60°C)
- `humidity` – 0 bis 100%
- `airpressure` – 900 bis 1100 hPa
- `wind` – keine negativen Werte

## Standard-Prüfroutinen
```python
def quality_report(df, table_name):
    report = {
        'table': table_name,
        'rows': len(df),
        'nulls': df.isnull().sum().to_dict(),
        'duplicates': df.duplicated().sum(),
    }
    return report

def check_date_logic(df, start_col, end_col):
    invalid = df[df[start_col] >= df[end_col]]
    return invalid
```

## Output
Qualitätsprobleme werden in `analysis/quality_report.csv` dokumentiert.
