from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import StringIO
import re
from typing import Iterable
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
FORECAST_ITEMS_URL = (
    "https://data.geo.admin.ch/api/stac/v1/collections/"
    "ch.meteoschweiz.ogd-local-forecasting/items?limit=20"
)
SOURCE_LABEL = "MeteoSchweiz Open Data, SwissMetNet via STAC"
FORECAST_SOURCE_LABEL = "MeteoSchweiz Open Data, Local Forecast via STAC"
ZURICH_TZ = ZoneInfo("Europe/Zurich")
UTC = timezone.utc

FORECAST_POINT_BY_STATION = {
    "KLO": {
        "point_id": 59,
        "point_type_id": 1,
        "station_name": "Zuerich / Kloten",
    },
}
FORECAST_PARAMETERS = {
    "temperature_c": "tre200h0",
    "wind_speed_kmh": "fu3010h0",
    "gust_speed_kmh": "fu3010h1",
    "wind_direction_deg": "dkl010h0",
    "precipitation_hourly_mm": "rre150h0",
    "weather_symbol": "jww003i0",
}
FORECAST_ASSET_RE = re.compile(r"^vnut12\.lssw\.(\d{12})\.([a-z0-9]+)\.csv$")

RAIN_SYMBOLS = {
    6,
    9,
    14,
    17,
    20,
    29,
    32,
    33,
    106,
    109,
    114,
    117,
    120,
    129,
    132,
    133,
}
SLEET_SYMBOLS = {7, 10, 15, 18, 21, 31, 107, 110, 115, 118, 121, 131}
SNOW_SYMBOLS = {
    8,
    11,
    16,
    19,
    22,
    30,
    34,
    37,
    39,
    42,
    108,
    111,
    116,
    119,
    122,
    130,
    134,
    137,
    139,
    142,
}
THUNDERSTORM_SYMBOLS = {
    12,
    13,
    23,
    24,
    25,
    36,
    38,
    40,
    41,
    112,
    113,
    123,
    124,
    125,
    136,
    138,
    140,
    141,
}
FOG_SYMBOLS = {28, 128}

WEATHER_SYMBOL_LABELS = {
    6: "Aufhellungen, einzelne Regenschauer",
    7: "Aufhellungen, einzelne Regen- oder Schneeschauer",
    8: "Aufhellungen, einzelne Schneeschauer",
    9: "Bewoelkt, einige Regenschauer",
    10: "Bewoelkt, einige Regen- oder Schneeschauer",
    11: "Bewoelkt, einige Schneeschauer",
    12: "Aufhellungen, leicht gewitterhaft",
    13: "Aufhellungen und gewitterhaft",
    14: "Stark bewoelkt, schwacher Regen",
    15: "Stark bewoelkt, schwacher Schnee oder Regen",
    16: "Stark bewoelkt, schwacher Schnee",
    17: "Stark bewoelkt, zeitweise Regen",
    18: "Stark bewoelkt, zeitweise Schnee oder Regen",
    19: "Stark bewoelkt, zeitweise Schnee",
    20: "Stark bewoelkt, anhaltender Regen",
    21: "Stark bewoelkt, anhaltender Regen oder Schnee",
    22: "Stark bewoelkt, anhaltender Schnee",
    23: "Stark bewoelkt, leicht gewitterhaft",
    24: "Stark bewoelkt, gewitterhaft",
    25: "Stark bewoelkt, stark gewitterhaft",
    28: "Nebel",
    29: "Leicht bewoelkt, einzelne Regenschauer",
    30: "Leicht bewoelkt, leichter Schneefall",
    31: "Teilweise sonnig, Schnee- oder Regenschauer",
    32: "Teilweise sonnig, einige Regenschauer",
    33: "Bewoelkt, haeufige Regenschauer",
    34: "Bewoelkt, haeufige Schneeschauer",
    36: "Teilweise sonnig, gewitterhaft",
    37: "Teilweise sonnig, Gewitter und Schneeschauer",
    38: "Bewoelkt, Gewitter und Regenschauer",
    39: "Bewoelkt, Gewitter und Schneeschauer",
    40: "Stark bewoelkt, leicht gewitterhaft",
    41: "Bewoelkt, leicht gewitterhaft",
    42: "Stark bewoelkt, Gewitter und Schneeschauer",
    106: "Aufhellungen, einzelne Regenschauer",
    107: "Aufhellungen, einzelne Regen- oder Schneeschauer",
    108: "Aufhellungen, einzelne Schneeschauer",
    109: "Bewoelkt, einige Regenschauer",
    110: "Bewoelkt, einige Regen- oder Schneeschauer",
    111: "Bewoelkt, einige Schneeschauer",
    112: "Aufhellungen, leicht gewitterhaft",
    113: "Aufhellungen und gewitterhaft",
    114: "Stark bewoelkt, schwacher Regen",
    115: "Stark bewoelkt, schwacher Schnee oder Regen",
    116: "Stark bewoelkt, schwacher Schnee",
    117: "Stark bewoelkt, zeitweise Regen",
    118: "Stark bewoelkt, zeitweise Schnee oder Regen",
    119: "Stark bewoelkt, zeitweise Schnee",
    120: "Stark bewoelkt, anhaltender Regen",
    121: "Stark bewoelkt, anhaltender Regen oder Schnee",
    122: "Stark bewoelkt, anhaltender Schnee",
    123: "Stark bewoelkt, leicht gewitterhaft",
    124: "Stark bewoelkt, gewitterhaft",
    125: "Stark bewoelkt, stark gewitterhaft",
    128: "Nebel",
    129: "Leicht bewoelkt, einzelne Regenschauer",
    130: "Leicht bewoelkt, leichter Schneefall",
    131: "Leicht bewoelkt, Schnee- oder Regenschauer",
    132: "Leicht bewoelkt, einige Regenschauer",
    133: "Bewoelkt, haeufige Regenschauer",
    134: "Bewoelkt, haeufige Schneeschauer",
    136: "Aufhellungen, gewitterhaft",
    137: "Leicht bewoelkt, Gewitter und Schneeschauer",
    138: "Bewoelkt, Gewitter und Regenschauer",
    139: "Bewoelkt, Gewitter und Schneeschauer",
    140: "Stark bewoelkt, leicht gewitterhaft",
    141: "Bewoelkt, leicht gewitterhaft",
    142: "Stark bewoelkt, Gewitter und Schneeschauer",
}


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


