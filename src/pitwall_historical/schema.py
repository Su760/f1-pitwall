"""Explicit source column contracts; no inference from observed non-null rows."""

from __future__ import annotations

SCHEMAS: dict[str, dict[str, str]] = {
    "sessions": {
        "session_key": "int",
        "meeting_key": "int",
        "circuit_key": "int",
        "circuit_short_name": "str",
        "country_name": "str",
        "location": "str",
        "year": "int",
        "session_name": "str",
        "session_type": "str",
        "date_start": "timestamp",
        "date_end": "timestamp",
        "is_cancelled": "bool",
    },
    "meetings": {
        "meeting_key": "int",
        "circuit_key": "int",
        "circuit_short_name": "str",
        "country_name": "str",
        "location": "str",
        "year": "int",
        "meeting_name": "str",
        "meeting_official_name": "str",
        "date_start": "timestamp",
        "date_end": "timestamp",
    },
    "drivers": {
        "session_key": "int",
        "meeting_key": "int",
        "driver_number": "int",
        "full_name": "str",
        "name_acronym": "str",
        "team_name": "str",
    },
    "laps": {
        "session_key": "int",
        "meeting_key": "int",
        "driver_number": "int",
        "lap_number": "int",
        "date_start": "timestamp",
        "lap_duration": "float",
        "duration_sector_1": "float",
        "duration_sector_2": "float",
        "duration_sector_3": "float",
        "is_pit_out_lap": "bool",
    },
    "stints": {
        "session_key": "int",
        "meeting_key": "int",
        "driver_number": "int",
        "stint_number": "int",
        "lap_start": "int",
        "lap_end": "int",
        "compound": "str",
        "tyre_age_at_start": "int",
    },
    "pit": {
        "session_key": "int",
        "meeting_key": "int",
        "driver_number": "int",
        "lap_number": "int",
        "date": "timestamp",
        "lane_duration": "float",
        "pit_duration": "float",
        "stop_duration": "float",
    },
    "race_control": {
        "session_key": "int",
        "meeting_key": "int",
        "date": "timestamp",
        "category": "str",
        "flag": "str",
        "scope": "str",
        "driver_number": "int",
        "sector": "int",
        "message": "str",
        "lap_number": "int",
    },
    "weather": {
        "session_key": "int",
        "meeting_key": "int",
        "date": "timestamp",
        "rainfall": "int",
        "air_temperature": "float",
        "track_temperature": "float",
        "humidity": "float",
        "pressure": "float",
        "wind_direction": "float",
        "wind_speed": "float",
    },
    "session_result": {
        "session_key": "int",
        "meeting_key": "int",
        "driver_number": "int",
        "number_of_laps": "int",
        "dnf": "bool",
        "dns": "bool",
        "dsq": "bool",
        "position": "int",
        "duration": "float",
    },
}

LOGICAL_KEYS: dict[str, tuple[str, ...]] = {
    "sessions": ("session_key",),
    "meetings": ("meeting_key",),
    "drivers": ("session_key", "driver_number"),
    "laps": ("session_key", "driver_number", "lap_number"),
    "stints": ("session_key", "driver_number", "stint_number"),
    "pit": ("session_key", "driver_number", "lap_number", "date"),
    "race_control": (
        "session_key",
        "date",
        "category",
        "flag",
        "scope",
        "driver_number",
        "sector",
        "message",
    ),
    "weather": ("session_key", "date"),
    "session_result": ("session_key", "driver_number"),
}

# Nullable storage is intentional, even when a purpose requires the field.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "sessions": (
        "session_key",
        "meeting_key",
        "circuit_key",
        "country_name",
        "year",
        "session_name",
        "session_type",
        "date_start",
        "date_end",
    ),
    "meetings": ("meeting_key", "circuit_key", "year", "meeting_name", "date_start"),
    "drivers": ("session_key", "meeting_key", "driver_number", "full_name"),
    "laps": (
        "session_key",
        "meeting_key",
        "driver_number",
        "lap_number",
        "date_start",
        "lap_duration",
        "is_pit_out_lap",
    ),
    "stints": tuple(SCHEMAS["stints"]),
    "pit": ("session_key", "meeting_key", "driver_number", "lap_number", "date"),
    "race_control": ("session_key", "meeting_key", "date", "category", "message"),
    "weather": ("session_key", "meeting_key", "date", "rainfall"),
    "session_result": (
        "session_key",
        "meeting_key",
        "driver_number",
        "number_of_laps",
        "dnf",
        "dns",
        "dsq",
    ),
}


def arrow_schema(table: str):
    """Import the optional dependency only when Parquet is requested."""
    import pyarrow as pa

    types = {
        "int": pa.int64(),
        "float": pa.float64(),
        "str": pa.string(),
        "bool": pa.bool_(),
        "timestamp": pa.timestamp("us", tz="UTC"),
    }
    fields = [(name, types[kind]) for name, kind in SCHEMAS[table].items()]
    if table == "pit":
        fields += [("effective_lane_duration", pa.float64()), ("lane_duration_source", pa.string())]
    fields += [
        ("source_request", pa.string()),
        ("source_row", pa.int64()),
        ("raw_json", pa.string()),
        ("validation_errors", pa.list_(pa.string())),
    ]
    return pa.schema(fields, metadata={b"pitwall_schema_version": b"1", b"table": table.encode()})
