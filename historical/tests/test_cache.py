"""Snapshot integrity and truthful completion using small synthetic source data."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from pitwall_historical.cache import CacheError, import_snapshot, load_snapshot
from pitwall_historical.client import HTTPResponse, OpenF1Client


def config():
    return json.loads(Path("historical/config.json").read_text())


def source_client(*, failed=None, bad_discovery=None, duplicate=False, mutate=None):
    times = [0.0]

    def transport(url, timeout, max_bytes):
        parsed = urlparse(url)
        endpoint = parsed.path.rsplit("/", 1)[-1]
        params = parse_qs(parsed.query)
        if endpoint == failed:
            return HTTPResponse(403, {}, b'{"error":"fixture unavailable"}')
        if endpoint == "sessions":
            year = int(params["year"][0])
            body = [
                {
                    "session_key": year * 10,
                    "meeting_key": year,
                    "circuit_key": 99,
                    "year": year,
                    "country_name": "Bahrain",
                    "session_name": "Race",
                }
            ]
            if bad_discovery == year:
                body = []
            if duplicate:
                body *= 2
        elif endpoint == "meetings":
            body = [{"meeting_key": int(params["meeting_key"][0]), "circuit_key": 99}]
        elif endpoint == "laps":
            body = [
                {
                    "session_key": int(params["session_key"][0]),
                    "driver_number": 4,
                    "lap_number": 1,
                    "lap_duration": None,
                }
            ]
        else:
            body = []
        if mutate is not None:
            body = mutate(endpoint, body)
        return HTTPResponse(200, {}, json.dumps(body).encode())

    def sleep(seconds):
        times[0] += seconds

    return OpenF1Client(
        config(),
        transport=transport,
        monotonic=lambda: times[0],
        sleep=sleep,
        now=lambda: datetime(2026, 10, 13, tzinfo=UTC),
    )


def save_manifest(snapshot, manifest):
    (snapshot / "manifest.json").write_text(json.dumps(manifest))


def test_import_resolves_source_keys_and_offline_preserves_rows(tmp_path):
    snapshot = import_snapshot(tmp_path, config(), client=source_client())
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "complete"
    assert [s["session_key"] for s in manifest["sessions"]] == [20230, 20240, 20250]
    assert len(manifest["requests"]) == 27
    assert len(tables["laps"]) == 3
    assert tables["laps"][0]["lap_duration"] is None
    assert tables["laps"][0]["source_row"] == 0
    assert tables["laps"][0]["source_request"]
    assert all(request["sha256"] for request in manifest["requests"])


def test_refresh_creates_new_snapshot_without_altering_prior_evidence(tmp_path):
    first = import_snapshot(tmp_path, config(), client=source_client())
    original = {p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()}
    second = import_snapshot(tmp_path, config(), client=source_client())
    assert first != second
    assert original == {
        p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()
    }
    assert load_snapshot(first)[1] == load_snapshot(second)[1]


@pytest.mark.parametrize("failed", ["laps", "sessions"])
def test_failed_or_partial_import_stays_auditable_not_complete(tmp_path, failed):
    snapshot = import_snapshot(tmp_path, config(), client=source_client(failed=failed))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == ("failed" if failed == "sessions" else "partial")
    failures = [r for r in manifest["requests"] if r["status"] == "failed"]
    assert failures
    assert all(
        (snapshot / r["raw_path"]).read_bytes() == b'{"error":"fixture unavailable"}'
        for r in failures
    )
    assert tables[failed] == []


def test_partial_discovery_retains_evidence_and_imports_only_resolved_years(tmp_path):
    snapshot = import_snapshot(tmp_path, config(), client=source_client(bad_discovery=2024))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "partial"
    assert [s["year"] for s in manifest["sessions"]] == [2023, 2025]
    assert len(tables["laps"]) == 2
    assert any("2024" in failure for failure in manifest["errors"])


def test_ambiguous_discovery_never_selects_an_arbitrary_row(tmp_path):
    snapshot = import_snapshot(tmp_path, config(), client=source_client(duplicate=True))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "failed"
    assert manifest["sessions"] == []
    assert len(tables["sessions"]) == 6


@pytest.mark.parametrize(
    "mutation",
    [
        "body",
        "hash",
        "row_count",
        "escape",
        "symlink",
        "missing_request",
        "fake_complete",
        "schema",
    ],
)
def test_corrupt_or_forged_cache_fails_closed(tmp_path, mutation):
    snapshot = import_snapshot(tmp_path, config(), client=source_client())
    manifest = json.loads((snapshot / "manifest.json").read_text())
    request = manifest["requests"][0]
    if mutation == "body":
        (snapshot / request["raw_path"]).write_bytes(b"[]")
    elif mutation == "hash":
        request["sha256"] = "0" * 64
    elif mutation == "row_count":
        request["row_count"] = 99
    elif mutation == "escape":
        request["raw_path"] = "../outside.json"
    elif mutation == "symlink":
        raw = snapshot / request["raw_path"]
        outside = tmp_path / "outside.json"
        outside.write_bytes(raw.read_bytes())
        raw.unlink()
        raw.symlink_to(outside)
    elif mutation == "missing_request":
        manifest["requests"].pop()
    elif mutation == "fake_complete":
        manifest["sessions"].pop()
    else:
        manifest["schema_version"] = 999
    save_manifest(snapshot, manifest)
    with pytest.raises(CacheError):
        load_snapshot(snapshot)


def test_valid_hash_but_malformed_json_is_rejected(tmp_path):
    snapshot = import_snapshot(tmp_path, config(), client=source_client())
    manifest = json.loads((snapshot / "manifest.json").read_text())
    request = manifest["requests"][0]
    body = b'[{"session_key":NaN}]'
    (snapshot / request["raw_path"]).write_bytes(body)
    request["sha256"] = hashlib.sha256(body).hexdigest()
    request["byte_count"] = len(body)
    save_manifest(snapshot, manifest)
    with pytest.raises(CacheError):
        load_snapshot(snapshot)


def test_nonnull_scope_mismatch_fails_but_null_remains_unknown(tmp_path):
    def wrong_scope(endpoint, rows):
        return [{**row, "session_key": 999} for row in rows] if endpoint == "laps" else rows

    snapshot = import_snapshot(tmp_path, config(), client=source_client(mutate=wrong_scope))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "partial"
    assert tables["laps"] == []
    assert any("mismatches requested" in error for error in manifest["errors"])

    def null_scope(endpoint, rows):
        return [{**row, "session_key": None} for row in rows] if endpoint == "laps" else rows

    snapshot = import_snapshot(tmp_path, config(), client=source_client(mutate=null_scope))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "complete"
    assert all(row["session_key"] is None for row in tables["laps"])


def test_inconsistent_circuit_cannot_select_a_winner_arbitrarily(tmp_path):
    def changed_circuit(endpoint, rows):
        if endpoint == "sessions":
            return [{**row, "circuit_key": row["year"]} for row in rows]
        return rows

    snapshot = import_snapshot(tmp_path, config(), client=source_client(mutate=changed_circuit))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "failed"
    assert manifest["sessions"] == []
    assert len(tables["sessions"]) == 3


def test_reserved_fields_cannot_overwrite_provenance(tmp_path):
    def collision(endpoint, rows):
        return [{**row, "source_row": 77} for row in rows] if endpoint == "laps" else rows

    snapshot = import_snapshot(tmp_path, config(), client=source_client(mutate=collision))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "partial"
    assert tables["laps"] == []
    assert any("provenance field collision" in error for error in manifest["errors"])


def test_duplicate_rows_and_unknown_fields_are_preserved(tmp_path):
    def duplicates(endpoint, rows):
        if endpoint == "laps":
            row = {**rows[0], "unknown_future_column": {"unit": None}}
            return [row, row]
        return rows

    snapshot = import_snapshot(tmp_path, config(), client=source_client(mutate=duplicates))
    manifest, tables = load_snapshot(snapshot)
    assert manifest["status"] == "complete"
    assert len(tables["laps"]) == 6
    assert [row["source_row"] for row in tables["laps"]] == [0, 1, 0, 1, 0, 1]
    assert tables["laps"][0]["unknown_future_column"] == {"unit": None}


def test_failure_attempt_body_hash_is_verified_even_when_retry_succeeds(tmp_path):
    client = source_client()
    original = client.transport
    calls = [0]

    def fail_once(url, timeout, max_bytes):
        calls[0] += 1
        if calls[0] == 1:
            return HTTPResponse(503, {}, b"busy")
        return original(url, timeout, max_bytes)

    client.transport = fail_once
    snapshot = import_snapshot(tmp_path, config(), client=client)
    manifest, _ = load_snapshot(snapshot)
    assert manifest["status"] == "complete"
    attempt = manifest["requests"][0]["attempts"][0]
    (snapshot / attempt["raw_path"]).write_bytes(b"evil")
    with pytest.raises(CacheError, match="SHA-256"):
        load_snapshot(snapshot)


def test_boolean_schema_version_cannot_masquerade_as_integer_one(tmp_path):
    snapshot = import_snapshot(tmp_path, config(), client=source_client())
    manifest = json.loads((snapshot / "manifest.json").read_text())
    manifest["schema_version"] = True
    save_manifest(snapshot, manifest)
    with pytest.raises(CacheError, match="schema"):
        load_snapshot(snapshot)
