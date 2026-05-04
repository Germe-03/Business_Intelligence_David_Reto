# SKILL: Datenqualität

## Trigger
Wenn Datenqualitätsprobleme geprüft oder behoben werden sollen.

## Prüfliste pro Tabelle
- **flight**: departure < arrival, from ≠ to
- **booking**: price > 0, bookings ≤ airplane.capacity
- **weatherdata**: temp (-60/+60), humidity (0-100), wind (≥ 0)
- **passengerdetails / employee**: zip plausibel, birthdate → Alter 0–120
- **flight_log**: Verspätung = departure_new - departure_old

## Standard-Checks
```python
def quality_report(df, name):
    return {"table": name, "rows": len(df),
            "nulls": df.isnull().sum().to_dict(),
            "duplicates": df.duplicated().sum()}

def check_time_logic(df, start, end):
    return df[df[start] >= df[end]]
```

## Output
Ergebnis als `docs/quality_report.csv` speichern.
