# Skill: Analyse & SQL

## Zweck
Standard-Abfragen und EDA-Muster für die Flughafendatenbank.

## Kern-KPIs für das Dashboard

### Auslastung pro Flug
```sql
SELECT f.flight_id, f.flightno,
       COUNT(b.booking_id) AS bookings,
       a.capacity,
       ROUND(COUNT(b.booking_id) / a.capacity * 100, 1) AS occupancy_pct
FROM flight f
JOIN airplane a ON f.airplane_id = a.airplane_id
LEFT JOIN booking b ON f.flight_id = b.flight_id
GROUP BY f.flight_id, a.capacity;
```

### Umsatz pro Airline
```sql
SELECT al.airlinename, SUM(b.price) AS revenue, COUNT(b.booking_id) AS bookings
FROM booking b
JOIN flight f ON b.flight_id = f.flight_id
JOIN airline al ON f.airline_id = al.airline_id
GROUP BY al.airline_id
ORDER BY revenue DESC;
```

### Verspätungen aus flight_log
```sql
SELECT flight_id,
       TIMESTAMPDIFF(MINUTE, departure_old, departure_new) AS delay_minutes,
       comment
FROM flight_log
WHERE departure_new > departure_old;
```

### Wetterkorrelation mit Verspätungen
```sql
SELECT w.weather, COUNT(fl.flight_id) AS delayed_flights,
       AVG(TIMESTAMPDIFF(MINUTE, fl.departure_old, fl.departure_new)) AS avg_delay
FROM flight_log fl
JOIN flight f ON fl.flight_id = f.flight_id
JOIN airport_geo ag ON f.from = ag.airport_id
JOIN weatherdata w ON DATE(fl.departure_old) = w.log_date
WHERE fl.departure_new > fl.departure_old
GROUP BY w.weather;
```

### Top-Routen nach Buchungen
```sql
SELECT ag1.city AS from_city, ag2.city AS to_city,
       COUNT(b.booking_id) AS bookings,
       AVG(b.price) AS avg_price
FROM flight f
JOIN airport_geo ag1 ON f.from = ag1.airport_id
JOIN airport_geo ag2 ON f.to = ag2.airport_id
JOIN booking b ON f.flight_id = b.flight_id
GROUP BY f.from, f.to
ORDER BY bookings DESC
LIMIT 20;
```

## Externe CSV-Analyse (Zürich FIDS)
- Trennzeichen: Semikolon (`;`)
- Wichtige Spalten Arrivals: FLC (Airline), FLN (FlugNr), ORG (Origin), STA, ETA, ATA, TAR (Gate), PAX, TYS (Typ), REG (Registration)
- Wichtige Spalten Departures: FLC, FLN, DES (Destination), STD, ETD, ATD, GAT, PAX, TYS, REG
- Verspätung Ankunft: `ATA - STA`
- Verspätung Abflug: `ATD - STD`
