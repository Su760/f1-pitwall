"""Offline cohort partition, evidence alignment and exact identifiability checks."""

import json
from copy import deepcopy
from datetime import timedelta

import pytest

from historical.tests.test_quality import CONFIG, MANIFEST, START, fixture, report, row
from pitwall_historical.cohort import (
    audit_cohort,
    audit_snapshot,
    exact_rank,
    identifiability,
    main,
    partition_rows,
)

SELECTION = {"session_key": 10, "excluded_driver_numbers": [], "quality_version": "f1-audit-v2"}


def verified_session_manifest():
    manifest = {**MANIFEST, "status": "partial", "requests": []}
    for table in fixture():
        params = (
            {"year": 2024}
            if table == "sessions"
            else {"meeting_key": 20}
            if table == "meetings"
            else {"session_key": 10}
        )
        manifest["requests"].append(
            {"id": table, "endpoint": table, "params": params, "status": "success"}
        )
    manifest["requests"].append(
        {
            "id": "other-pit",
            "endpoint": "pit",
            "params": {"session_key": 99},
            "status": "failed",
            "error": "HTTP 404",
        }
    )
    return manifest


def test_partition_keeps_source_identity_and_overlapping_reasons():
    quality = report()
    before = deepcopy(quality)
    membership, excluded = partition_rows(quality, SELECTION)
    assert quality == before
    assert [r["lap_number"] for r in membership] == [2, 3, 4]
    assert [r["source_row"] for r in excluded] == [0]
    membership, excluded = partition_rows(quality, {**SELECTION, "excluded_driver_numbers": [1]})
    assert membership == []
    assert len(excluded) == 4
    assert excluded[0]["cohort_exclusion_reasons"] == ["excluded_driver:1", "opening_lap"]
    assert all(r["source_request"] == "laps-fixture" for r in excluded)
    with pytest.raises(ValueError, match="quality version"):
        partition_rows({**quality, "quality_version": "f1-audit-v1"}, SELECTION)


def test_included_weather_and_stint_evidence_checked_without_reselection():
    tables = fixture()
    quality = report(tables)
    audit = audit_cohort(tables, quality, MANIFEST, CONFIG, SELECTION)
    assert audit["reconciliation"]["source_rows"] == 4
    assert audit["reconciliation"]["included_rows"] == 3
    assert audit["interval_checks"]["failed_rows"] == 0
    # Tampered audit reference cannot silently select a future sample.
    quality["lap_audit"][1]["weather_source"] = quality["lap_audit"][2]["weather_source"]
    audit = audit_cohort(tables, quality, MANIFEST, CONFIG, SELECTION)
    assert audit["reconciliation"]["included_rows"] == 3
    assert audit["interval_checks"]["failed_rows"] == 1
    assert "weather_reference_not_latest_prior" in audit["interval_checks"]["rows"][0]["failures"]
    assert audit["suitability"]["descriptive_late_race"]["status"] == "blocked"


def test_session_suitability_keeps_full_gate_blocked_and_unneeded_fields_separate():
    tables = fixture()
    manifest = verified_session_manifest()
    audit = audit_cohort(tables, report(tables, manifest), manifest, CONFIG, SELECTION)
    assert len(audit["session_requests"]) == 9
    assert audit["session_download"]["status"] == "complete"
    assert audit["full_circuit_gate"]["status"] == "blocked"
    assert audit["source_snapshot_status"] == "partial"
    # No stationary measurements or publication times are required for recorded laps.
    assert audit["suitability"]["descriptive_late_race"]["status"] == "suitable_with_limits"
    assert audit["suitability"]["within_event_prediction"]["status"] == "conditional_proposal_only"
    manifest["requests"] = [r for r in manifest["requests"] if r["id"] != "pit"]
    audit = audit_cohort(tables, report(tables, manifest), manifest, CONFIG, SELECTION)
    assert audit["reconciliation"]["included_rows"] == 3
    assert (
        "selected_session_endpoints_not_complete"
        in audit["suitability"]["descriptive_late_race"]["blockers"]
    )


def test_unobserved_stint_and_future_weather_are_not_hidden_by_lap_membership():
    tables = fixture()
    manifest = verified_session_manifest()
    tables["stints"][0]["lap_end"] = 5
    quality = report(tables, manifest)
    audit = audit_cohort(tables, quality, manifest, CONFIG, SELECTION)
    assert audit["reconciliation"]["included_rows"] == 3
    assert (
        "included_driver_stint_consistency_unresolved"
        in audit["suitability"]["descriptive_late_race"]["blockers"]
    )
    # Independently audit a stale quality artifact against changed evidence.
    tables["weather"] = [row("weather", date=START + timedelta(seconds=1000), rainfall=0)]
    audit = audit_cohort(tables, quality, manifest, CONFIG, SELECTION)
    assert audit["interval_checks"]["failed_rows"] == 3


