"""Small synthetic source-shaped audit cases; no network or race observations."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from pitwall_historical.quality import build_report, render_markdown
from pitwall_historical.schema import SCHEMAS

START = datetime(2024, 1, 1, 12, tzinfo=UTC)
CONFIG = {
    "max_lap_number": 1000,
    "weather_max_age_seconds": 120,
    "timing_tolerance_seconds": 2,
    "sector_tolerance_seconds": 0.05,
    "min_lap_duration_seconds": 30,
    "max_lap_duration_seconds": 300,
}
MANIFEST = {"status": "complete", "snapshot_id": "fixture", "source_url": "test.invalid"}


def row(table, index=0, **values):
    source = {"session_key": 10, "meeting_key": 20, **values}
    normalized = {name: source.get(name) for name in SCHEMAS[table]}
    normalized.update(
        source_request=f"{table}-fixture",
        source_row=index,
        raw_json=json.dumps(source, sort_keys=True, default=lambda v: v.isoformat()),
        validation_errors=[],
    )
    return normalized


def fixture():
    tables = {table: [] for table in SCHEMAS}
    tables["sessions"] = [
        row(
            "sessions",
            circuit_key=30,
            country_name="Bahrain",
            year=2024,
            session_name="Race",
            session_type="Race",
            date_start=START,
            date_end=START + timedelta(minutes=10),
        )
    ]
    tables["meetings"] = [
        row(
            "meetings",
            circuit_key=30,
            year=2024,
            meeting_name="Synthetic audit",
            date_start=START,
        )
    ]
    tables["drivers"] = [row("drivers", driver_number=1, full_name="Fixture Driver")]
    tables["laps"] = [
        row(
            "laps",
            index=lap - 1,
            driver_number=1,
            lap_number=lap,
            date_start=START + timedelta(seconds=(lap - 1) * 90),
            lap_duration=90.0,
            duration_sector_1=30.0,
            duration_sector_2=30.0,
            duration_sector_3=30.0,
            is_pit_out_lap=False,
        )
        for lap in range(1, 5)
    ]
    tables["stints"] = [
        row(
            "stints",
            driver_number=1,
            stint_number=1,
            lap_start=1,
            lap_end=4,
            compound="SOFT",
            tyre_age_at_start=0,
        )
    ]
    tables["weather"] = [
        row(
            "weather",
            index=lap - 1,
            date=START + timedelta(seconds=(lap - 1) * 90),
            rainfall=0,
        )
        for lap in range(1, 5)
    ]
    tables["race_control"] = [
        row(
            "race_control",
            date=START,
            category="Flag",
            flag="GREEN",
            scope="Track",
            message="GREEN LIGHT - RACE START",
        )
    ]
    tables["session_result"] = [
        row(
            "session_result",
            driver_number=1,
            number_of_laps=4,
            dnf=False,
            dns=False,
            dsq=False,
        )
    ]
    return tables


def report(tables=None, manifest=None):
    return build_report(tables or fixture(), manifest or MANIFEST, CONFIG)


def driver(result, number=1):
    return next(
        item for item in result["sessions"][0]["drivers"] if item["driver_number"] == number
    )


def audit_lap(result, number):
    return next(item for item in result["lap_audit"] if item["lap_number"] == number)


def test_known_fixture_retains_rows_and_counts_distinct_exclusions():
    tables = fixture()
    before = deepcopy(tables)
    result = report(tables)
    assert tables == before
    assert result["table_audits"]["laps"]["rows"] == 4
    assert driver(result)["coverage"]["missing_completed_laps"] == []
    assert driver(result)["coverage"]["expected_completed_laps"] == 4
    assert result["lap_audit"][2]["tyre_age_before_lap"] == 2
    assert result["sessions"][0]["readiness"]["descriptive_lap_stint"]["status"] == "ready"
    assert (
        result["sessions"][0]["readiness"]["dry_pace_investigation"]["counts"]["eligible_rows"] == 3
    )
    assert result["sessions"][0]["lap_exclusions"]["distinct_excluded_rows"] == 1
    assert result["sessions"][0]["readiness"]["incremental_pit_loss"]["status"] == "blocked"
    assert result["sessions"][0]["readiness"]["decision_time_features"]["status"] == "blocked"
    assert json.loads(json.dumps(result)) == result
    assert "not necessarily publication timestamps" in render_markdown(result)


def test_null_age_and_missing_weather_are_unknown_not_zero_or_dry():
    tables = fixture()
    tables["stints"][0]["tyre_age_at_start"] = None
    tables["weather"] = []
    result = report(tables)
    assert result["table_audits"]["stints"]["missing_required"]["tyre_age_at_start"] == 1
    assert all(item["tyre_age_before_lap"] is None for item in result["lap_audit"])
    assert all(item["weather_classification"] == "unknown" for item in result["lap_audit"])
    assert result["sessions"][0]["readiness"]["dry_pace_investigation"]["status"] == "blocked"


def test_missing_stint_endpoint_blocks_gate_without_discarding_valid_laps():
    tables = fixture()
    tables["stints"][0]["lap_end"] = 5
    tables["pit"] = [
        row(
            "pit",
            driver_number=1,
            lap_number=2,
            date=START + timedelta(seconds=170),
            lane_duration=24.0,
            stop_duration=2.5,
        )
    ]
    tables["pit"][0].update(effective_lane_duration=24.0, lane_duration_source="lane_duration")
    before = deepcopy(tables)
    result = report(tables)
    assert tables == before
    assert driver(result)["coverage"]["coverage_complete"] is True
    assert result["stint_audit"][0]["flags"] == ["missing_boundary_lap"]
    readiness = result["sessions"][0]["readiness"]
    for purpose in ("descriptive_lap_stint", "dry_pace_investigation"):
        assert readiness[purpose]["status"] == "limited"
        assert "unresolved_stint_consistency" in readiness[purpose]["blockers"]
        assert readiness[purpose]["counts"]["unresolved_stint_rows"] == 1
        assert readiness[purpose]["stint_blocking_reasons"] == {"missing_boundary_lap": 1}
    assert readiness["descriptive_lap_stint"]["counts"]["eligible_rows"] == 4
    assert all(lap["descriptive_eligible"] for lap in result["lap_audit"])
    assert readiness["pit_lane_description"]["status"] == "ready"
    assert readiness["stationary_stop_description"]["status"] == "ready"
    assert result["circuit_gate"]["status"] == "blocked"
    assert result["quality_version"] == "f1-audit-v2"
    assert "unresolved_stint_consistency" in render_markdown(result)


def test_completed_retirement_stint_does_not_require_unfinished_tail_join():
    tables = fixture()
    tables["session_result"][0].update(number_of_laps=3, dnf=True)
    tables["stints"][0]["lap_end"] = 3
    tables["laps"][3]["lap_duration"] = None
    result = report(tables)
    assert result["stint_audit"][0]["flags"] == []
    assert driver(result)["coverage"]["retirement_started_lap_numbers"] == [4]
    assert driver(result)["coverage"]["coverage_complete"] is True
    readiness = result["sessions"][0]["readiness"]["descriptive_lap_stint"]
    assert readiness["counts"]["eligible_rows"] == 3
    assert readiness["counts"]["unresolved_stint_rows"] == 0
    assert "unresolved_stint_consistency" not in readiness["blockers"]
    assert len(result["lap_audit"]) == 4


def test_retirement_uses_driver_result_and_started_tail_separately():
    tables = fixture()
    tables["session_result"][0].update(number_of_laps=2, dnf=True)
    tables["laps"] = tables["laps"][:3]
    tables["laps"][2]["lap_duration"] = None
    result = report(tables)
    coverage = driver(result)["coverage"]
    assert coverage["expected_completed_laps"] == 2
    assert coverage["missing_completed_laps"] == []
    assert coverage["extra_lap_numbers"] == [3]
    assert coverage["retirement_started_lap_numbers"] == [3]
    assert coverage["participation_status"] == "dnf"
    assert coverage["coverage_complete"] is True


def test_missing_results_preserves_unknown_tail_and_child_only_driver():
    tables = fixture()
    tables["session_result"] = []
    tables["laps"].append(row("laps", index=4, driver_number=99, lap_number=2))
    result = report(tables)
    assert driver(result)["coverage"]["expected_completed_laps"] is None
    assert driver(result)["coverage"]["trailing_coverage"] == "unknown"
    assert driver(result, 99)["driver_join"] == "unmatched"
    assert result["table_audits"]["laps"]["unmatched_joins"]["driver"] == 1
    assert result["circuit_gate"]["status"] != "passed"


def test_dns_expectation_is_zero_but_contradictory_laps_are_flagged():
    tables = fixture()
    tables["session_result"][0].update(number_of_laps=0, dns=True)
    result = report(tables)
    assert driver(result)["coverage"]["expected_completed_laps"] == 0
    assert driver(result)["coverage"]["coverage_complete"] is False
    assert "dns_with_lap_records" in driver(result)["coverage"]["flags"]


def test_exact_duplicates_and_conflicts_remain_distinct_and_excluded():
    tables = fixture()
    duplicate = deepcopy(tables["laps"][1])
    duplicate["source_row"] = 4
    conflict = deepcopy(tables["laps"][2])
    conflict.update(source_row=5, lap_duration=95.0, raw_json='{"conflict":true}')
    tables["laps"].extend([duplicate, conflict])
    result = report(tables)
    counts = result["table_audits"]["laps"]
    assert counts["rows"] == 6
    assert counts["exact_duplicate_extra_rows"] == 1
    assert counts["conflicting_key_groups"] == 1
    assert counts["conflicting_rows"] == 2
    assert len(result["lap_audit"]) == 6
    assert result["sessions"][0]["lap_exclusions"]["reasons"]["duplicate_record"] == 2
    assert result["sessions"][0]["lap_exclusions"]["reasons"]["conflicting_record"] == 2
    assert driver(result)["coverage"]["coverage_complete"] is False


def test_stint_overlap_never_picks_arbitrary_age_and_missing_bounds_flagged():
    tables = fixture()
    tables["stints"][0].update(lap_end=3)
    tables["stints"].append(
        row(
            "stints",
            index=1,
            driver_number=1,
            stint_number=2,
            lap_start=3,
            lap_end=5,
            compound="HARD",
            tyre_age_at_start=1,
        )
    )
    result = report(tables)
    lap = audit_lap(result, 3)
    assert lap["stint_join"] == "ambiguous"
    assert lap["tyre_age_before_lap"] is None
    assert "stint_overlap" in result["stint_audit"][0]["flags"]
    assert "missing_boundary_lap" in result["stint_audit"][1]["flags"]
    assert "stint_start_without_pit_evidence" in result["stint_audit"][1]["flags"]


def test_join_checks_include_session_and_meeting_not_only_driver():
    tables = fixture()
    tables["laps"][1]["meeting_key"] = 999
    tables["stints"][0]["session_key"] = 999
    result = report(tables)
    assert result["table_audits"]["laps"]["unmatched_joins"]["meeting"] == 1
    assert result["table_audits"]["stints"]["unmatched_joins"]["session"] == 1
    assert audit_lap(result, 2)["stint_join"] == "unmatched"
    assert "unmatched_meeting" in audit_lap(result, 2)["exclusion_reasons"]


def test_pit_alias_conflict_blocks_lane_only_missing_stop_is_not_zero():
    tables = fixture()
    pit = row(
        "pit",
        driver_number=1,
        lap_number=2,
        date=START + timedelta(seconds=170),
        lane_duration=24.0,
        pit_duration=26.0,
        stop_duration=None,
    )
    pit.update(
        effective_lane_duration=24.0,
        lane_duration_source="lane_duration",
        validation_errors=["pit_duration_alias_conflict"],
    )
    tables["pit"] = [pit]
    result = report(tables)
    assert result["pit_audit"][0]["stationary_duration_seconds"] is None
    assert "pit_duration_alias_conflict" in result["pit_audit"][0]["flags"]
    assert result["sessions"][0]["readiness"]["pit_lane_description"]["status"] == "blocked"
    assert result["sessions"][0]["readiness"]["stationary_stop_description"]["status"] == "blocked"
    assert (
        result["sessions"][0]["readiness"]["descriptive_lap_stint"]["counts"]["eligible_rows"] == 4
    )
    assert "pit_associated_lap" in audit_lap(result, 2)["flags"]
    assert "pit_associated_lap" in audit_lap(result, 3)["flags"]


def test_weather_never_backfills_from_future_or_skips_conflicting_latest_sample():
    tables = fixture()
    tables["weather"] = [row("weather", date=START + timedelta(seconds=91), rainfall=0)]
    result = report(tables)
    assert audit_lap(result, 2)["weather_classification"] == "unknown"
    assert audit_lap(result, 3)["weather_classification"] == "dry_candidate"
    assert audit_lap(result, 4)["weather_classification"] == "unknown"
    conflict = row("weather", index=1, date=START + timedelta(seconds=91), rainfall=1)
    tables["weather"].append(conflict)
    assert audit_lap(report(tables), 3)["weather_classification"] == "unknown"


def test_wet_compound_is_evidence_even_without_rain_sample():
    tables = fixture()
    tables["stints"][0]["compound"] = "INTERMEDIATE"
    tables["weather"] = []
    result = report(tables)
    assert all(lap["weather_classification"] == "wet_evidence" for lap in result["lap_audit"])


def test_local_green_does_not_clear_safety_car_and_in_lap_is_not_end():
    tables = fixture()
    tables["race_control"].extend(
        [
            row(
                "race_control",
                index=1,
                date=START + timedelta(seconds=100),
                category="SafetyCar",
                message="SAFETY CAR DEPLOYED",
            ),
            row(
                "race_control",
                index=2,
                date=START + timedelta(seconds=150),
                category="Flag",
                flag="GREEN",
                scope="Sector",
                sector=2,
                message="GREEN",
            ),
            row(
                "race_control",
                index=3,
                date=START + timedelta(seconds=170),
                category="SafetyCar",
                message="SAFETY CAR IN THIS LAP",
            ),
            row(
                "race_control",
                index=4,
                date=START + timedelta(seconds=280),
                category="Flag",
                flag="GREEN",
                scope="Track",
                message="GREEN",
            ),
        ]
    )
    result = report(tables)
    assert audit_lap(result, 2)["neutralization"] == "affected"
    assert audit_lap(result, 3)["neutralization"] == "affected"
    assert audit_lap(result, 4)["neutralization"] == "affected"


def test_control_without_global_clear_is_unknown_and_driver_lap_not_used():
    tables = fixture()
    tables["race_control"] = [
        row(
            "race_control",
            date=START + timedelta(seconds=800),
            category="Flag",
            flag="YELLOW",
            scope="Track",
            message="YELLOW",
            lap_number=2,
        )
    ]
    result = report(tables)
    assert audit_lap(result, 2)["neutralization"] == "unknown"
    assert "neutralization_affected" not in audit_lap(result, 2)["flags"]


def test_timing_sector_disagreement_overlap_and_partial_manifest_block_gate():
    tables = fixture()
    tables["laps"][1]["duration_sector_1"] = 40.0
    tables["laps"][2]["date_start"] = START + timedelta(seconds=170)
    result = report(tables, {**MANIFEST, "status": "partial"})
    assert "sector_total_disagreement" in audit_lap(result, 2)["flags"]
    assert "lap_timing_overlap" in audit_lap(result, 3)["flags"]
    assert result["circuit_gate"]["status"] == "blocked"
    assert all(
        purpose["status"] != "ready" for purpose in result["sessions"][0]["readiness"].values()
    )


@pytest.mark.parametrize("missing", ["sessions", "meetings", "drivers", "laps", "stints"])
def test_empty_required_table_cannot_pass_circuit_gate(missing):
    tables = fixture()
    tables[missing] = []
    result = report(tables)
    assert result["circuit_gate"]["status"] != "passed"


def test_global_clear_mid_lap_does_not_erase_unknown_early_interval():
    tables = fixture()
    tables["race_control"][0]["date"] = START + timedelta(seconds=45)
    result = report(tables)
    assert audit_lap(result, 1)["neutralization"] == "unknown"
    assert audit_lap(result, 2)["neutralization"] == "clear"


def test_rows_without_session_identity_cannot_disappear_from_gate():
    tables = fixture()
    orphan = row("laps", index=4, session_key=None, driver_number=1, lap_number=7)
    tables["laps"].append(orphan)
    result = report(tables)
    assert len(result["lap_audit"]) == 5
    assert result["circuit_gate"]["status"] == "blocked"
    assert "orphan_or_ambiguous_source_rows" in result["circuit_gate"]["blockers"]


def test_failed_empty_snapshot_exposes_precise_access_error():
    manifest = {
        **MANIFEST,
        "status": "failed",
        "errors": ["sessions: HTTP 403"],
        "requests": [
            {
                "id": "sessions",
                "endpoint": "sessions",
                "params": {"year": 2024},
                "status": "failed",
                "error": "HTTP 403",
            }
        ],
    }
    result = build_report({}, manifest, CONFIG)
    assert result["circuit_gate"]["status"] == "blocked"
    assert result["source_failures"][0]["error"] == "HTTP 403"
    assert "HTTP 403" in render_markdown(result)
    assert "PitWall" in render_markdown(result)


def test_pit_date_on_following_lap_is_uncertain_but_durations_stay_describable():
    tables = fixture()
    pit = row(
        "pit",
        driver_number=1,
        lap_number=2,
        date=START + timedelta(seconds=185),
        lane_duration=24.0,
        stop_duration=2.5,
    )
    pit.update(effective_lane_duration=24.0, lane_duration_source="lane_duration")
    tables["pit"] = [pit]
    result = report(tables)
    assert "pit_timestamp_outside_reported_lap" in result["pit_audit"][0]["flags"]
    assert result["pit_audit"][0]["lane_eligible"] is True
    assert result["pit_audit"][0]["stationary_eligible"] is True
    assert (
        result["sessions"][0]["readiness"]["pit_lane_description"]["counts"]["eligible_rows"] == 1
    )


def test_local_hazard_and_unmatched_clear_do_not_destroy_known_track_state():
    tables = fixture()
    tables["race_control"].extend(
        [
            row(
                "race_control",
                index=1,
                date=START + timedelta(seconds=100),
                category="Flag",
                flag="TRACK SURFACE SLIPPERY",
                scope="Sector",
                sector=4,
                message="TRACK SURFACE SLIPPERY IN TRACK SECTOR 4",
            ),
            row(
                "race_control",
                index=2,
                date=START + timedelta(seconds=130),
                category="Flag",
                flag="CLEAR",
                scope="Sector",
                sector=4,
                message="CLEAR",
            ),
            row(
                "race_control",
                index=3,
                date=START + timedelta(seconds=160),
                category="Flag",
                flag="CLEAR",
                scope="Sector",
                sector=6,
                message="CLEAR",
            ),
        ]
    )
    result = report(tables)
    assert audit_lap(result, 2)["neutralization"] == "affected"
    assert audit_lap(result, 3)["neutralization"] == "clear"


def test_pit_exit_green_does_not_certify_clear_track_or_end_safety_car():
    tables = fixture()
    tables["race_control"][0]["message"] = "GREEN LIGHT - PIT EXIT OPEN"
    result = report(tables)
    assert audit_lap(result, 2)["neutralization"] == "unknown"
    tables["race_control"] = [
        row("race_control", date=START, category="SafetyCar", message="SAFETY CAR DEPLOYED"),
        row(
            "race_control",
            index=1,
            date=START + timedelta(seconds=90),
            category="Flag",
            flag="GREEN",
            scope="Track",
            message="GREEN LIGHT - PIT EXIT OPEN",
        ),
    ]
    assert audit_lap(report(tables), 3)["neutralization"] == "affected"


def test_missing_control_instructions_make_laps_unknown_after_prior_green():
    tables = fixture()
    tables["race_control"].append(
        row(
            "race_control",
            index=1,
            date=START + timedelta(seconds=100),
            category="Flag",
            scope="Track",
            message=None,
            flag=None,
        )
    )
    result = report(tables)
    assert audit_lap(result, 2)["neutralization"] == "unknown"
    assert audit_lap(result, 2)["dry_pace_eligible"] is False


def test_unexplained_stint_boundary_excludes_both_neighboring_laps():
    tables = fixture()
    tables["stints"][0]["lap_end"] = 3
    tables["stints"].append(
        row(
            "stints",
            index=1,
            driver_number=1,
            stint_number=2,
            lap_start=4,
            lap_end=4,
            compound="HARD",
            tyre_age_at_start=0,
        )
    )
    result = report(tables)
    for lap in (3, 4):
        assert "stint_boundary_inconsistent" in audit_lap(result, lap)["exclusion_reasons"]
        assert audit_lap(result, lap)["dry_pace_eligible"] is False
    assert result["sessions"][0]["readiness"]["dry_pace_investigation"]["status"] != "ready"


@pytest.mark.parametrize(
    "table,field",
    [
        ("stints", "compound"),
        ("drivers", "full_name"),
        ("meetings", "meeting_name"),
    ],
)
def test_required_joined_metadata_missing_blocks_descriptive_gate(table, field):
    tables = fixture()
    tables[table][0][field] = None
    result = report(tables)
    assert result["sessions"][0]["readiness"]["descriptive_lap_stint"]["status"] != "ready"
    assert result["circuit_gate"]["status"] == "blocked"


def test_driver_scoped_hazard_affects_only_matching_driver():
    tables = fixture()
    tables["laps"].append(
        row(
            "laps",
            index=4,
            driver_number=99,
            lap_number=2,
            date_start=START + timedelta(seconds=90),
            lap_duration=90.0,
            is_pit_out_lap=False,
        )
    )
    tables["race_control"].append(
        row(
            "race_control",
            index=1,
            date=START + timedelta(seconds=100),
            category="Flag",
            flag="YELLOW",
            scope="Driver",
            driver_number=1,
            message="YELLOW",
        )
    )
    result = report(tables)
    laps = [lap for lap in result["lap_audit"] if lap["lap_number"] == 2]
    assert next(lap for lap in laps if lap["driver_number"] == 1)["neutralization"] == "affected"
    assert next(lap for lap in laps if lap["driver_number"] == 99)["neutralization"] == "clear"


def test_extreme_source_duration_and_lap_number_cannot_overflow_or_expand_ranges():
    tables = fixture()
    tables["laps"][1]["lap_duration"] = 1e308
    tables["laps"][3]["lap_number"] = 2**62
    tables["session_result"][0]["number_of_laps"] = 2**62
    pit = row("pit", driver_number=1, lap_number=2, date=START + timedelta(seconds=185))
    pit.update(effective_lane_duration=24.0, lane_duration_source="lane_duration")
    tables["pit"] = [pit]
    result = report(tables)
    assert "extreme_lap_duration" in audit_lap(result, 2)["flags"]
    assert audit_lap(result, 2)["neutralization"] == "unknown"
    coverage = driver(result)["coverage"]
    assert coverage["expected_completed_laps"] is None
    assert coverage["internal_missing_laps"] is None
    assert "unsupported_lap_number_range" in coverage["flags"]
    assert result["circuit_gate"]["status"] == "blocked"


def test_timestamp_arithmetic_near_datetime_max_is_unknown_not_crash():
    tables = fixture()
    tables["laps"][1]["date_start"] = datetime.max.replace(tzinfo=UTC)
    result = report(tables)
    assert audit_lap(result, 2)["neutralization"] == "unknown"


def test_session_download_status_includes_failed_meeting_and_missing_endpoints():
    tables = fixture()
    manifest = {
        **MANIFEST,
        "status": "partial",
        "requests": [
            {
                "id": "meeting",
                "endpoint": "meetings",
                "params": {"meeting_key": 20},
                "status": "failed",
                "error": "HTTP 503",
            },
            {"id": "laps", "endpoint": "laps", "params": {"session_key": 10}, "status": "success"},
        ],
    }
    result = report(tables, manifest)
    download = result["sessions"][0]["source_download"]
    assert download["status"] == "partial"
    assert download["failures"][0]["endpoint"] == "meetings"
    assert "drivers" in download["missing_request_endpoints"]


def test_retrospective_safety_car_infringement_is_not_a_control_transition():
    tables = fixture()
    tables["race_control"].append(
        row(
            "race_control",
            index=1,
            date=START + timedelta(seconds=100),
            category="Other",
            message="TURN 4 INCIDENT NOTED - SAFETY CAR INFRINGEMENT",
        )
    )
    result = report(tables)
    assert audit_lap(result, 2)["neutralization"] == "clear"
    assert audit_lap(result, 3)["neutralization"] == "clear"
