from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dashboard.runway_view import (
    _has_thunderstorm,
    _precipitation_from_weather,
    _weather_basis_text,
    _weather_snapshot_apply_key,
    _weather_snapshot_caption,
)
from src.infrastructure.meteoswiss_weather import ForecastWeatherSnapshot, LiveWeatherSnapshot


def test_weather_label_mapping_for_decision_inputs():
    assert _precipitation_from_weather("Regen-Gewitter") == "rain"
    assert _precipitation_from_weather("Nebel-Regen") == "fog"
    assert _precipitation_from_weather("Regen-Schneefall") == "snow"
    assert _precipitation_from_weather("__all__") == "none"
    assert _has_thunderstorm("Nebel-Regen-Gewitter") is True
    assert _has_thunderstorm("Regen") is False


def test_forecast_snapshot_texts_explain_valid_time_and_manual_visibility():
    snapshot = _forecast_snapshot()

    caption = _weather_snapshot_caption(snapshot)
    basis = _weather_basis_text(snapshot)
    apply_key = _weather_snapshot_apply_key(snapshot)

    assert "Forecast: Flughafen Zuerich / Kloten" in caption
    assert "gueltig 19.05.2026 17:00 Lokalzeit" in caption
    assert "Sichtweite bleibt manuell" in caption
    assert "Wetterbasis: MeteoSchweiz-Forecast fuer Kloten" in basis
    assert "Aktuelle Annahme: Regen" in basis
    assert apply_key == "forecast:KLO:2:2026-05-19T15:00:00+00:00:2026-05-19T12:00:00+00:00"


def test_live_snapshot_texts_explain_measurement_time():
    snapshot = _live_snapshot()

    caption = _weather_snapshot_caption(snapshot)
    basis = _weather_basis_text(snapshot)
    apply_key = _weather_snapshot_apply_key(snapshot)

    assert "Live-Wetter: Flughafen Zuerich / Kloten" in caption
    assert "19.05.2026 14:10 Lokalzeit" in caption
    assert "keinen aktuellen Kloten-Wert" in caption
    assert "Wetterbasis: MeteoSchweiz-Livewerte Kloten" in basis
    assert "Aktuelle Annahme: keine besondere Wetterlage" in basis
    assert apply_key == "live:KLO:2026-05-19T12:10:00+00:00"


def test_manual_weather_basis_text_when_no_snapshot_available():
    assert _weather_basis_text(None) == (
        "Wetterbasis: manuelle Eingaben. Wind, Sichtweite, Wetterlage und "
        "Abflugstunde koennen frei fuer Szenarien gesetzt werden."
    )


def _forecast_snapshot() -> ForecastWeatherSnapshot:
    forecast_at = datetime(2026, 5, 19, 15, 0, tzinfo=timezone.utc)
    run_at = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    return ForecastWeatherSnapshot(
        station_code="KLO",
        station_name="Zuerich / Kloten",
        point_id=59,
        point_type_id=1,
        target_offset_hours=2,
        forecast_at_utc=forecast_at,
        forecast_at_local=forecast_at.astimezone(ZoneInfo("Europe/Zurich")),
        forecast_run_at_utc=run_at,
        forecast_run_at_local=run_at.astimezone(ZoneInfo("Europe/Zurich")),
        updated_at_utc=run_at,
        temperature_c=16.9,
        wind_speed_kmh=8.1,
        gust_speed_kmh=16.9,
        wind_direction_deg=296,
        precipitation_hourly_mm=0.1,
        visibility_m=None,
        weather_symbol_code=117,
        weather_symbol_label="Stark bewoelkt, zeitweise Regen",
        derived_weather_condition="Regen",
        source_url="https://example.test/forecast.csv",
    )


def _live_snapshot() -> LiveWeatherSnapshot:
    measured = datetime(2026, 5, 19, 12, 10, tzinfo=timezone.utc)
    return LiveWeatherSnapshot(
        station_code="KLO",
        station_name="Zuerich / Kloten",
        measured_at_utc=measured,
        measured_at_local=measured.astimezone(ZoneInfo("Europe/Zurich")),
        temperature_c=15.2,
        wind_speed_kmh=11.4,
        gust_speed_kmh=18.0,
        wind_direction_deg=280,
        precipitation_10min_mm=0.0,
        humidity_pct=63.0,
        dewpoint_c=8.1,
        pressure_qfe_hpa=970.0,
        pressure_qnh_hpa=1015.0,
        global_radiation_wm2=220.0,
        sunshine_10min_min=5.0,
        snow_depth_cm=None,
        windchill_c=None,
        foehn_index=None,
        visibility_m=None,
        derived_weather_condition=None,
        visual_observed_at_local=None,
        visual_cloud_cover_pct=None,
        visual_observation_note=None,
        source_url="https://example.test/live.csv",
    )
