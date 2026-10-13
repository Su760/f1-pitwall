"""Historical tests cannot reach the network; fixtures are intentionally artificial."""

import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Historical CI is offline: unexpected network access")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def cached_source(tmp_path):
    from pitwall_historical.cache import import_snapshot
    from pitwall_historical.client import HTTPResponse, OpenF1Client

    config = json.loads(Path("historical/config.json").read_text())
    config["years"] = [2024]
    now = [0.0]

    def transport(url, timeout, max_bytes):
        parsed = urlparse(url)
        endpoint = parsed.path.rsplit("/", 1)[-1]
        params = parse_qs(parsed.query)
        identity = {"session_key": 123, "meeting_key": 456}
        sources = {
            "sessions": [
                {
                    **identity,
                    "year": 2024,
                    "country_name": "Bahrain",
                    "session_name": "Race",
                    "session_type": "Race",
                    "circuit_key": 789,
                    "date_start": "2024-01-01T12:00:00Z",
                    "date_end": "2024-01-01T12:10:00Z",
                }
            ],
            "meetings": [
                {
                    "meeting_key": 456,
                    "circuit_key": 789,
                    "year": 2024,
                    "meeting_name": "Artificial unit-test meeting",
                    "date_start": "2024-01-01T12:00:00Z",
                }
            ],
            "drivers": [{**identity, "driver_number": 7, "full_name": "Fixture Driver"}],
            "laps": [
                {
                    **identity,
                    "driver_number": 7,
                    "lap_number": 1,
                    "date_start": "2024-01-01T12:00:00Z",
                    "lap_duration": 90.0,
                    "is_pit_out_lap": False,
                }
            ],
            "stints": [
                {
                    **identity,
                    "driver_number": 7,
                    "stint_number": 1,
                    "lap_start": 1,
                    "lap_end": 1,
                    "tyre_age_at_start": 0,
                    "compound": "SOFT",
                }
            ],
            "pit": [],
            "weather": [{**identity, "date": "2024-01-01T12:00:00Z", "rainfall": 0}],
            "race_control": [
                {
                    **identity,
                    "date": "2024-01-01T12:00:00Z",
                    "flag": "GREEN",
                    "category": "Flag",
                    "scope": "Track",
                    "message": "GREEN LIGHT",
                }
            ],
            "session_result": [
                {
                    **identity,
                    "driver_number": 7,
                    "number_of_laps": 1,
                    "dnf": False,
                    "dns": False,
                    "dsq": False,
                }
            ],
        }
        assert params
        return HTTPResponse(200, {}, json.dumps(sources[endpoint]).encode())

    def sleep(delay):
        now[0] += delay

    client = OpenF1Client(
        config,
        transport=transport,
        monotonic=lambda: now[0],
        sleep=sleep,
        now=lambda: datetime(2026, 10, 13, tzinfo=UTC),
    )
    return import_snapshot(tmp_path / "cache", config, client=client)
