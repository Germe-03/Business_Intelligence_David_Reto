# SKILL: Analyse & SQL

## Trigger
Wenn SQL-Abfragen geschrieben oder explorative Analysen durchgeführt werden.

## Kern-Queries

### Runway-Nutzung nach Wetter (aus CSVs + weatherdata)
```sql
SELECT w.weather, w.winddirection, arr.RWY, COUNT(*) as flights
FROM arrivals arr
JOIN weatherdata w ON DATE(arr.STA) = w.log_date
GROUP BY w.weather, w.winddirection, arr.RWY
ORDER BY flights DESC;
```

### Verspätung aus flight_log
```sql
SELECT flight_id,
       TIMESTAMPDIFF(MINUTE, departure_old, departure_new) AS delay_min
FROM flight_log WHERE departure_new > departure_old;
```

## CSV-Spalten (Zürich FIDS)
- Arrivals: FLC, FLN, ORG, STA, ETA, ATA, TYS, PAX, RWY, REG
- Departures: FLC, FLN, DES, STD, ETD, ATD, TYS, PAX, RWY, REG
- Verspätung Ankunft: ATA - STA | Abflug: ATD - STD
