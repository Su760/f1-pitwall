"""Bounded, sequential OpenF1 historical HTTP access (standard library only)."""

from __future__ import annotations

import json
import math
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http.client import HTTPException, IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINTS = (
    "sessions",
    "meetings",
    "drivers",
    "laps",
    "stints",
    "pit",
    "race_control",
    "weather",
    "session_result",
)
RESERVED_FIELDS = {"source_request", "source_row", "raw_json", "validation_errors"}


def validate_config(config: dict) -> None:
    """Reject configurations outside the approved bounded historical source."""
    if (
        not isinstance(config, dict)
        or type(config.get("schema_version")) is not int
        or config["schema_version"] != 1
    ):
        raise ValueError("config schema_version must be 1")
    if config.get("source_url") != "https://api.openf1.org/v1":
        raise ValueError("source_url must be the official OpenF1 historical API")
    if config.get("country_name") != "Bahrain" or config.get("session_name") != "Race":
        raise ValueError("selection must be Bahrain Race sessions")
    years = config.get("years")
    if (
        not isinstance(years, list)
        or not years
        or any(type(year) is not int or year not in (2023, 2024, 2025) for year in years)
        or len(years) != len(set(years))
    ):
        raise ValueError("years must be a nonempty unique subset of 2023–2025")
    for key, maximum in (
        ("requests_per_second", 3),
        ("requests_per_minute", 30),
        ("max_attempts", 10),
        ("max_response_bytes", None),
    ):
        value = config.get(key)
        if type(value) is not int or value <= 0 or (maximum and value > maximum):
            raise ValueError(f"invalid bounded integer configuration: {key}")
    for key in ("timeout_seconds", "backoff_seconds", "max_retry_after_seconds"):
        value = config.get(key)
        try:
            finite = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite or value < 0 or (key == "timeout_seconds" and value == 0):
            raise ValueError(f"invalid finite duration configuration: {key}")
    try:
        json.dumps(config, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ValueError("configuration must be finite JSON data") from error


def parse_rows(body: bytes) -> list[dict]:
    """Parse arrays without accepting non-JSON constants or ambiguous object keys."""

    def reject_constant(value):
        raise ValueError(f"nonfinite JSON value: {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("JSON number exceeds finite float range")
        return number

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    try:
        rows = json.loads(
            body,
            parse_constant=reject_constant,
            parse_float=finite_float,
            object_pairs_hook=unique_object,
        )
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"malformed source JSON: {error}") from error
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("malformed source data: expected an array of objects")
    if any(RESERVED_FIELDS.intersection(row) for row in rows):
        raise ValueError("malformed source data: reserved provenance field collision")
    return rows


@dataclass(frozen=True)
class HTTPResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    body_complete: bool = True
    body_error: str | None = None


@dataclass(frozen=True)
class Attempt:
    number: int
    status: str
    retrieved_at: str
    status_code: int | None
    body: bytes | None
    body_complete: bool
    error: str | None = None
    retry_after: str | None = None


@dataclass(frozen=True)
class FetchResult:
    rows: list[dict] | None
    attempts: list[Attempt]
    error: str | None = None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Redirects otherwise issue hidden, unbudgeted HTTP requests.
        return None


def urllib_transport(url: str, timeout: float, max_bytes: int) -> HTTPResponse:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "PitWall-Arena-F1/1 (historical audit)",
        },
    )
    try:
        response = build_opener(_NoRedirect()).open(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        chunks = []
        size = 0
        error = None
        try:
            while size <= max_bytes:
                chunk = response.read(min(65536, max_bytes + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
        except IncompleteRead as incomplete:
            chunks.append(incomplete.partial)
            error = f"IncompleteRead: {incomplete}"
        except (OSError, HTTPException) as incomplete:
            error = f"{type(incomplete).__name__}: {incomplete}"
        body = b"".join(chunks)
        declared_size = next(
            (value for key, value in response.headers.items() if key.lower() == "content-length"),
            None,
        )
        if declared_size is not None and error is None:
            try:
                if int(declared_size) != len(body):
                    error = "received bytes disagree with declared Content-Length"
            except (ValueError, TypeError):
                error = "invalid response Content-Length"
        return HTTPResponse(
            response.status,
            dict(response.headers),
            body,
            body_complete=error is None and len(body) <= max_bytes,
            body_error=error,
        )


class OpenF1Client:
    """One sequential rate budget shared by all requests and all retry attempts."""

    def __init__(
        self,
        config: dict,
        *,
        transport: Callable = urllib_transport,
        monotonic: Callable = time.monotonic,
        sleep: Callable = time.sleep,
        now: Callable = lambda: datetime.now(UTC),
    ):
        validate_config(config)
        self.config = json.loads(json.dumps(config))
        self.transport = transport
        self.monotonic = monotonic
        self.sleep = sleep
        self.now = now
        self._starts: deque[float] = deque()

    def _acquire(self) -> None:
        while True:
            now = self.monotonic()
            while self._starts and self._starts[0] <= now - 60:
                self._starts.popleft()
            waits = [0.0]
            if len(self._starts) >= self.config["requests_per_minute"]:
                waits.append(self._starts[0] + 60 - now)
            recent = [start for start in self._starts if start > now - 1]
            if len(recent) >= self.config["requests_per_second"]:
                waits.append(recent[0] + 1 - now)
            wait = max(waits)
            if wait <= 0:
                self._starts.append(now)
                return
            self.sleep(wait)

    def _retry_after(self, value: str) -> float:
        if value.strip().isdigit():
            delay = float(value.strip())
        else:
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    raise ValueError("missing timezone")
                delay = max(0.0, (date - self.now()).total_seconds())
            except (ValueError, TypeError, OverflowError) as error:
                raise ValueError(f"invalid Retry-After: {value!r}") from error
        if not math.isfinite(delay) or delay > self.config["max_retry_after_seconds"]:
            raise ValueError("Retry-After exceeds configured waiting budget")
        return delay

    def fetch(
        self, endpoint: str, params: dict, *, on_attempt: Callable | None = None
    ) -> FetchResult:
        if endpoint not in ENDPOINTS:
            raise ValueError(f"unsupported endpoint: {endpoint}")
        url = f"{self.config['source_url']}/{endpoint}?{urlencode(sorted(params.items()))}"
        attempts = []
        for number in range(1, self.config["max_attempts"] + 1):
            self._acquire()
            body = None
            body_complete = False
            status_code = None
            retry_after = None
            rows = None
            retry = False
            delay = self.config["backoff_seconds"] * 2 ** (number - 1)
            error = None
            try:
                response = self.transport(
                    url, self.config["timeout_seconds"], self.config["max_response_bytes"]
                )
                body = response.body
                body_complete = response.body_complete
                status_code = response.status_code
                retry_after = next(
                    (
                        str(value)
                        for key, value in response.headers.items()
                        if key.lower() == "retry-after"
                    ),
                    None,
                )
                if len(body) > self.config["max_response_bytes"]:
                    body_complete = False
                    status = "malformed"
                    error = "response exceeds configured byte limit; body is a received prefix"
                elif response.body_error is not None:
                    status = "transport_error"
                    error = response.body_error
                    retry = True
                elif not body_complete:
                    status = "malformed"
                    error = "response body is incomplete"
                elif not 200 <= status_code < 300:
                    status = "http_error"
                    error = f"HTTP {status_code} from {endpoint}"
                    retry = status_code == 429 or 500 <= status_code < 600
                else:
                    try:
                        rows = parse_rows(body)
                        status = "success"
                    except ValueError as invalid:
                        status = "malformed"
                        error = str(invalid)
            except (OSError, URLError, HTTPException) as transport_error:
                status = "transport_error"
                error = f"{type(transport_error).__name__}: {transport_error}"
                retry = True
            if retry and retry_after is not None and number < self.config["max_attempts"]:
                try:
                    delay = max(delay, self._retry_after(retry_after))
                except ValueError as invalid:
                    error = f"{error}; {invalid}"
                    retry = False
            attempt = Attempt(
                number,
                status,
                self.now().isoformat(),
                status_code,
                body,
                body_complete,
                error,
                retry_after,
            )
            attempts.append(attempt)
            if on_attempt is not None:
                on_attempt(attempt)
            if rows is not None:
                return FetchResult(rows, attempts)
            if not retry or number == self.config["max_attempts"]:
                return FetchResult(None, attempts, error)
            self.sleep(delay)
        raise AssertionError("validated attempt budget must execute at least once")
