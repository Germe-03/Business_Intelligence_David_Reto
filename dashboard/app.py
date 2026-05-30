import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


st.set_page_config(
    page_title="Flughafen-Dashboard - Übersicht",
    layout="wide",
)

st.title("Flughafen-Dashboard")
st.caption("Decision-Support und Business Intelligence rund um Flughafendaten - Studienprojekt.")

st.markdown(
    """
Dieses Projekt verbindet zwei Werkzeuge unter einem Dach:

- **Runway-Empfehlung** - ein Entscheidungs-Tool: Wetter und Flugzeugtyp eingeben,
  und das System empfiehlt regelbasiert die beste Startpiste für Zürich (28/32/34)
  mit Score, Konfidenz und Begründung.
- **BI-/OSINT-/KI-Dashboard** - Datenanalyse über Flugbetrieb, Buchungen, Umsatz,
  Passagiere und Wetter, ein KI-Analyst (Frage auf Deutsch -> Datenbank-Abfrage) sowie
  Live-Karten echter Flugzeuge rund um Zürich.

Demonstriert werden damit Clean Architecture mit Tests, Datenvisualisierung,
UX nach ISO 9241 und der Einsatz von KI.
"""
)

st.subheader("Die Seiten (Auswahl links im Menü)")
st.markdown(
    """
| Seite | Zweck |
|---|---|
| **Runway Empfehlung** | Pistenempfehlung für Starts in ZRH nach Wetter und Flugzeugtyp |
| **BI Dashboard** | Kennzahlen und Visualisierungen zu Flugbetrieb, Umsatz und Wetter |
| **KI Analyst** | Fragen in natürlicher Sprache, automatisch in eine SQL-Abfrage übersetzt |
| **OSINT Live** | Aktuelle Flugzeugpositionen rund um ZRH (OpenSky Network) |
| **OSINT Map** | Flugreichste Routen aus den Daten plus Live-Overlay |
| **OSINT Kepler** | 3D-Routen und Buchungs-Heatmap ab ZRH |
"""
)

st.info(
    "**Zur Datengrundlage:** Die Auswertungen nutzen eine öffentliche Demo-Flugdatenbank "
    "mit rund 13'500 Flughäfen weltweit (Flüge/Buchungen aus Sommer 2015, Wetter 2005-2015). "
    "Die Kennzahlen im BI-Dashboard sind daher standardmässig weltweit, nicht Zürich-spezifisch - "
    "der Zürich-Bezug liegt in der Pisten-Logik und den Live-Daten. Das BI-Dashboard lässt sich "
    "links per Datenquelle auf Abflüge ab Zürich einschränken."
)
st.caption(
    "Hinweis: Die Runway-Empfehlung ist ein vereinfachtes Lernmodell und nicht für "
    "operative Freigaben gedacht."
)