@dataclass(frozen=True)
class ForecastWeatherSnapshot:
    station_code: str
    station_name: str
    point_id: int
    point_type_id: int
    target_offset_hours: int
    forecast_at_utc: datetime
    forecast_at_local: datetime
    forecast_run_at_utc: datetime
    forecast_run_at_local: datetime
    updated_at_utc: datetime | None
    temperature_c: float
    wind_speed_kmh: float
    gust_speed_kmh: float | None
    wind_direction_deg: int
    precipitation_hourly_mm: float | None
    visibility_m: int | None
    weather_symbol_code: int | None
    weather_symbol_label: str | None
    derived_weather_condition: str | None
    source_url: str


@dataclass(frozen=True)
class _ForecastValue:
    value: float | None
    valid_at_utc: datetime


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


def fetch_forecast_weather(
    station_code: str = "KLO",
    offset_hours: int = 2,
) -> ForecastWeatherSnapshot:
    if offset_hours < 0:
        raise MeteoSwissWeatherError("Forecast-Zeitpunkt muss in der Zukunft liegen.")

    station = station_code.upper()
    point = FORECAST_POINT_BY_STATION.get(station)
    if point is None:
        raise MeteoSwissWeatherError(
            f"Keine lokale MeteoSchweiz-Forecast-Zuordnung fuer {station} vorhanden."
        )

    item = _latest_forecast_item()
    assets = item.get("assets", {})
    target_at_utc = _forecast_target_time_utc(offset_hours)
    point_id = int(point["point_id"])
    point_type_id = int(point["point_type_id"])

    temperature_asset = _latest_forecast_asset(assets, FORECAST_PARAMETERS["temperature_c"])
    temperature = _read_forecast_value(
        str(temperature_asset["href"]),
        FORECAST_PARAMETERS["temperature_c"],
        point_id,
        point_type_id,
        target_at_utc,
        allow_next=True,
    )
    forecast_at_utc = temperature.valid_at_utc

    wind_speed_asset = _latest_forecast_asset(assets, FORECAST_PARAMETERS["wind_speed_kmh"])
    gust_asset = _latest_forecast_asset(assets, FORECAST_PARAMETERS["gust_speed_kmh"])
    direction_asset = _latest_forecast_asset(assets, FORECAST_PARAMETERS["wind_direction_deg"])
    precipitation_asset = _latest_forecast_asset(
        assets,
        FORECAST_PARAMETERS["precipitation_hourly_mm"],
    )

    wind_speed = _read_forecast_value(
        str(wind_speed_asset["href"]),
        FORECAST_PARAMETERS["wind_speed_kmh"],
        point_id,
        point_type_id,
        forecast_at_utc,
        allow_next=False,
    )
    gust_speed = _read_forecast_value(
        str(gust_asset["href"]),
        FORECAST_PARAMETERS["gust_speed_kmh"],
        point_id,
        point_type_id,
        forecast_at_utc,
        allow_next=False,
    )
    wind_direction = _read_forecast_value(
        str(direction_asset["href"]),
        FORECAST_PARAMETERS["wind_direction_deg"],
        point_id,
        point_type_id,
        forecast_at_utc,
        allow_next=False,
    )
    precipitation = _read_forecast_value(
        str(precipitation_asset["href"]),
        FORECAST_PARAMETERS["precipitation_hourly_mm"],
        point_id,
        point_type_id,
        forecast_at_utc,
        allow_next=False,
    )

    weather_symbol = _read_optional_forecast_value(
        assets,
        FORECAST_PARAMETERS["weather_symbol"],
        point_id,
        point_type_id,
        forecast_at_utc,
    )
    weather_symbol_code = (
        int(round(weather_symbol.value))
        if weather_symbol is not None and weather_symbol.value is not None
        else None
    )
    precipitation_value = precipitation.value
    derived_weather = _derive_forecast_weather_condition(
        weather_symbol_code,
        precipitation_value,
        temperature.value,
    )
    run_at_utc = _latest_forecast_asset_issue_time(temperature_asset)

    return ForecastWeatherSnapshot(
        station_code=station,
        station_name=str(point["station_name"]),
        point_id=point_id,
        point_type_id=point_type_id,
        target_offset_hours=offset_hours,
        forecast_at_utc=forecast_at_utc,
        forecast_at_local=forecast_at_utc.astimezone(ZURICH_TZ),
        forecast_run_at_utc=run_at_utc,
        forecast_run_at_local=run_at_utc.astimezone(ZURICH_TZ),
        updated_at_utc=_parse_iso_datetime(item.get("properties", {}).get("updated")),
        temperature_c=_required_forecast_float(temperature, "Temperatur"),
        wind_speed_kmh=_required_forecast_float(wind_speed, "Windgeschwindigkeit"),
        gust_speed_kmh=gust_speed.value,
        wind_direction_deg=round(_required_forecast_float(wind_direction, "Windrichtung")) % 360,
        precipitation_hourly_mm=precipitation_value,
        visibility_m=None,
        weather_symbol_code=weather_symbol_code,
        weather_symbol_label=(
            WEATHER_SYMBOL_LABELS.get(weather_symbol_code)
            if weather_symbol_code is not None
            else None
        ),
        derived_weather_condition=derived_weather,
        source_url=str(temperature_asset["href"]),
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


def _latest_forecast_item() -> dict:
    payload = _get_json(FORECAST_ITEMS_URL)
    features = payload.get("features", [])
    usable_features = [feature for feature in features if feature.get("assets")]
    if not usable_features:
        raise MeteoSwissWeatherError("Keine MeteoSchweiz-Forecast-Dateien gefunden.")

    return max(
        usable_features,
        key=lambda feature: (
            _parse_iso_datetime(feature.get("properties", {}).get("updated"))
            or datetime.min.replace(tzinfo=UTC)
        ),
    )


def _latest_forecast_asset(assets: dict, parameter: str) -> dict:
    matches: list[tuple[datetime, dict]] = []
    for name, asset in assets.items():
        match = FORECAST_ASSET_RE.match(name)
        if match is None or match.group(2) != parameter:
            continue
        matches.append((_parse_forecast_timestamp(match.group(1)), asset))

    if not matches:
        raise MeteoSwissWeatherError(
            f"Keine MeteoSchweiz-Forecast-Datei fuer Parameter {parameter} gefunden."
        )
    return max(matches, key=lambda item: item[0])[1]


def _latest_forecast_asset_issue_time(asset: dict) -> datetime:
    href = str(asset.get("href", ""))
    filename = href.rsplit("/", 1)[-1]
    match = FORECAST_ASSET_RE.match(filename)
    if match is None:
        raise MeteoSwissWeatherError("Forecast-Laufzeit konnte nicht gelesen werden.")
    return _parse_forecast_timestamp(match.group(1))


def _read_forecast_value(
    csv_url: str,
    parameter: str,
    point_id: int,
    point_type_id: int,
    target_at_utc: datetime,
    *,
    allow_next: bool,
) -> _ForecastValue:
    try:
        with requests.get(csv_url, timeout=30, stream=True) as response:
            response.raise_for_status()
            response.encoding = "latin-1"
            return _read_forecast_value_from_lines(
                response.iter_lines(decode_unicode=True),
                parameter,
                point_id,
                point_type_id,
                target_at_utc,
                allow_next=allow_next,
            )
    except requests.RequestException as exc:
        raise MeteoSwissWeatherError(
            "MeteoSchweiz Forecast-Datei ist im Moment nicht erreichbar."
        ) from exc


def _read_optional_forecast_value(
    assets: dict,
    parameter: str,
    point_id: int,
    point_type_id: int,
    forecast_at_utc: datetime,
) -> _ForecastValue | None:
    try:
        asset = _latest_forecast_asset(assets, parameter)
        return _read_forecast_value(
            str(asset["href"]),
            parameter,
            point_id,
            point_type_id,
            forecast_at_utc,
            allow_next=False,
        )
    except MeteoSwissWeatherError:
        return None


def _read_forecast_value_from_lines(
    lines: Iterable[str | bytes],
    parameter: str,
    point_id: int,
    point_type_id: int,
    target_at_utc: datetime,
    *,
    allow_next: bool,
) -> _ForecastValue:
    target_key = target_at_utc.astimezone(UTC).strftime("%Y%m%d%H%M")
    point_key = str(point_id)
    point_type_key = str(point_type_id)
    header_seen = False

    for raw_line in lines:
        line = raw_line.decode("latin-1") if isinstance(raw_line, bytes) else raw_line
        if not line:
            continue
        if not header_seen:
            header_seen = True
            if parameter not in line.split(";"):
                raise MeteoSwissWeatherError(
                    f"MeteoSchweiz-Forecast-Spalte fehlt: {parameter}"
                )
            continue

        fields = line.split(";")
        if len(fields) < 4 or fields[0] != point_key or fields[1] != point_type_key:
            continue

        date_key = fields[2]
        if date_key == target_key or (allow_next and date_key > target_key):
            return _ForecastValue(
                value=_parse_optional_forecast_number(fields[3]),
                valid_at_utc=_parse_forecast_timestamp(date_key),
            )

    raise MeteoSwissWeatherError(
        "MeteoSchweiz lieferte keinen passenden Forecast-Wert fuer Kloten."
    )


def _forecast_target_time_utc(offset_hours: int, now: datetime | None = None) -> datetime:
    local_now = (now or datetime.now(ZURICH_TZ)).astimezone(ZURICH_TZ)
    target = local_now + timedelta(hours=offset_hours)
    if target.minute or target.second or target.microsecond:
        target = target.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        target = target.replace(minute=0, second=0, microsecond=0)
    return target.astimezone(UTC)


def _parse_forecast_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d%H%M").replace(tzinfo=UTC)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _parse_optional_forecast_number(value: str) -> float | None:
    normalized = value.strip().replace(",", ".")
    if not normalized or normalized == "-":
        return None
    return float(normalized)


def _required_forecast_float(value: _ForecastValue, label: str) -> float:
    if value.value is None:
        raise MeteoSwissWeatherError(f"MeteoSchweiz-Forecast-Wert fehlt: {label}")
    return value.value


def _derive_forecast_weather_condition(
    weather_symbol_code: int | None,
    precipitation_mm: float | None,
    temperature_c: float | None,
) -> str | None:
    if weather_symbol_code in FOG_SYMBOLS:
        return "Nebel"
    if weather_symbol_code in THUNDERSTORM_SYMBOLS:
        return "Regen-Gewitter" if (precipitation_mm or 0.0) > 0 else "Gewitter"
    if weather_symbol_code in SLEET_SYMBOLS:
        return "Regen-Schneefall"
    if weather_symbol_code in SNOW_SYMBOLS:
        return "Schneefall"
    if weather_symbol_code in RAIN_SYMBOLS:
        return "Regen"

    precipitation = precipitation_mm or 0.0
    if precipitation <= 0:
        return None
    if temperature_c is not None and temperature_c <= 1.5:
        return "Schneefall"
    if temperature_c is not None and temperature_c <= 3.0:
        return "Regen-Schneefall"
    return "Regen"
