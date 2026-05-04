# SKILL: ETL – Daten laden

## Trigger
Wenn .tsv.zst Dateien oder externe CSVs geladen werden müssen.

## .tsv.zst laden
```python
import zstandard as zstd, pandas as pd, io, glob

def load_tsv_zst(path: str) -> pd.DataFrame:
    with open(path, 'rb') as f:
        with zstd.ZstdDecompressor().stream_reader(f) as r:
            return pd.read_csv(io.TextIOWrapper(r, encoding='utf-8'), sep='\t')

# Grosse Tabelle (booking = 24 Chunks)
def load_table(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    return pd.concat([load_tsv_zst(f) for f in files], ignore_index=True)
```

## Externe CSVs laden
```python
arrivals = pd.read_csv("Data/external/arrivals_*.csv", sep=';')
departures = pd.read_csv("Data/external/departures_*.csv", sep=';')
```

## Wichtig
- booking: 24 Chunks – in Tests nur 1 Chunk laden
- Encoding: utf-8
- Neue Dateien → `Data/external/`
