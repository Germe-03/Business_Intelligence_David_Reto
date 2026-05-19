from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.application.operational_context import (
    AircraftProfileSummary,
    BookingLoadSummary,
    OperationalContext,
    OperationalSelectionOptions,
    SelectOption,
    TrafficLoadSummary,
    WeatherHistorySummary,
)


DATA_DIR = Path("Data/flughafendb_large")
ZRH_AIRPORT_ID = 13591

class DumpOperationalContextRepository:
    def __init__(
        self,
        data_dir: str | Path = DATA_DIR,
        airport_iata: str = "ZRH",
    ) -> None:
        self._data_dir = Path(data_dir)
        self._airport_iata = airport_iata

    def get_selection_options(self) -> OperationalSelectionOptions:
        return OperationalSelectionOptions(
            aircraft_types=self._aircraft_options(),
            weather_conditions=self._weather_options(),
            destinations=self._destination_options(),
        )

    def get_context(
        self,
        aircraft_type_id: int | None,
        weather_condition: str,
        wind_speed_kmh: float,
        wind_direction_deg: float,
        departure_hour: int,
        destination_airport_id: int | None,
    ) -> OperationalContext:
        return OperationalContext(
            weather=self._weather_history(
                wind_speed_kmh=round(float(wind_speed_kmh), 1),
                wind_direction_deg=round(float(wind_direction_deg) % 360, 1),
                weather_condition=weather_condition,
            ),
            aircraft=self._aircraft_profile(aircraft_type_id),
            traffic=self._traffic_load(int(departure_hour), destination_airport_id),
            booking_load=self._booking_load(aircraft_type_id, destination_airport_id),
        )

    @lru_cache(maxsize=128)
    def _weather_history(
        self,
        wind_speed_kmh: float,
        wind_direction_deg: float,
        weather_condition: str,
    ) -> WeatherHistorySummary:
        weather_path = self._data_dir / "flughafendb_large@weatherdata@@0.tsv.zst"
        columns = self._columns_for("weatherdata")
        usecols = [
            "log_date",
            "station",
            "temp",
            "humidity",
            "airpressure",
            "wind",
            "weather",
            "winddirection",
        ]

        total_observations = 0
        similar_observations = 0
        date_min: str | None = None
        date_max: str | None = None
        stations: set[int] = set()
        weather_counter: Counter[str] = Counter()
        temp_sum = 0.0
        humidity_sum = 0.0
        pressure_sum = 0.0
        wind_sum = 0.0

        for chunk in pd.read_csv(
            weather_path,
            sep="\t",
            names=columns,
            usecols=usecols,
            compression="zstd",
            na_values="\\N",
            chunksize=250_000,
        ):
            total_observations += len(chunk)
            if chunk.empty:
                continue

            chunk_min = str(chunk["log_date"].min())
            chunk_max = str(chunk["log_date"].max())
            date_min = chunk_min if date_min is None else min(date_min, chunk_min)
            date_max = chunk_max if date_max is None else max(date_max, chunk_max)
            stations.update(int(station) for station in chunk["station"].dropna().unique())

            direction_diff = _angular_diff(chunk["winddirection"], wind_direction_deg)
            speed_diff = (chunk["wind"] - wind_speed_kmh).abs()
            mask = (direction_diff <= 30) & (speed_diff <= 10)
            mask &= _weather_condition_mask(chunk["weather"], weather_condition)

            similar = chunk.loc[mask]
            if similar.empty:
                continue

            similar_observations += len(similar)
            temp_sum += float(similar["temp"].sum())
            humidity_sum += float(similar["humidity"].sum())
            pressure_sum += float(similar["airpressure"].sum())
            wind_sum += float(similar["wind"].sum())
            weather_counter.update(
                str(value) if pd.notna(value) else "Keine Angabe"
                for value in similar["weather"]
            )

        return WeatherHistorySummary(
            selected_weather=_weather_label(weather_condition),
            similar_observations=similar_observations,
            total_observations=total_observations,
            date_min=date_min,
            date_max=date_max,
            station_count=len(stations),
            avg_temp_c=_safe_average(temp_sum, similar_observations),
            avg_humidity_percent=_safe_average(humidity_sum, similar_observations),
            avg_airpressure_hpa=_safe_average(pressure_sum, similar_observations),
            avg_wind_kmh=_safe_average(wind_sum, similar_observations),
            top_weather=tuple(weather_counter.most_common(5)),
        )

    @lru_cache(maxsize=512)
    def _aircraft_profile(self, aircraft_type_id: int | None) -> AircraftProfileSummary:
        airplanes = self._airplanes()
        airplane_types = self._airplane_types()
        selected = airplanes.copy()
        if aircraft_type_id is not None:
            selected = selected.loc[selected["type_id"].eq(aircraft_type_id)].copy()
        if selected.empty:
            return AircraftProfileSummary(
                type_id=aircraft_type_id,
                aircraft_type="Keine Auswahl",
                category="medium",
                aircraft_count=0,
                avg_capacity=None,
                min_capacity=None,
                max_capacity=None,
                top_types=(),
            )

        selected = selected.merge(airplane_types, on="type_id", how="left")
        category = _capacity_category(float(selected["capacity"].mean()))
        aircraft_type = (
            str(selected["identifier"].dropna().iloc[0])
            if selected["identifier"].notna().any()
            else "Unbekannt"
        )
        top_types = (
            selected["identifier"]
            .fillna("Unbekannt")
            .value_counts()
            .head(5)
            .items()
        )
        return AircraftProfileSummary(
            type_id=aircraft_type_id,
            aircraft_type=aircraft_type,
            category=category,
            aircraft_count=len(selected),
            avg_capacity=round(float(selected["capacity"].mean()), 1),
            min_capacity=int(selected["capacity"].min()),
            max_capacity=int(selected["capacity"].max()),
            top_types=tuple((str(name), int(count)) for name, count in top_types),
        )

    @lru_cache(maxsize=512)
    def _traffic_load(
        self,
        departure_hour: int,
        destination_airport_id: int | None,
    ) -> TrafficLoadSummary:
        departure_hour = departure_hour % 24
        flights = self._filter_departures(destination_airport_id)
        destination_label = self._destination_label(destination_airport_id)
        empty_hours = tuple((hour, 0) for hour in range(24))
        if flights.empty:
            return TrafficLoadSummary(
                airport_iata=self._airport_iata,
                destination_label=destination_label,
                destination_airport_id=destination_airport_id,
                departure_hour=departure_hour,
                total_departures=0,
                active_days=0,
                departures_at_hour=0,
                avg_departures_at_hour_per_day=0,
                busiest_hour=None,
                busiest_hour_departures=0,
                hourly_departures=empty_hours,
            )

        hourly_counts = (
            flights["departure"].dt.hour.value_counts().reindex(range(24), fill_value=0)
        )
        active_days = int(flights["departure"].dt.date.nunique())
        departures_at_hour = int(hourly_counts.loc[departure_hour])
        busiest_hour = int(hourly_counts.idxmax())
        return TrafficLoadSummary(
            airport_iata=self._airport_iata,
            destination_label=destination_label,
            destination_airport_id=destination_airport_id,
            departure_hour=departure_hour,
            total_departures=len(flights),
            active_days=active_days,
            departures_at_hour=departures_at_hour,
            avg_departures_at_hour_per_day=round(
                departures_at_hour / active_days if active_days else 0,
                2,
            ),
            busiest_hour=busiest_hour,
            busiest_hour_departures=int(hourly_counts.loc[busiest_hour]),
            hourly_departures=tuple((int(hour), int(count)) for hour, count in hourly_counts.items()),
        )

    @lru_cache(maxsize=512)
    def _booking_load(
        self,
        aircraft_type_id: int | None,
        destination_airport_id: int | None,
    ) -> BookingLoadSummary:
        booking_path = self._data_dir / "flughafendb_large@booking@0.tsv.zst"
        columns = self._columns_for("booking")
        bookings = pd.read_csv(
            booking_path,
            sep="\t",
            names=columns,
            usecols=["flight_id", "price"],
            compression="zstd",
            na_values="\\N",
        )
        grouped = (
            bookings.groupby("flight_id")
            .agg(bookings=("flight_id", "size"), avg_price=("price", "mean"))
            .reset_index()
        )
        flight_capacity = self._flights()[["flight_id", "airplane_id", "to"]].merge(
            self._airplanes()[["airplane_id", "capacity", "type_id"]],
            on="airplane_id",
            how="left",
        )
        if aircraft_type_id is not None:
            flight_capacity = flight_capacity.loc[
                flight_capacity["type_id"].eq(aircraft_type_id)
            ]
        if destination_airport_id is not None:
            flight_capacity = flight_capacity.loc[
                flight_capacity["to"].eq(destination_airport_id)
            ]

        load = grouped.merge(flight_capacity, on="flight_id", how="inner")
        load = load.loc[load["capacity"].gt(0)]
        aircraft_label = self._aircraft_type_label(aircraft_type_id)
        destination_label = self._destination_label(destination_airport_id)

        if load.empty:
            return BookingLoadSummary(
                sampled_chunk="booking@0",
                aircraft_type=aircraft_label,
                destination_label=destination_label,
                sampled_bookings=0,
                sampled_flights=0,
                avg_bookings_per_flight=None,
                avg_load_factor_percent=None,
                median_load_factor_percent=None,
                high_load_flights_percent=None,
                note="Nur Booking-Chunk 0 geladen; keine passenden Fluege im Flight-Dump gefunden.",
            )

        load_factor = (load["bookings"] / load["capacity"] * 100).clip(upper=100)
        high_load_percent = float((load_factor >= 85).mean() * 100)
        return BookingLoadSummary(
            sampled_chunk="booking@0",
            aircraft_type=aircraft_label,
            destination_label=destination_label,
            sampled_bookings=int(load["bookings"].sum()),
            sampled_flights=len(load),
            avg_bookings_per_flight=round(float(load["bookings"].mean()), 1),
            avg_load_factor_percent=round(float(load_factor.mean()), 1),
            median_load_factor_percent=round(float(load_factor.median()), 1),
            high_load_flights_percent=round(high_load_percent, 1),
            note="Sample aus Booking-Chunk 0, damit die 55-Mio.-Zeilen-Tabelle nicht voll geladen wird.",
        )

    @lru_cache(maxsize=1)
    def _aircraft_options(self) -> tuple[SelectOption, ...]:
        merged = self._airplanes().merge(self._airplane_types(), on="type_id", how="left")
        grouped = (
            merged.groupby(["type_id", "identifier"], dropna=False)
            .agg(aircraft_count=("airplane_id", "size"), avg_capacity=("capacity", "mean"))
            .reset_index()
            .sort_values(["aircraft_count", "identifier"], ascending=[False, True])
        )
        return tuple(
            SelectOption(
                value=str(int(row.type_id)),
                label=(
                    f"{row.identifier or 'Unbekannt'} "
                    f"({row.avg_capacity:.0f} Sitze, {int(row.aircraft_count)} Flugzeuge)"
                ),
            )
            for row in grouped.itertuples(index=False)
        )

    @lru_cache(maxsize=1)
    def _weather_options(self) -> tuple[SelectOption, ...]:
        weather_path = self._data_dir / "flughafendb_large@weatherdata@@0.tsv.zst"
        columns = self._columns_for("weatherdata")
        values: set[str] = set()
        for chunk in pd.read_csv(
            weather_path,
            sep="\t",
            names=columns,
            usecols=["weather"],
            compression="zstd",
            na_values="\\N",
            chunksize=500_000,
        ):
            values.update(str(value) for value in chunk["weather"].dropna().unique())
        return (SelectOption(value="__all__", label="Alle Wetterlagen"),) + tuple(
            SelectOption(value=value, label=value) for value in sorted(values)
        )

    @lru_cache(maxsize=1)
    def _destination_options(self) -> tuple[SelectOption, ...]:
        destination_ids = sorted(int(value) for value in self._zrh_departures()["to"].unique())
        return (SelectOption(value="__all__", label="Alle Destinationen"),) + tuple(
            SelectOption(
                value=str(airport_id),
                label=self._destination_label(airport_id),
            )
            for airport_id in destination_ids
        )

    def _filter_departures(self, destination_airport_id: int | None) -> pd.DataFrame:
        flights = self._zrh_departures()
        if destination_airport_id is None:
            return flights
        return flights.loc[flights["to"].eq(destination_airport_id)].copy()

    def _aircraft_type_label(self, aircraft_type_id: int | None) -> str:
        if aircraft_type_id is None:
            return "Alle Flugzeugtypen"
        airplane_types = self._airplane_types().set_index("type_id")
        if aircraft_type_id not in airplane_types.index:
            return f"Typ {aircraft_type_id}"
        return str(airplane_types.loc[aircraft_type_id, "identifier"])

    def _destination_label(self, destination_airport_id: int | None) -> str:
        if destination_airport_id is None:
            return "Alle Destinationen"
        airports = self._airports().set_index("airport_id")
        if destination_airport_id not in airports.index:
            return f"Airport {destination_airport_id}"
        row = airports.loc[destination_airport_id]
        iata = row.get("iata")
        name = row.get("name")
        if pd.notna(iata):
            return f"{iata} - {name}"
        return str(name)

    @lru_cache(maxsize=1)
    def _flights(self) -> pd.DataFrame:
        columns = self._columns_for("flight")
        flights = pd.read_csv(
            self._data_dir / "flughafendb_large@flight@@0.tsv.zst",
            sep="\t",
            names=columns,
            usecols=["flight_id", "from", "to", "departure", "arrival", "airplane_id"],
            compression="zstd",
            na_values="\\N",
            parse_dates=["departure", "arrival"],
        )
        return flights

    @lru_cache(maxsize=1)
    def _zrh_departures(self) -> pd.DataFrame:
        return self._flights().loc[self._flights()["from"].eq(ZRH_AIRPORT_ID)].copy()

    @lru_cache(maxsize=1)
    def _airplanes(self) -> pd.DataFrame:
        columns = self._columns_for("airplane")
        airplanes = pd.read_csv(
            self._data_dir / "flughafendb_large@airplane@@0.tsv.zst",
            sep="\t",
            names=columns,
            compression="zstd",
            na_values="\\N",
        )
        airplanes["category"] = airplanes["capacity"].map(_capacity_category)
        return airplanes

    @lru_cache(maxsize=1)
    def _airplane_types(self) -> pd.DataFrame:
        columns = self._columns_for("airplane_type")
        return pd.read_csv(
            self._data_dir / "flughafendb_large@airplane_type@@0.tsv.zst",
            sep="\t",
            names=columns,
            usecols=["type_id", "identifier"],
            compression="zstd",
            na_values="\\N",
        )

    @lru_cache(maxsize=1)
    def _airports(self) -> pd.DataFrame:
        columns = self._columns_for("airport")
        return pd.read_csv(
            self._data_dir / "flughafendb_large@airport@@0.tsv.zst",
            sep="\t",
            names=columns,
            usecols=["airport_id", "iata", "name"],
            compression="zstd",
            na_values="\\N",
        )

    @lru_cache(maxsize=16)
    def _columns_for(self, table: str) -> list[str]:
        metadata_path = self._data_dir / f"flughafendb_large@{table}.json"
        with metadata_path.open(encoding="utf-8") as handle:
            return list(json.load(handle)["options"]["columns"])


def _angular_diff(values: pd.Series, direction_deg: float) -> pd.Series:
    return ((values - direction_deg + 180) % 360 - 180).abs()


def _weather_condition_mask(values: pd.Series, weather_condition: str) -> pd.Series:
    if weather_condition == "__all__":
        return pd.Series(True, index=values.index)
    return values.fillna("").eq(weather_condition)


def _weather_label(weather_condition: str) -> str:
    if weather_condition == "__all__":
        return "Alle Wetterlagen"
    return weather_condition


def _capacity_category(capacity: int | float) -> str:
    if capacity <= 100:
        return "light"
    if capacity <= 250:
        return "medium"
    return "heavy"


def _safe_average(total: float, count: int) -> float | None:
    if count == 0:
        return None
    return round(total / count, 1)
