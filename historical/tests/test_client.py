"""Offline HTTP boundary checks with source-shaped response bodies."""

import json
from datetime import UTC, datetime, timedelta
from http.client import IncompleteRead
from pathlib import Path
from types import SimpleNamespace

import pytest

from pitwall_historical.client import HTTPResponse, OpenF1Client, urllib_transport


def config(**overrides):
    values = json.loads(Path("historical/config.json").read_text())
    values.update(overrides)
    return values


class Clock:
    def __init__(self):
        self.seconds = 0.0

    def monotonic(self):
        return self.seconds

    def sleep(self, seconds):
        assert seconds >= 0
        self.seconds += seconds

    def now(self):
        return datetime(2026, 10, 13, tzinfo=UTC) + timedelta(seconds=self.seconds)


def client_for(responses, **overrides):
    clock = Clock()
    calls = []
    iterator = iter(responses)

    def transport(url, timeout, max_bytes):
        calls.append((clock.seconds, url, timeout, max_bytes))
        response = next(iterator)
        if isinstance(response, Exception):
            raise response
        return response

    client = OpenF1Client(
        config(**overrides),
        transport=transport,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        now=clock.now,
    )
    return client, calls, clock


def test_every_attempt_obeys_both_rolling_limits():
    client, calls, _ = client_for([HTTPResponse(200, {}, b"[]")] * 34)
    for _ in range(34):
        assert client.fetch("laps", {"session_key": 1}).error is None
    times = [call[0] for call in calls]
    assert times[:4] == [0, 0, 0, 1]
    assert times[30] >= 60
    for i, time in enumerate(times):
        assert sum(time - 1 < earlier <= time for earlier in times[: i + 1]) <= 3
        assert sum(time - 60 < earlier <= time for earlier in times[: i + 1]) <= 30


def test_retries_are_bounded_and_save_every_attempt_before_wait():
    client, calls, clock = client_for([HTTPResponse(503, {}, b"busy")] * 4)
    saved = []
    result = client.fetch(
        "laps", {"session_key": 1}, on_attempt=lambda a: saved.append((clock.seconds, a.body))
    )
    assert result.rows is None
    assert "503" in result.error
    assert [call[0] for call in calls] == [0, 2, 6, 14]
    assert saved == [(0, b"busy"), (2, b"busy"), (6, b"busy"), (14, b"busy")]


@pytest.mark.parametrize("header", ["7", "Tue, 13 Oct 2026 00:00:07 GMT"])
def test_retry_after_delta_and_http_date(header):
    client, calls, _ = client_for(
        [
            HTTPResponse(429, {"Retry-After": header}, b"rate limit"),
            HTTPResponse(200, {}, b'[{"lap_duration":null}]'),
        ]
    )
    result = client.fetch("laps", {"session_key": 1})
    assert result.rows == [{"lap_duration": None}]
    assert [call[0] for call in calls] == [0, 7]


def test_excessive_retry_after_fails_without_early_retry():
    client, calls, _ = client_for([HTTPResponse(429, {"retry-after": "121"}, b"busy")])
    result = client.fetch("laps", {"session_key": 1})
    assert len(calls) == 1
    assert "Retry-After" in result.error
    assert result.rows is None


@pytest.mark.parametrize("body", [b"not-json", b"{}", b"[null]", b"[NaN]", b"[{}] trailing"])
def test_malformed_data_is_explicit_and_not_retried(body):
    client, calls, _ = client_for([HTTPResponse(200, {}, body)])
    result = client.fetch("laps", {"session_key": 1})
    assert len(calls) == 1
    assert result.rows is None
    assert "malformed" in result.error.lower()
    assert result.attempts[0].body == body


def test_ambiguous_json_keys_fail_without_overwriting_evidence():
    client, calls, _ = client_for([HTTPResponse(200, {}, b'[{"lap_number":1,"lap_number":2}]')])
    result = client.fetch("laps", {"session_key": 1})
    assert result.rows is None
    assert "duplicate JSON object key" in result.error
    assert len(calls) == 1


def test_timeout_retry_and_configuration_reaches_transport():
    client, calls, _ = client_for([TimeoutError("read timed out"), HTTPResponse(200, {}, b"[]")])
    result = client.fetch("laps", {"session_key": 1})
    assert result.rows == []
    assert result.attempts[0].body is None
    assert result.attempts[0].status == "transport_error"
    assert calls[0][2:] == (30, 20000000)
    assert calls[1][0] == 2


def test_transport_preserves_partial_bytes_and_retries_incomplete_body(monkeypatch):
    class BrokenResponse:
        status = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            raise IncompleteRead(b'[{"lap_number":', 10)

    monkeypatch.setattr(
        "pitwall_historical.client.build_opener",
        lambda *_: SimpleNamespace(open=lambda *args, **kwargs: BrokenResponse()),
    )
    response = urllib_transport("https://api.openf1.org/v1/laps", 30, 1000)
    assert response.body == b'[{"lap_number":'
    assert response.body_complete is False
    client, calls, _ = client_for([response, HTTPResponse(200, {}, b"[]")])
    result = client.fetch("laps", {"session_key": 1})
    assert result.rows == []
    assert len(calls) == 2
    assert result.attempts[0].body == b'[{"lap_number":'
    assert result.attempts[0].status == "transport_error"


def test_declared_content_length_detects_truncation_even_for_valid_json(monkeypatch):
    class ShortResponse:
        status = 200
        headers = {"Content-Length": "20"}

        def __init__(self):
            self.chunks = iter([b"[]", b""])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return next(self.chunks)

    monkeypatch.setattr(
        "pitwall_historical.client.build_opener",
        lambda *_: SimpleNamespace(open=lambda *args, **kwargs: ShortResponse()),
    )
    response = urllib_transport("https://api.openf1.org/v1/laps", 30, 1000)
    assert response.body == b"[]"
    assert response.body_complete is False
    assert "Content-Length" in response.body_error


def test_response_limit_and_nontransient_http_error_fail_without_retry():
    for response, overrides in [
        (HTTPResponse(200, {}, b"[{},{}]"), {"max_response_bytes": 5}),
        (HTTPResponse(403, {}, b"forbidden"), {}),
    ]:
        client, calls, _ = client_for([response], **overrides)
        result = client.fetch("laps", {"session_key": 1})
        assert result.error
        assert result.rows is None
        assert len(calls) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"requests_per_second": 4},
        {"requests_per_minute": 31},
        {"max_attempts": 0},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("nan")},
        {"years": [2023, 2023]},
        {"source_url": "http://api.openf1.org/v1"},
        {"max_response_bytes": True},
    ],
)
def test_invalid_or_unbounded_config_rejected(overrides):
    with pytest.raises(ValueError):
        OpenF1Client(config(**overrides))


@pytest.mark.parametrize("key", ["timeout_seconds", "backoff_seconds", "max_retry_after_seconds"])
def test_oversized_json_integer_duration_reports_validation_error(key):
    with pytest.raises(ValueError, match="invalid finite duration configuration"):
        OpenF1Client(config(**{key: 10**400}))


def test_cli_rejects_oversized_config_duration_without_traceback(tmp_path, capsys):
    from pitwall_historical.__main__ import main

    path = tmp_path / "config.json"
    path.write_text(json.dumps(config(timeout_seconds=10**400)))
    status = main(["import", "--config", str(path), "--cache", str(tmp_path / "cache")])
    assert status == 2
    error = capsys.readouterr().err
    assert "Historical audit failed" in error
    assert "Traceback" not in error
    assert not (tmp_path / "cache").exists()
