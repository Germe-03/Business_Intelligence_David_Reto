# Datenbankschema

## Primäre Tabellen (MySQL-Dump)
| Tabelle | Schlüsselspalten | Grösse |
|---|---|---|
| airline | airline_id, iata, airlinename, base_airport | ~113 |
| airplane | airplane_id, capacity, type_id, airline_id | ~5'500 |
| airplane_type | type_id, identifier, description | ~342 |
| airport | airport_id, iata, icao, name | ~13'500 |
| airport_geo | airport_id, city, country, latitude, longitude | ~13'500 |
| booking | booking_id, flight_id, seat, passenger_id, price | ~55 Mio |
| employee | employee_id, firstname, lastname, salary, department | ~1'000 |
| flight | flight_id, flightno, from, to, departure, arrival | ~758'000 |
| flight_log | flight_id, departure_old, departure_new, comment | variabel |
| flightschedule | flightno, from, to, departure, arrival, Mo–So | variabel |
| passenger | passenger_id, passportno, firstname, lastname | ~36'000 |
| passengerdetails | passenger_id, birthdate, sex, city, country, zip | ~36'000 |
| weatherdata | log_date, time, station, temp, wind, winddirection, weather | variabel |

## Externe CSVs (Semikolon-getrennt)
### arrivals_*.csv
FLC (Airline), FLN (FlugNr), ORG (Origin), STA, ETA, ATA, TYS (Typ), PAX, RWY (Piste), REG (Registration)

### departures_*.csv
FLC, FLN, DES (Destination), STD, ETD, ATD, TYS, PAX, RWY, REG

## Runway-Mapping Zürich (ZRH)
| RWY | Richtung | Nutzung |
|---|---|---|
| 14 | 140° | Landung (Nordwind) |
| 16 | 160° | Landung |
| 28 | 280° | Start & Landung (häufigste) |
| 32 | 320° | Start |
| 34 | 340° | Start & Landung |
