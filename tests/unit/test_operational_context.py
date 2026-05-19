from src.application.operational_context import (
    AircraftProfileSummary,
    BookingLoadSummary,
    BuildOperationalContext,
    LoadOperationalSelectionOptions,
    OperationalContext,
    OperationalSelectionOptions,
    SelectOption,
    TrafficLoadSummary,
    WeatherHistorySummary,
)
from src.infrastructure.dump_operational_context import (
    _angular_diff,
    _capacity_category,
    _safe_average,
    _weather_condition_mask,
    _weather_label,
)
import pandas as pd


def test_build_operational_context_delegates_to_repository():
    repository = _FakeOperationalRepository()
    use_case = BuildOperationalContext(repository)

    context = use_case.execute(
        aircraft_type_id=228,
        weather_condition="Regen",
        wind_speed_kmh=24,
        wind_direction_deg=280,
        departure_hour=11,
        destination_airport_id=2009,
    )

    assert context.aircraft.category == "medium"
    assert repository.last_call == (228, "Regen", 24, 280, 11, 2009)


def test_load_selection_options_delegates_to_repository():
    repository = _FakeOperationalRepository()
    use_case = LoadOperationalSelectionOptions(repository)

    options = use_case.execute()

    assert options.aircraft_types[0].label == "Airbus-A320-Familie"


def test_angular_diff_wraps_around_zero_degree_boundary():
    diffs = _angular_diff(pd.Series([350, 10, 180]), 0)

    assert diffs.tolist() == [10, 10, 180]


def test_weather_condition_mask_matches_exact_label_or_all():
    values = pd.Series(["Regen-Gewitter", "Nebel-Regen", "Schneefall", None])

    mask = _weather_condition_mask(values, "Regen-Gewitter")

    assert mask.tolist() == [True, False, False, False]
    assert _weather_condition_mask(values, "__all__").tolist() == [True, True, True, True]


def test_weather_and_aircraft_labels_are_user_readable():
    assert _weather_label("__all__") == "Alle Wetterlagen"
    assert _weather_label("Regen") == "Regen"
    assert _capacity_category(50) == "light"
    assert _capacity_category(180) == "medium"
    assert _capacity_category(320) == "heavy"


def test_safe_average_handles_empty_counts():
    assert _safe_average(10, 0) is None
    assert _safe_average(9, 3) == 3


class _FakeOperationalRepository:
    def __init__(self) -> None:
        self.last_call = None

    def get_context(
        self,
        aircraft_type_id: int | None,
        weather_condition: str,
        wind_speed_kmh: float,
        wind_direction_deg: float,
        departure_hour: int,
        destination_airport_id: int | None,
    ) -> OperationalContext:
        self.last_call = (
            aircraft_type_id,
            weather_condition,
            wind_speed_kmh,
            wind_direction_deg,
            departure_hour,
            destination_airport_id,
        )
        return OperationalContext(
            weather=WeatherHistorySummary(
                selected_weather=weather_condition,
                similar_observations=10,
                total_observations=100,
                date_min="2005-01-01",
                date_max="2005-01-02",
                station_count=4,
                avg_temp_c=3.0,
                avg_humidity_percent=80.0,
                avg_airpressure_hpa=1015.0,
                avg_wind_kmh=20.0,
                top_weather=(("Regen", 10),),
            ),
            aircraft=AircraftProfileSummary(
                type_id=aircraft_type_id,
                aircraft_type="Airbus-A320-Familie",
                category="medium",
                aircraft_count=5,
                avg_capacity=150.0,
                min_capacity=100,
                max_capacity=200,
                top_types=(("A320", 3),),
            ),
            traffic=TrafficLoadSummary(
                airport_iata="ZRH",
                destination_label="CTP - CARUTAPERA",
                destination_airport_id=destination_airport_id,
                departure_hour=departure_hour,
                total_departures=50,
                active_days=10,
                departures_at_hour=7,
                avg_departures_at_hour_per_day=0.7,
                busiest_hour=11,
                busiest_hour_departures=7,
                hourly_departures=((11, 7),),
            ),
            booking_load=BookingLoadSummary(
                sampled_chunk="booking@0",
                aircraft_type="Airbus-A320-Familie",
                destination_label="CTP - CARUTAPERA",
                sampled_bookings=100,
                sampled_flights=5,
                avg_bookings_per_flight=20.0,
                avg_load_factor_percent=50.0,
                median_load_factor_percent=50.0,
                high_load_flights_percent=10.0,
                note="sample",
            ),
        )

    def get_selection_options(self) -> OperationalSelectionOptions:
        return OperationalSelectionOptions(
            aircraft_types=(SelectOption(value="228", label="Airbus-A320-Familie"),),
            weather_conditions=(SelectOption(value="Regen", label="Regen"),),
            destinations=(SelectOption(value="2009", label="CTP - CARUTAPERA"),),
        )
