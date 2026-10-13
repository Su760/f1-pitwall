"""Immutable raw snapshots and verified offline recovery of source evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from pitwall_historical.client import (
    ENDPOINTS,
    Attempt,
    OpenF1Client,
    parse_rows,
    validate_config,
)

SCHEMA_VERSION = 1
SESSION_ENDPOINTS = (
    "drivers",
    "laps",
    "stints",
    "pit",
    "race_control",
    "weather",
    "session_result",
)


class CacheError(ValueError):
    """Source evidence or its claimed provenance cannot be verified."""


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _request_id(endpoint: str, params: dict) -> str:
    return endpoint + "-" + "-".join(f"{key}-{value}" for key, value in sorted(params.items()))


def _discovery(config: dict) -> list[tuple[str, dict]]:
    return [
        (
            "sessions",
            {
                "country_name": config["country_name"],
                "session_name": config["session_name"],
                "year": year,
            },
        )
        for year in config["years"]
    ]


def _session_requests(sessions: list[dict]) -> list[tuple[str, dict]]:
    requests = []
    meetings = set()
    for session in sessions:
        if session["meeting_key"] not in meetings:
            requests.append(("meetings", {"meeting_key": session["meeting_key"]}))
            meetings.add(session["meeting_key"])
        requests.extend(
            (endpoint, {"session_key": session["session_key"]}) for endpoint in SESSION_ENDPOINTS
        )
    return requests


def _resolve(rows: list[dict], year: int, config: dict) -> dict:
    if len(rows) != 1:
        raise CacheError(f"{year}: expected exactly one Bahrain Race session, received {len(rows)}")
    session = rows[0]
    for field in ("session_key", "meeting_key", "circuit_key", "year"):
        if type(session.get(field)) is not int or session[field] <= 0:
            raise CacheError(f"{year}: missing/invalid selection field {field}")
    if (
        session["year"] != year
        or session.get("country_name") != config["country_name"]
        or session.get("session_name") != config["session_name"]
    ):
        raise CacheError(f"{year}: returned session metadata does not match selection")
    return session


def _scope(rows: list[dict], params: dict) -> None:
    for key in ("session_key", "meeting_key"):
        if key in params:
            for number, row in enumerate(rows):
                value = row.get(key)
                if value is not None and (type(value) is not int or value != params[key]):
                    raise CacheError(f"row {number}: {key} mismatches requested {params[key]}")


def _save_manifest(snapshot: Path, manifest: dict) -> None:
    pending = snapshot / ".manifest.pending"
    pending.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")
    pending.replace(snapshot / "manifest.json")


def import_snapshot(cache_root: Path, config: dict, *, client=None) -> Path:
    """Fetch a fresh snapshot; failures are persisted and returned for offline audit."""
    validate_config(config)
    config = json.loads(json.dumps(config))
    if client is None:
        client = OpenF1Client(config)
    elif client.config != config:
        raise ValueError("client configuration must match the snapshot configuration")
    identity = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:12]
    snapshot = Path(cache_root) / identity
    snapshot.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": identity,
        "source_url": config["source_url"],
        "source_identity": "OpenF1 historical API",
        "config": config,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "in_progress",
        "sessions": [],
        "requests": [],
        "errors": [],
    }
    _save_manifest(snapshot, manifest)

    def fetch(endpoint: str, params: dict) -> list[dict] | None:
        request = {
            "id": _request_id(endpoint, params),
            "endpoint": endpoint,
            "params": params,
            "status": "in_progress",
            "raw_path": None,
            "sha256": None,
            "byte_count": None,
            "retrieved_at": None,
            "row_count": None,
            "attempts": [],
        }
        manifest["requests"].append(request)
        _save_manifest(snapshot, manifest)

        def save_attempt(attempt: Attempt) -> None:
            evidence = asdict(attempt)
            body = evidence.pop("body")
            evidence.update(raw_path=None, sha256=None, byte_count=None)
            if body is not None:
                relative = f"raw/{request['id']}/attempt-{attempt.number:03d}.json"
                path = snapshot / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as handle:
                    handle.write(body)
                evidence.update(raw_path=relative, sha256=_digest(body), byte_count=len(body))
            request["attempts"].append(evidence)
            for key in ("raw_path", "sha256", "byte_count", "retrieved_at"):
                request[key] = evidence[key]
            _save_manifest(snapshot, manifest)

        try:
            result = client.fetch(endpoint, params, on_attempt=save_attempt)
            if result.error is not None:
                raise CacheError(result.error)
            _scope(result.rows, params)
            request["status"] = "success"
            request["row_count"] = len(result.rows)
            _save_manifest(snapshot, manifest)
            return result.rows
        except Exception as error:
            # Never turn a request exception into a complete or invented table.
            request["status"] = "failed"
            request["error"] = f"{type(error).__name__}: {error}"
            manifest["errors"].append(f"{request['id']}: {request['error']}")
            _save_manifest(snapshot, manifest)
            return None

    for endpoint, params in _discovery(config):
        rows = fetch(endpoint, params)
        if rows is not None:
            try:
                manifest["sessions"].append(_resolve(rows, params["year"], config))
            except CacheError as error:
                manifest["errors"].append(str(error))
        _save_manifest(snapshot, manifest)
    sessions = manifest["sessions"]
    if len({session["circuit_key"] for session in sessions}) > 1:
        manifest["errors"].append("selection does not resolve to one common circuit")
        manifest["sessions"] = []
    elif len({session["session_key"] for session in sessions}) != len(sessions):
        manifest["errors"].append("selection repeats a session key across years")
        manifest["sessions"] = []
    _save_manifest(snapshot, manifest)
    for endpoint, params in _session_requests(manifest["sessions"]):
        fetch(endpoint, params)
    manifest["status"] = (
        "complete" if not manifest["errors"] else "partial" if manifest["sessions"] else "failed"
    )
    manifest["finished_at"] = datetime.now(UTC).isoformat()
    _save_manifest(snapshot, manifest)
    return snapshot


def _read_body(snapshot: Path, record: dict, limit: int) -> bytes | None:
    relative = record.get("raw_path")
    if relative is None:
        if record.get("sha256") is not None or record.get("byte_count") is not None:
            raise CacheError("body-less record has a hash or byte count")
        return None
    if not isinstance(relative, str):
        raise CacheError("raw_path must be a relative path")
    parts = PurePosixPath(relative)
    if (
        parts.is_absolute()
        or ".." in parts.parts
        or not parts.parts
        or parts.parts[0] != "raw"
        or "\\" in relative
    ):
        raise CacheError("unsafe raw path")
    path = snapshot / relative
    if not path.resolve().is_relative_to(snapshot.resolve()):
        raise CacheError("raw path escapes snapshot")
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent != snapshot.parent):
        raise CacheError("raw evidence cannot use symlinks")
    try:
        if path.stat().st_size > limit + 1:
            raise CacheError("cached body exceeds configured response bound")
        body = path.read_bytes()
    except OSError as error:
        raise CacheError(f"cannot read raw evidence: {error}") from error
    if type(record.get("byte_count")) is not int or len(body) != record["byte_count"]:
        raise CacheError("raw byte count mismatch")
    if _digest(body) != record.get("sha256"):
        raise CacheError("raw SHA-256 mismatch")
    return body


def _timestamp(value) -> None:
    try:
        if not isinstance(value, str) or datetime.fromisoformat(value).tzinfo is None:
            raise ValueError("timestamp must include timezone")
    except ValueError as error:
        raise CacheError("invalid retrieval timestamp") from error


def load_snapshot(snapshot: Path) -> tuple[dict, dict[str, list[dict]]]:
    """Validate recorded evidence before exposing rows, including partial snapshots."""
    snapshot = Path(snapshot)
    try:
        manifest = json.loads((snapshot / "manifest.json").read_bytes())
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != SCHEMA_VERSION
        ):
            raise CacheError("unsupported manifest schema")
        config = manifest["config"]
        validate_config(config)
        if manifest.get("source_url") != config["source_url"]:
            raise CacheError("source identity mismatch")
        if manifest.get("snapshot_id") != snapshot.name:
            raise CacheError("snapshot directory identity mismatch")
        if manifest.get("status") not in {"complete", "partial", "failed", "in_progress"}:
            raise CacheError("invalid import status")
        if not isinstance(manifest.get("sessions"), list):
            raise CacheError("missing resolved sessions")
        if not isinstance(manifest.get("requests"), list):
            raise CacheError("missing requests")
        if not isinstance(manifest.get("errors"), list):
            raise CacheError("missing import errors")
        return _validate_requests(snapshot, manifest, config)
    except (KeyError, TypeError, ValueError, OSError) as error:
        if isinstance(error, CacheError):
            raise
        raise CacheError(f"invalid cached evidence: {error}") from error


def _validate_requests(snapshot: Path, manifest: dict, config: dict) -> tuple[dict, dict]:
    tables = {endpoint: [] for endpoint in ENDPOINTS}
    requests = {}
    raw_by_request = {}
    seen_paths = set()
    for request in manifest["requests"]:
        if not isinstance(request, dict):
            raise CacheError("invalid request record")
        endpoint, params = request["endpoint"], request["params"]
        if endpoint not in ENDPOINTS or not isinstance(params, dict):
            raise CacheError("invalid request endpoint or parameters")
        identity = _request_id(endpoint, params)
        if request.get("id") != identity or identity in requests:
            raise CacheError("duplicate or mismatched request identity")
        requests[identity] = request
        if request.get("status") not in {"success", "failed", "in_progress"}:
            raise CacheError("invalid request status")
        attempts = request.get("attempts")
        if not isinstance(attempts, list) or len(attempts) > config["max_attempts"]:
            raise CacheError("invalid attempt budget")
        for number, attempt in enumerate(attempts, 1):
            if not isinstance(attempt, dict) or attempt.get("number") != number:
                raise CacheError("invalid attempt ordering")
            if attempt.get("status") not in {
                "success",
                "http_error",
                "transport_error",
                "malformed",
            }:
                raise CacheError("invalid attempt status")
            _timestamp(attempt.get("retrieved_at"))
            body = _read_body(snapshot, attempt, config["max_response_bytes"])
            if attempt.get("raw_path") is not None:
                if attempt["raw_path"] in seen_paths:
                    raise CacheError("raw response path reused across attempts")
                seen_paths.add(attempt["raw_path"])
            if type(attempt.get("body_complete")) is not bool:
                raise CacheError("missing body completeness")
            if attempt["status"] == "success":
                if (
                    body is None
                    or not attempt["body_complete"]
                    or type(attempt.get("status_code")) is not int
                    or not 200 <= attempt["status_code"] < 300
                ):
                    raise CacheError("successful attempt lacks a complete HTTP success body")
                parse_rows(body)
        if attempts:
            for key in ("raw_path", "sha256", "byte_count", "retrieved_at"):
                if request.get(key) != attempts[-1].get(key):
                    raise CacheError(f"request/attempt {key} mismatch")
        elif request["status"] == "success":
            raise CacheError("successful request has no attempts")
        body = _read_body(snapshot, request, config["max_response_bytes"])
        if request["status"] == "success":
            if not attempts or attempts[-1]["status"] != "success" or body is None:
                raise CacheError("request success is unsupported by attempts")
            rows = parse_rows(body)
            if type(request.get("row_count")) is not int or request["row_count"] != len(rows):
                raise CacheError("raw row count mismatch")
            _scope(rows, params)
            raw_by_request[identity] = rows
            tables[endpoint].extend(
                {**row, "source_request": identity, "source_row": index}
                for index, row in enumerate(rows)
            )
        elif request["status"] == "failed" and not request.get("error"):
            raise CacheError("failed request has no error")

    resolved = []
    selection_errors = []
    for endpoint, params in _discovery(config):
        rows = raw_by_request.get(_request_id(endpoint, params))
        if rows is not None:
            try:
                resolved.append(_resolve(rows, params["year"], config))
            except CacheError as error:
                selection_errors.append(str(error))
    if len({row["circuit_key"] for row in resolved}) > 1 or len(
        {row["session_key"] for row in resolved}
    ) != len(resolved):
        resolved = []
        selection_errors.append("selection does not identify unique sessions at one circuit")
    if manifest["sessions"] != resolved:
        if manifest["status"] != "in_progress":
            raise CacheError("resolved sessions differ from verified source metadata")
        # A crash can occur between persisting a successful response and its selection.
        if any(session not in resolved for session in manifest["sessions"]):
            raise CacheError("in-progress selection is unsupported by source metadata")
    expected = {
        _request_id(endpoint, params): (endpoint, params)
        for endpoint, params in _discovery(config) + _session_requests(resolved)
    }
    if set(requests) - set(expected):
        raise CacheError("unexpected request outside configured selection")
    if manifest["status"] != "in_progress" and set(requests) != set(expected):
        raise CacheError("snapshot is missing expected request records")
    if manifest["status"] == "complete":
        if (
            manifest["errors"]
            or selection_errors
            or len(resolved) != len(config["years"])
            or any(request["status"] != "success" for request in requests.values())
        ):
            raise CacheError("complete status contradicts verified source evidence")
    elif manifest["status"] in {"partial", "failed"}:
        if not manifest["errors"]:
            raise CacheError("incomplete snapshot is missing failure evidence")
        if manifest["status"] == "failed" and resolved:
            raise CacheError("failed status contradicts resolved partial selection")
        if manifest["status"] == "partial" and not resolved:
            raise CacheError("partial status has no resolved selection")
    return manifest, tables
