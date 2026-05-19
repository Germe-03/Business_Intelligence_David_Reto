from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo

import pandas as pd
import requests


STAC_ITEM_URL = (
    "https://data.geo.admin.ch/api/stac/v1/collections/"
    "ch.meteoschweiz.ogd-smn/items/{station}"
)
OBS_ITEM_URL = (
    "https://data.geo.admin.ch/api/stac/v1/collections/"
    "ch.meteoschweiz.ogd-obs/items/{station}"
)
SOURCE_LABEL = "MeteoSchweiz Open Data, SwissMetNet via STAC"


@dataclass(frozen=True)
class LiveWeatherSnapshot:
    station_code: str
    station_name: str
    measured_at_utc: datetime
    measured_at_local: datetime
    temperature_c: float
    wind_speed_kmh: float
    gust_speed_kmh: float | None
    wind_direction_deg: int
    precipitation_10min_mm: float
    humidity_pct: float | None
    dewpoint_c: float | None
    pressure_qfe_hpa: float | None
    pressure_qnh_hpa: float | None
    global_radiation_wm2: float | None
    sunshine_10min_min: float | None
    snow_depth_cm: float | None
    windchill_c: float | None
    foehn_index: float | None
    visibility_m: int | None
    derived_weather_condition: str | None
    visual_observed_at_local: datetime | None
    visual_cloud_cover_pct: float | None
    visual_observation_note: str | None
    source_url: str


class MeteoSwissWeatherError(RuntimeError):
    pass


def fetch_live_weather(station_code: str = "KLO") -> LiveWeatherSnapshot:
    station = station_code.lower()
    item_url = STAC_ITEM_URL.format(station=station)
    item = _get_json(item_url)
    assets = item.get("assets", {})
    asset = assets.get(f"ogd-smn_{station}_t_now.csv")
    if not asset:
        raise MeteoSwissWeatherError(
            f"Keine 10-Minuten-Livewerte fuer Station {station_code.upper()} gefunden."
        )

    csv_url = str(asset["href"])
    csv_text = _get_text(csv_url)
    frame = pd.read_csv(StringIO(csv_text), sep=";", na_values="-")
    if frame.empty:
        raise MeteoSwissWeatherError(
            f"MeteoSchweiz lieferte keine Livewerte fuer {station_code.upper()}."
        )

    latest = frame.dropna(subset=["reference_timestamp"]).iloc[-1]
    measured_at_utc = pd.to_datetime(
        latest["reference_timestamp"],
        dayfirst=True,
        utc=True,
    ).to_pydatetime()

    visual = _fetch_visual_observation(station_code)
    derived_weather = _derive_weather_condition(latest, visual)

    return LiveWeatherSnapshot(
        station_code=station_code.upper(),
        station_name=str(item.get("properties", {}).get("title", station_code.upper())),
        measured_at_utc=measured_at_utc,
        measured_at_local=measured_at_utc.astimezone(ZoneInfo("Europe/Zurich")),
        temperature_c=_required_float(latest, "tre200s0"),
        wind_speed_kmh=_required_float(latest, "fu3010z0"),
        gust_speed_kmh=_optional_float(latest, "fu3010z1"),
        wind_direction_deg=round(_required_float(latest, "dkl010z0")) % 360,
        precipitation_10min_mm=_optional_float(latest, "rre150z0") or 0.0,
        humidity_pct=_optional_float(latest, "ure200s0"),
        dewpoint_c=_optional_float(latest, "tde200s0"),
        pressure_qfe_hpa=_optional_float(latest, "prestas0"),
        pressure_qnh_hpa=_optional_float(latest, "pp0qnhs0"),
        global_radiation_wm2=_optional_float(latest, "gre000z0"),
        sunshine_10min_min=_optional_float(latest, "sre000z0"),
        snow_depth_cm=_optional_float(latest, "htoauts0"),
        windchill_c=_optional_float(latest, "xchills0"),
        foehn_index=_optional_float(latest, "wcc006s0"),
        visibility_m=None,
        derived_weather_condition=derived_weather,
        visual_observed_at_local=visual.get("observed_at_local"),
        visual_cloud_cover_pct=visual.get("cloud_cover_pct"),
        visual_observation_note=visual.get("note"),
        source_url=csv_url,
    )


