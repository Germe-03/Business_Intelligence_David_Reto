from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SelectOption:
    value: str
    label: str


@dataclass(frozen=True)
class OperationalSelectionOptions:
    aircraft_types: tuple[SelectOption, ...]
    weather_conditions: tuple[SelectOption, ...]
    destinations: tuple[SelectOption, ...]


@dataclass(frozen=True)
class WeatherHistorySummary:
    selected_weather: str
    similar_observations: int
    total_observations: int
    date_min: str | None
    date_max: str | None
    station_count: int
    avg_temp_c: float | None
    avg_humidity_percent: float | None
    avg_airpressure_hpa: float | None
    avg_wind_kmh: float | None
    top_weather: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class AircraftProfileSummary:
    type_id: int | None
    aircraft_type: str
    category: str
    aircraft_count: int
    avg_capacity: float | None
    min_capacity: int | None
    max_capacity: int | None
    top_types: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class TrafficLoadSummary:
    airport_iata: str
    destination_label: str
    destination_airport_id: int | None
    departure_hour: int
    total_departures: int
    active_days: int
    departures_at_hour: int
    avg_departures_at_hour_per_day: float
    busiest_hour: int | None
    busiest_hour_departures: int
    hourly_departures: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class BookingLoadSummary:
    sampled_chunk: str
    aircraft_type: str
    destination_label: str
    sampled_bookings: int
    sampled_flights: int
    avg_bookings_per_flight: float | None
    avg_load_factor_percent: float | None
    median_load_factor_percent: float | None
    high_load_flights_percent: float | None
    note: str


@dataclass(frozen=True)
class OperationalContext:
    weather: WeatherHistorySummary
    aircraft: AircraftProfileSummary
    traffic: TrafficLoadSummary
    booking_load: BookingLoadSummary


class OperationalContextRepository(Protocol):
    def get_selection_options(self) -> OperationalSelectionOptions:
        ...

    def get_context(
        self,
        aircraft_type_id: int | None,
        weather_condition: str,
        wind_speed_kmh: float,
        wind_direction_deg: float,
        departure_hour: int,
        destination_airport_id: int | None,
    ) -> OperationalContext:
        ...


class BuildOperationalContext:
    def __init__(self, repository: OperationalContextRepository) -> None:
        self._repository = repository

    def execute(
        self,
        aircraft_type_id: int | None,
        weather_condition: str,
        wind_speed_kmh: float,
        wind_direction_deg: float,
        departure_hour: int,
        destination_airport_id: int | None,
    ) -> OperationalContext:
        return self._repository.get_context(
            aircraft_type_id=aircraft_type_id,
            weather_condition=weather_condition,
            wind_speed_kmh=wind_speed_kmh,
            wind_direction_deg=wind_direction_deg,
            departure_hour=departure_hour,
            destination_airport_id=destination_airport_id,
        )


class LoadOperationalSelectionOptions:
    def __init__(self, repository: OperationalContextRepository) -> None:
        self._repository = repository

    def execute(self) -> OperationalSelectionOptions:
        return self._repository.get_selection_options()
