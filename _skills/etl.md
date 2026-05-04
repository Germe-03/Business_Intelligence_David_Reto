# Skill: ETL & Datenladen

## Zweck
Daten aus den .tsv.zst Dateien und externen CSVs laden und für die Analyse vorbereiten.

## Datenbankverbindung (MySQL)
```python
from sqlalchemy import create_engine
engine = create_engine("mysql+pymysql://root:password@localhost/flughafendb_large")
```

## .tsv.zst Dateien lesen
Die Rohdaten liegen als Zstandard-komprimierte TSV-Dateien vor:
```python
import zstandard as zstd
import pandas as pd
import io

def load_tsv_zst(filepath):
    with open(filepath, 'rb') as f:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(f) as reader:
            text = io.TextIOWrapper(reader, encoding='utf-8')
            return pd.read_csv(text, sep='\t')
```

## Grosse Tabellen (booking – 24 Chunks)
```python
import glob
chunks = sorted(glob.glob("Data/flughafendb_large/*booking*.tsv.zst"))
df = pd.concat([load_tsv_zst(f) for f in chunks], ignore_index=True)
```

## Externe CSVs laden
```python
arrivals = pd.read_csv("Data/external/arrivals_2007-06-18_2007-06-24.csv", sep=';')
departures = pd.read_csv("Data/external/departures_2017-06-19_2017-06-25.csv", sep=';')
```

## Neue Datenquellen
Neue CSV-Dateien immer in `Data/external/` ablegen.
Neue Tabellen aus der DB folgen dem gleichen .tsv.zst Muster.

## Wichtige Datei-Namenskonvention
- `flughafendb_large@{tabelle}@@0.tsv.zst` – Single-Chunk-Tabellen
- `flughafendb_large@{tabelle}@{n}.tsv.zst` – Multi-Chunk (booking: 0–23)