def test_control_at_lap_end_and_mid_lap_clear_do_not_share_boundary():
    tables = fixture()
    tables["race_control"].append(
        row(
            "race_control",
            index=1,
            date=START + timedelta(seconds=180),
            category="SafetyCar",
            message="SAFETY CAR DEPLOYED",
        )
    )
    quality = report(tables)
    membership, _ = partition_rows(quality, SELECTION)
    assert [r["lap_number"] for r in membership] == [2]
    audit = audit_cohort(tables, quality, MANIFEST, CONFIG, SELECTION)
    assert audit["interval_checks"]["failed_rows"] == 0
    tables["race_control"].append(
        row(
            "race_control",
            index=2,
            date=START + timedelta(seconds=200),
            category="Flag",
            flag="CLEAR",
            scope="Track",
            message="TRACK CLEAR",
        )
    )
    membership, _ = partition_rows(report(tables), SELECTION)
    assert [r["lap_number"] for r in membership] == [2, 4]


def test_deletion_annotation_is_retrospective_and_does_not_exclude_member():
    tables = fixture()
    tables["race_control"].extend(
        [
            row(
                "race_control",
                index=1,
                date=START + timedelta(seconds=500),
                category="Other",
                lap_number=99,
                message="CAR 1 (FIX) TIME 1:30.000 DELETED - TRACK LIMITS AT TURN 4 LAP 2 12:01:30",
            ),
            row(
                "race_control",
                index=2,
                date=START + timedelta(seconds=501),
                category="Other",
                message="CAR 1 (FIX) TIME 1:30.000 DELETED - TRACK LIMITS (NEXT LAP)",
            ),
        ]
    )
    audit = audit_cohort(tables, report(tables), MANIFEST, CONFIG, SELECTION)
    assert audit["reconciliation"]["included_rows"] == 3
    assert audit["deletions"]["included_rows_with_explicit_deletion"] == 1
    assert audit["deletions"]["ambiguous_messages"] == 1
    assert audit["deletions"]["messages"][0]["matched_source_rows"][0]["source_row"] == 1


def test_exact_rank_and_nested_offset_confounding_do_not_use_pace_outcomes():
    assert exact_rank([[1, 1, 2], [1, 2, 3], [1, 3, 4]]) == 2
    assert exact_rank([]) == 0
    rows = []
    for driver, compound, offset in [(1, "HARD", -2), (2, "SOFT", -1)]:
        for lap in (3, 4, 5):
            rows.append(
                {
                    "driver_number": driver,
                    "stint_source": {"source_request": "stints", "source_row": driver},
                    "compound": compound,
                    "lap_number": lap,
                    "tyre_age_before_lap": lap + offset,
                }
            )
    result = identifiability(rows)
    assert result["age_minus_lap_constant_within_stint"] is True
    assert result["one_stint_per_driver"] is True
    assert result["compound_constant_within_stint"] is True
    full = result["designs"]["stint_offsets_lap_age_compound"]
    assert (full["columns"], full["rank"], full["nullity"]) == (5, 3, 2)
    assert result["designs"]["driver_and_stint_offsets"]["rank"] == 2
    rows[0]["tyre_age_before_lap"] += 1
    assert identifiability(rows)["age_minus_lap_constant_within_stint"] is False


def test_offline_artifacts_reproduce_provenance_and_refuse_overwrite(cached_source, tmp_path):
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({**SELECTION, "session_key": 123}))
    first, second = tmp_path / "a", tmp_path / "b"
    before = {
        p.relative_to(cached_source): p.read_bytes()
        for p in cached_source.rglob("*")
        if p.is_file()
    }
    audit_snapshot(cached_source, first, selection)
    audit_snapshot(cached_source, second, selection)
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    after = {
        p.relative_to(cached_source): p.read_bytes()
        for p in cached_source.rglob("*")
        if p.is_file()
    }
    assert before == after
    audit = json.loads((first / "audit.json").read_text())
    assert audit["reconciliation"]["included_rows"] == 0
    assert audit["suitability"]["descriptive_late_race"]["status"] == "blocked"
    assert audit["provenance"]["quality_version"] == "f1-audit-v2"
    with pytest.raises(FileExistsError):
        audit_snapshot(cached_source, first, selection)
    assert main([str(cached_source), "--output", str(first), "--selection", str(selection)]) == 1
    raw_manifest = json.loads((cached_source / "manifest.json").read_text())
    (cached_source / raw_manifest["requests"][0]["raw_path"]).write_bytes(b"[]")
    with pytest.raises(ValueError):
        audit_snapshot(cached_source, tmp_path / "corrupt", selection)
    assert not (tmp_path / "corrupt").exists()
