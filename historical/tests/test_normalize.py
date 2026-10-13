"""Small artificial source-shaped fixtures, never replacement observations."""

import json
from datetime import UTC, datetime

import pyarrow.parquet as pq
import pytest

from pitwall_historical.normalize import normalize_tables, write_tables


def row(**values):
    return {"source_request": "r0", "source_row": 0, **values}


def test_null_absent_invalid_and_unknown_fields_preserved():
    original = row(
        session_key=123,
        driver_number=True,
        lap_number=2,
        lap_duration=None,
        date_start="2024-03-02T15:02:00+03:00",
        is_pit_out_lap="false",
        extra="evidence",
    )
    lap = normalize_tables({"laps": [original]})["laps"][0]
    assert lap["lap_duration"] is None
    assert lap["driver_number"] is None
    assert lap["is_pit_out_lap"] is None
    assert lap["date_start"] == datetime(2024, 3, 2, 12, 2, tzinfo=UTC)
    assert {"invalid:driver_number", "invalid:is_pit_out_lap"} <= set(lap["validation_errors"])
    raw = json.loads(lap["raw_json"])
    assert raw["extra"] == "evidence"
    assert raw["lap_duration"] is None
    assert "meeting_key" not in raw
    assert "source_row" not in raw
    assert original["is_pit_out_lap"] == "false"


@pytest.mark.parametrize("value", ["2024-03-02T12:00:00", "bad", 123])
def test_naive_or_invalid_dates_are_unknown(value):
    lap = normalize_tables({"laps": [row(date_start=value)]})["laps"][0]
    assert lap["date_start"] is None
    assert "invalid:date_start" in lap["validation_errors"]


def test_pit_alias_current_precedence_and_conflict():
    rows = [
        row(lane_duration=22.1, pit_duration=22.1),
        row(pit_duration=24.3),
        row(lane_duration=22.1, pit_duration=25, stop_duration=None),
        row(lane_duration=-1, pit_duration=20),
    ]
    pits = normalize_tables({"pit": rows})["pit"]
    assert [r["effective_lane_duration"] for r in pits] == [22.1, 24.3, 22.1, 20]
    assert [r["lane_duration_source"] for r in pits] == [
        "lane_duration",
        "pit_duration",
        "lane_duration",
        "pit_duration",
    ]
    assert all(r["stop_duration"] is None for r in pits)
    assert "pit_duration_alias_conflict" in pits[2]["validation_errors"]
    assert "invalid:lane_duration" in pits[3]["validation_errors"]


def test_parquet_has_explicit_nullable_types_and_preserves_duplicates(tmp_path):
    source = row(session_key=123, driver_number=7, lap_number=1, lap_duration=None)
    tables = normalize_tables({"laps": [source, source]})
    evidence = write_tables(tables, tmp_path)
    laps = pq.read_table(tmp_path / "laps.parquet")
    assert laps.num_rows == 2
    assert str(laps.schema.field("lap_duration").type) == "double"
    assert str(laps.schema.field("date_start").type) == "timestamp[us, tz=UTC]"
    assert laps.column("lap_duration").null_count == 2
    assert evidence["laps"]["rows"] == 2
    assert pq.read_table(tmp_path / "weather.parquet").num_rows == 0


def test_invalid_ranges_are_unknown_with_raw_evidence():
    rows = normalize_tables(
        {
            "stints": [row(lap_start=0, tyre_age_at_start=-1, stint_number=1)],
            "weather": [row(rainfall=2, humidity=101, wind_direction=360)],
        }
    )
    assert rows["stints"][0]["lap_start"] is None
    assert rows["stints"][0]["tyre_age_at_start"] is None
    assert rows["weather"][0]["rainfall"] is None
    assert rows["weather"][0]["humidity"] is None
    assert rows["weather"][0]["wind_direction"] is None


def test_nonfinite_json_is_explicitly_rejected():
    with pytest.raises(ValueError):
        normalize_tables({"laps": [row(lap_duration=float("inf"))]})