def _get_json(url: str) -> dict:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise MeteoSwissWeatherError(
            "MeteoSchweiz STAC-API ist im Moment nicht erreichbar."
        ) from exc


def _get_text(url: str) -> str:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise MeteoSwissWeatherError(
            "MeteoSchweiz Messwert-Datei ist im Moment nicht erreichbar."
        ) from exc


def _fetch_visual_observation(station_code: str) -> dict:
    station = station_code.lower()
    try:
        item = _get_json(OBS_ITEM_URL.format(station=station))
        asset = item.get("assets", {}).get(f"ogd-obs_{station}_d_recent.csv")
        if not asset:
            return {"note": "Keine visuellen Beobachtungen fuer diese Station verfuegbar."}
        frame = pd.read_csv(StringIO(_get_text(str(asset["href"]))), sep=";", na_values="-")
    except MeteoSwissWeatherError:
        return {"note": "Visuelle Beobachtungen konnten nicht geladen werden."}

    if frame.empty:
        return {"note": "Keine visuellen Beobachtungen vorhanden."}

    latest = frame.dropna(subset=["reference_timestamp"]).iloc[-1]
    observed_at = pd.to_datetime(
        latest["reference_timestamp"],
        dayfirst=True,
        utc=True,
    ).to_pydatetime()
    observed_local = observed_at.astimezone(ZoneInfo("Europe/Zurich"))
    today = datetime.now(ZoneInfo("Europe/Zurich")).date()
    if observed_local.date() != today:
        return {
            "observed_at_local": observed_local,
            "note": (
                "Visuelle Kloten-Beobachtungen sind nicht tagesaktuell; "
                "Sichtweite bleibt manuell."
            ),
        }

    return {
        "observed_at_local": observed_local,
        "cloud_cover_pct": _optional_float(latest, "nto000d0"),
        "rain": _is_true(latest, "w1p012d0"),
        "rain_snow": _is_true(latest, "w2p001d0"),
        "snowfall": _is_true(latest, "w2p002d0"),
        "hail": _is_true(latest, "w3p002d0"),
        "fog": _is_true(latest, "w5p002d0"),
        "snow_cover": _is_true(latest, "est000d0"),
        "note": "Visuelle Tagesbeobachtung geladen; keine Sichtweite im Datensatz.",
    }


def _derive_weather_condition(row: pd.Series, visual: dict) -> str | None:
    if visual.get("fog"):
        return "Nebel"
    if visual.get("rain_snow"):
        return "Regen-Schneefall"
    if visual.get("snowfall"):
        return "Schneefall"
    if visual.get("rain"):
        return "Regen"

    precipitation = _optional_float(row, "rre150z0") or 0.0
    temperature = _optional_float(row, "tre200s0")
    snow_depth = _optional_float(row, "htoauts0") or 0.0
    if precipitation <= 0:
        return None
    if temperature is not None and temperature <= 1.5:
        return "Schneefall"
    if temperature is not None and temperature <= 3.0:
        return "Regen-Schneefall"
    if snow_depth > 0 and temperature is not None and temperature <= 4.0:
        return "Regen-Schneefall"
    return "Regen"


def _required_float(row: pd.Series, column: str) -> float:
    value = _optional_float(row, column)
    if value is None:
        raise MeteoSwissWeatherError(f"MeteoSchweiz-Wert fehlt: {column}")
    return value


def _optional_float(row: pd.Series, column: str) -> float | None:
    value = row.get(column)
    if pd.isna(value):
        return None
    return float(value)


def _is_true(row: pd.Series, column: str) -> bool:
    value = row.get(column)
    if pd.isna(value):
        return False
    return int(value) == 1
