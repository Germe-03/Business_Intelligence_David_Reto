# MMI-Prinzipien – Angewendet auf das Runway-Dashboard

Kurs: Grundlagen der Mensch-Maschine Interaktion (Javier Bargas-Avila)
Angewendet auf: Streamlit Decision-Support-Dashboard (Runway-Empfehlung)

---

## 1. ISO 9241 – 7 Dialoggestaltungsprinzipien

### 1.1 Aufgabenangemessenheit
> Zeige nur was der Nutzer für seine Aufgabe braucht.

- Dashboard-Startseite zeigt **direkt** die Runway-Empfehlung — keine Begrüssungsseite
- Wettereingabe hat **Standardwerte** (aktuell gemessene Werte wenn verfügbar)
- Technische Details (airport_id, flight_id) werden dem Nutzer **nie** angezeigt
- Nur relevante Wettervariablen für die Entscheidung sichtbar (Wind, Richtung, Wetterlage)

### 1.2 Selbstbeschreibungsfähigkeit
> Der Nutzer soll immer wissen wo er ist und was er tun kann.

- Jede Seite hat einen klaren Titel und eine Kurzbeschreibung ihres Zwecks
- Alle Eingabefelder haben beschriftete Labels (nicht nur Platzhalter)
- Einheiten immer angeben: `Windgeschwindigkeit (km/h)`, `Temperatur (°C)`
- Konfidenzwert der Empfehlung wird angezeigt: `Empfehlung: Piste 28 (87% Konfidenz)`

### 1.3 Steuerbarkeit
> Der Nutzer kontrolliert das System, nicht umgekehrt.

- Alle Filter und Eingaben sind jederzeit änderbar (kein "Weiter"-Zwang)
- Sidebar-Filter beeinflussen das Dashboard in Echtzeit
- "Zurücksetzen"-Button für alle Eingaben vorhanden

### 1.4 Erwartungskonformität
> Das System verhält sich so wie der Nutzer es erwartet.

- Runway-Nummern werden als **28**, **32**, **34** angezeigt (nicht als DB-IDs)
- Wetterlage-Icons: Wolke für Nebel, Schneeflocke für Schnee, Regentropfen für Regen
- Windrichtung als Kompassrose-Visualisierung, nicht als Zahl allein
- Farben konsistent: Grün = empfohlen, Orange = Einschränkungen, Rot = nicht geeignet

### 1.5 Fehlertoleranz
> Fehlerhafte Eingaben führen nicht zum Absturz, sondern zu hilfreichen Hinweisen.

- Windgeschwindigkeit: Eingabe < 0 wird abgefangen mit Hinweis
- Winddirection ausserhalb 0–360°: automatisch normalisieren
- Wenn keine Wetterdaten verfügbar: klar kommunizieren statt leere Grafik
- Fehlermeldungen beschreiben **was falsch ist** und **wie man es behebt**

### 1.6 Individualisierbarkeit
> Der Nutzer kann das System an seine Bedürfnisse anpassen.

- Einheiten wählbar: km/h oder Knoten für Windgeschwindigkeit
- Ansicht: Kompaktmodus (nur Empfehlung) vs. Detailmodus (alle Faktoren)
- Sprachauswahl: Deutsch / Englisch (Labels, Achsenbeschriftungen)

### 1.7 Lernförderlichkeit
> Das System hilft dem Nutzer, es besser zu verstehen.

- Tooltip bei der Empfehlung erklärt **warum** Piste X empfohlen wird
- Historische Ansicht: "So wurde in der Vergangenheit bei ähnlichem Wetter entschieden"
- Erste Nutzung: kurze Onboarding-Erklärung (dismissbar)

---

## 2. Don Norman – 6 Design-Faktoren

### Visibility (Sichtbarkeit)
- Empfohlene Piste ist das **grösste Element** auf der Seite
- Aktive Filter in der Sidebar sind visuell hervorgehoben

### Feedback
- Nach Änderung der Wettereingabe aktualisiert sich die Empfehlung sofort (Echtzeit)
- Ladezustand mit `st.spinner()` anzeigen wenn Modell rechnet

### Constraints
- Windrichtung: Slider nur 0–360°, keine Freitexteingabe
- Flugzeugkategorie: Dropdown (Klein/Mittel/Gross), keine freie Eingabe

### Mapping
- Windrichtung auf Kompassrose → zeigt intuitiv woher der Wind kommt
- Runway-Karte zeigt Piste am Flughafen Zürich visuell markiert

### Consistency
- Farbschema, Schriftart und Layout identisch auf allen Seiten
- Gleiches Wetter-Widget auf jeder Seite die Wetterdaten nutzt

### Conceptual Model (Konzeptuelles Modell)
- Nutzer sieht: "Ich gebe Wetter ein → System empfiehlt Piste"
- Kein internes ML-Jargon (nicht: "Klasse 2 mit Konfidenz 0.87", sondern: "Piste 28 — sehr empfohlen")

---

## 3. User Centered Design (UCD)

### Nutzer dieser Anwendung
**Primär:** Flugleiter / Dispatcher am Flughafen Zürich
- Kennt Runway-Nummern und Windbegriffe
- Braucht schnelle, eindeutige Entscheidungsunterstützung
- Arbeitet unter Zeitdruck

**Sekundär:** BI-Studenten / Prüfungskontext
- Braucht nachvollziehbare Visualisierungen
- Interessiert an der Datengrundlage

### CUJ – Critical User Journey
```
Nutzer öffnet Dashboard
  → sieht sofort aktuelle Wetterlage
  → passt ggf. Werte an
  → sieht Runway-Empfehlung mit Begründung
  → entscheidet
Gesamtzeit: unter 30 Sekunden
```

### Iteratives Design
1. Prototyp: nur Empfehlung + Eingabe
2. Feedback einholen (Kommilitonen, Dozent)
3. Historische Ansicht hinzufügen
4. Wieder testen

---

## 4. UX Metrics – HEART Framework

| Dimension | Metrik für dieses Dashboard |
|---|---|
| **Happiness** | Nutzer findet Empfehlung verständlich (subjektiv, Feedback) |
| **Engagement** | Wie oft wird die Wettereingabe angepasst pro Session |
| **Adoption** | Dashboard wird für Entscheidung verwendet, nicht ignoriert |
| **Retention** | Wird es auch nach der Erstnutzung wieder geöffnet |
| **Task Success** | Nutzer kommt in < 30s zur Runway-Empfehlung |

---

## 5. Gestalt-Prinzipien (Interaktionsdesign)

- **Nähe:** Zusammengehörende Wetterwerte gruppiert (Wind + Richtung zusammen)
- **Ähnlichkeit:** Alle Eingabefelder haben gleiches visuelles Gewicht
- **Gemeinsame Region:** Empfehlungsbereich klar vom Eingabebereich getrennt (Card/Box)

---

## Checkliste vor jedem Dashboard-Release

- [ ] Alle Felder haben Labels mit Einheiten
- [ ] Fehlereingaben werden abgefangen
- [ ] Empfehlung braucht < 30s Verständnis ohne Erklärung
- [ ] Konsistentes Farbschema auf allen Seiten
- [ ] Keine DB-IDs oder interne Keys sichtbar
- [ ] Tooltips bei Konfidenzwerten vorhanden
