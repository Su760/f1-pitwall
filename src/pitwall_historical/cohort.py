"""Offline retrospective cohort evidence; no fitting or quality-gate mutation."""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from fractions import Fraction
from pathlib import Path

from . import QUALITY_VERSION
from .cache import load_snapshot
from .normalize import _validate_quality_config, canonical, digest, normalize_tables
from .quality import _control_event, build_report

COHORT_VERSION = "f1.2-cohort-v1"


def _ref(row):
    return {key: row[key] for key in ("source_request", "source_row")}


def _key(row):
    return row["source_request"], row["source_row"]


def _counts(values):
    return dict(sorted(Counter(values).items()))


def partition_rows(quality, selection):
    """Partition physical source rows; expected counts are never selector inputs."""
    if set(selection) != {"session_key", "excluded_driver_numbers", "quality_version"}:
        raise ValueError(
            "selection must contain only session, excluded drivers and quality version"
        )
    if (
        selection["quality_version"] != QUALITY_VERSION
        or quality["quality_version"] != QUALITY_VERSION
    ):
        raise ValueError("cohort quality version does not match the required implementation")
    session = selection["session_key"]
    excluded_drivers = selection["excluded_driver_numbers"]
    if type(session) is not int or session <= 0 or not isinstance(excluded_drivers, list):
        raise ValueError("invalid cohort session or excluded drivers")
    if any(type(n) is not int or n <= 0 for n in excluded_drivers):
        raise ValueError("excluded drivers must be positive integers")
    if len(set(excluded_drivers)) != len(excluded_drivers):
        raise ValueError("excluded drivers must be unique")
    if len([s for s in quality["sessions"] if s["session_key"] == session]) != 1:
        raise ValueError("cohort session must resolve uniquely")
    included, excluded, seen = [], [], set()
    for lap in quality["lap_audit"]:
        if lap["session_key"] != session:
            continue
        if _key(lap) in seen:
            raise ValueError("duplicate physical source row identity")
        seen.add(_key(lap))
        reasons = list(lap["exclusion_reasons"])
        if lap["dry_pace_eligible"] != (not reasons):
            raise ValueError("quality eligibility contradicts its exclusion reasons")
        if lap["driver_number"] in excluded_drivers:
            reasons.append(f"excluded_driver:{lap['driver_number']}")
        item = {**lap, "cohort_exclusion_reasons": sorted(set(reasons))}
        (excluded if reasons else included).append(item)
    return included, excluded


def exact_rank(rows):
    """Exact rational row elimination of integer designs, without outcome values."""
    basis = {}
    for values in rows:
        vector = [Fraction(value) for value in values]
        for pivot, base in sorted(basis.items()):
            factor = vector[pivot]
            if factor:
                vector = [x - factor * y for x, y in zip(vector, base, strict=True)]
        pivot = next((i for i, value in enumerate(vector) if value), None)
        if pivot is not None:
            scale = vector[pivot]
            basis[pivot] = [x / scale for x in vector]
    return len(basis)


def identifiability(rows):
    """Reference-coded additive design diagnostics; lap durations are never read."""
    if not rows:
        return {"status": "no_rows", "designs": {}}
    drivers = sorted({r["driver_number"] for r in rows})
    stints = sorted({_key(r["stint_source"]) for r in rows})
    compounds = sorted({r["compound"] for r in rows})
    groups = defaultdict(list)
    driver_stints = defaultdict(set)
    for r in rows:
        groups[_key(r["stint_source"])].append(r)
        driver_stints[r["driver_number"]].add(_key(r["stint_source"]))
    designs = {}
    specifications = {
        "lap_age_compound": (False, False, True, True, True),
        "driver_offsets_lap": (True, False, True, False, False),
        "stint_offsets_lap_age": (False, True, True, True, False),
        "stint_offsets_lap_age_compound": (False, True, True, True, True),
        "driver_offsets_lap_age_compound": (True, False, True, True, True),
        "driver_and_stint_offsets": (True, True, False, False, False),
    }
    for name, (driver, stint, lap, age, compound) in specifications.items():
        names = ["intercept"]
        if driver:
            names += [f"driver:{d}" for d in drivers[1:]]
        if stint:
            names += [f"stint:{s[0]}:{s[1]}" for s in stints[1:]]
        names += [n for n, use in (("race_lap", lap), ("tyre_age", age)) if use]
        if compound:
            names += [f"compound:{c}" for c in compounds[1:]]
        matrix = []
        for r in rows:
            values = [1]
            if driver:
                values += [int(r["driver_number"] == d) for d in drivers[1:]]
            if stint:
                values += [int(_key(r["stint_source"]) == s) for s in stints[1:]]
            if lap:
                values.append(r["lap_number"])
            if age:
                values.append(r["tyre_age_before_lap"])
            if compound:
                values += [int(r["compound"] == c) for c in compounds[1:]]
            matrix.append(values)
        rank = exact_rank(matrix)
        designs[name] = {
            "rows": len(rows),
            "columns": len(names),
            "rank": rank,
            "nullity": len(names) - rank,
            "column_names": names,
        }
    return {
        "method": "exact rational rank; reference-coded categories; no outcome used or model fit",
        "age_minus_lap_constant_within_stint": all(
            len({r["tyre_age_before_lap"] - r["lap_number"] for r in group}) == 1
            for group in groups.values()
        ),
        "compound_constant_within_stint": all(
            len({r["compound"] for r in group}) == 1 for group in groups.values()
        ),
        "one_stint_per_driver": all(len(v) == 1 for v in driver_stints.values()),
        "stint_offsets": [
            {
                "stint_source": {"source_request": key[0], "source_row": key[1]},
                "driver_number": group[0]["driver_number"],
                "age_minus_race_lap": sorted(
                    {r["tyre_age_before_lap"] - r["lap_number"] for r in group}
                ),
            }
            for key, group in sorted(groups.items())
        ],
        "designs": designs,
    }


def _coverage(rows, fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[f] for f in fields)].append(row)
    return [
        {
            **dict(zip(fields, key, strict=True)),
            "rows": len(group),
            "drivers": sorted({r["driver_number"] for r in group}),
            "race_laps": sorted({r["lap_number"] for r in group}),
            "tyre_ages": sorted({r["tyre_age_before_lap"] for r in group}),
            "compounds": sorted({r["compound"] for r in group}),
        }
        for key, group in sorted(groups.items())
    ]


def _interval_checks(tables, members, config, session):
    """Inspect each selected half-open lap interval and its referenced raw evidence."""
    by_ref = {name: {_key(r): r for r in rows} for name, rows in tables.items()}
    controls = [r for r in tables["race_control"] if r["session_key"] == session]
    weather = [
        r for r in tables["weather"] if r["session_key"] == session and r["date"] is not None
    ]
    checked = []
    for member in members:
        failures = []
        lap = by_ref["laps"][_key(member)]
        start = lap["date_start"]
        end = start + timedelta(seconds=lap["lap_duration"])
        stints = [by_ref["stints"][_key(ref)] for ref in member["stint_sources"]]
        stint = stints[0] if len(stints) == 1 else None
        if stint is None or not (
            stint["session_key"] == session
            and stint["driver_number"] == member["driver_number"]
            and stint["lap_start"] <= member["lap_number"] <= stint["lap_end"]
            and stint["tyre_age_at_start"] is not None
            and member["tyre_age_before_lap"]
            == stint["tyre_age_at_start"] + member["lap_number"] - stint["lap_start"]
            and member["compound"] == stint["compound"]
        ):
            failures.append("stint_join_or_age_inconsistent")
        prior = [r for r in weather if r["date"] <= start]
        latest = max((r["date"] for r in prior), default=None)
        latest_rows = [r for r in prior if r["date"] == latest]
        sample = latest_rows[0] if len(latest_rows) == 1 else None
        if sample is None or member["weather_source"] != _ref(sample):
            failures.append("weather_reference_not_latest_prior")
        weather_age = (start - latest).total_seconds() if latest else None
        if sample is None or not (
            sample["rainfall"] == 0
            and weather_age <= config["weather_max_age_seconds"]
            and member["weather_sample_age_seconds"] == weather_age
        ):
            failures.append("weather_value_or_age_unresolved")
        applicable = [
            r
            for r in controls
            if not (
                r.get("scope") == "Driver"
                and r.get("driver_number") not in (None, member["driver_number"])
            )
        ]
        clears = [
            r
            for r in applicable
            if r["date"] is not None
            and r["date"] <= start
            and _control_event(r) == ("clear", "global")
        ]
        clear = max(clears, key=lambda r: r["date"], default=None)
        # Independent conservative check after the last explicit global clear.
        # Any state-changing/ambiguous command inside this window requires review;
        # a later clear cannot erase an overlap within a selected interval.
        hazards = [
            r
            for r in applicable
            if r["date"] is None
            or (
                r["date"] < end
                and (clear is None or r["date"] >= clear["date"])
                and _control_event(r)[0] not in {"ignore", "clear"}
            )
        ]
        if clear is None or hazards:
            failures.append("control_boundary_requires_review")
        checked.append(
            {
                **_ref(member),
                "driver_number": member["driver_number"],
                "lap_number": member["lap_number"],
                "date_start": start,
                "date_end_exclusive": end,
                "stint_source": _ref(stint) if stint else None,
                "weather_source": _ref(sample) if sample else None,
                "weather_sample_age_seconds": weather_age,
                "last_global_clear_source": _ref(clear) if clear else None,
                "seconds_after_global_clear": (start - clear["date"]).total_seconds()
                if clear
                else None,
                "control_review_sources": [_ref(r) for r in hazards],
                "failures": failures,
            }
        )
    return {
        "checked_rows": len(checked),
        "failed_rows": sum(bool(r["failures"]) for r in checked),
        "rows": checked,
    }


def _deletions(tables, session, members):
    laps = [r for r in tables["laps"] if r["session_key"] == session]
    member_keys = {_key(r) for r in members}
    messages, tagged = [], set()
    for event in tables["race_control"]:
        message = event.get("message") or ""
        if event["session_key"] != session or "DELETED" not in message:
            continue
        car = re.search(r"\bCAR (\d+)\b", message)
        numbers = re.findall(r"\bLAP (\d+)\b", message)
        explicit = car is not None and len(numbers) == 1 and "NEXT LAP" not in message
        matches = [
            r
            for r in laps
            if explicit and r["driver_number"] == int(car[1]) and r["lap_number"] == int(numbers[0])
        ]
        selected = [r for r in matches if _key(r) in member_keys]
        tagged.update(_key(r) for r in selected)
        messages.append(
            {
                **_ref(event),
                "date": event["date"],
                "message": message,
                "mapping": "explicit_car_and_lap" if explicit else "ambiguous",
                "matched_source_rows": [_ref(r) for r in matches],
                "included_source_rows": [_ref(r) for r in selected],
            }
        )
    return {
        "included_rows_with_explicit_deletion": len(tagged),
        "ambiguous_messages": sum(m["mapping"] == "ambiguous" for m in messages),
        "unmatched_explicit_messages": sum(
            m["mapping"] != "ambiguous" and not m["matched_source_rows"] for m in messages
        ),
        "messages": messages,
        "interpretation": (
            "Retrospective annotation only; no membership change or decision-time feature."
        ),
    }


def audit_cohort(tables, quality, manifest, config, selection):
    members, excluded = partition_rows(quality, selection)
    session = next(s for s in quality["sessions"] if s["session_key"] == selection["session_key"])
    metadata = session["identity"]
    requests = [
        r
        for r in manifest.get("requests", [])
        if r["params"].get("session_key") == selection["session_key"]
        or (
            r["endpoint"] == "meetings"
            and r["params"].get("meeting_key") == metadata["meeting_key"]
        )
        or (r["endpoint"] == "sessions" and r["params"].get("year") == metadata["year"])
    ]
    raw_laps = [r for r in tables["laps"] if r["session_key"] == selection["session_key"]]
    if Counter(_key(r) for r in raw_laps) != Counter(_key(r) for r in members + excluded):
        raise ValueError("cohort partition does not reconcile all session source laps")
    drivers = {r["driver_number"] for r in members}
    coverage = [r for r in session["drivers"] if r["driver_number"] in drivers]
    stint_audit = [
        r
        for r in quality["stint_audit"]
        if r["session_key"] == selection["session_key"] and r["driver_number"] in drivers
    ]
    unresolved = [
        r
        for r in stint_audit
        if set(r["flags"]) - {"pit_boundary_semantics_uncertain", "tyre_age_unavailable"}
    ]
    checked = _interval_checks(tables, members, config, selection["session_key"])
    by_stint = {_key(r): r for r in tables["stints"]}
    enriched = []
    for r in members:
        if len(r["stint_sources"]) != 1:
            raise ValueError("selected row has no unique stint identity")
        stint = by_stint[_key(r["stint_sources"][0])]
        enriched.append({**r, "stint_source": _ref(stint), "stint_number": stint["stint_number"]})
    blockers = []
    if not members:
        blockers.append("no_selected_rows")
    if session["source_download"]["status"] != "complete":
        blockers.append("selected_session_endpoints_not_complete")
    if any(not d["coverage"]["coverage_complete"] for d in coverage):
        blockers.append("included_driver_coverage_unresolved")
    if unresolved:
        blockers.append("included_driver_stint_consistency_unresolved")
    if checked["failed_rows"]:
        blockers.append("included_interval_evidence_unresolved")
    metadata_counts = [session["tables"][name] for name in ("sessions", "meetings")]
    metadata_counts += [d["tables"]["drivers"] for d in coverage]
    if any(
        c["rows_with_missing_required"]
        or c["validation_errors"]
        or c["duplicate_rows"]
        or c["conflicting_rows"]
        or any(c["unmatched_joins"].values())
        for c in metadata_counts
    ):
        blockers.append("metadata_unresolved")
    by_ref_weather = {_key(r): r for r in tables["weather"]}
    weather_keys = sorted(
        {_key(r["weather_source"]) for r in checked["rows"] if r["weather_source"]}
    )
    base_excluded = sum(not r["dry_pace_eligible"] for r in excluded)
    return {
        "cohort_version": COHORT_VERSION,
        "selection": selection,
        "full_circuit_gate": quality["circuit_gate"],
        "session_identity": metadata,
        "session_download": session["source_download"],
        "session_requests": requests,
        "source_snapshot_status": manifest["status"],
        "source_failures": quality["source_failures"],
        "reconciliation": {
            "source_rows": len(raw_laps),
            "included_rows": len(members),
            "distinct_excluded_rows": len(excluded),
            "v2_excluded_rows": base_excluded,
            "additional_excluded_driver_rows": len(excluded) - base_excluded,
            "overlapping_reason_counts": _counts(
                reason for r in excluded for reason in r["cohort_exclusion_reasons"]
            ),
        },
        "included_driver_coverage": coverage,
        "included_driver_stint_audits": stint_audit,
        "interval_checks": checked,
        "control_events": [
            {**r, "interpreted_transition": _control_event(r)}
            for r in tables["race_control"]
            if r["session_key"] == selection["session_key"]
        ],
        "selected_weather_samples": [by_ref_weather[key] for key in weather_keys],
        "deletions": _deletions(tables, selection["session_key"], members),
        "coverage": {
            name: _coverage(enriched, fields)
            for name, fields in {
                "driver": ["driver_number"],
                "stint": ["driver_number", "stint_number", "compound"],
                "compound": ["compound"],
                "tyre_age": ["tyre_age_before_lap"],
                "race_lap": ["lap_number"],
                "compound_by_age": ["compound", "tyre_age_before_lap"],
                "compound_by_race_lap": ["compound", "lap_number"],
            }.items()
        },
        "identifiability": identifiability(enriched),
        "suitability": {
            "descriptive_late_race": {
                "status": "blocked" if blockers else "suitable_with_limits",
                "blockers": blockers,
                "target": (
                    "recorded selected elapsed lap intervals, including deletion-tagged laps; "
                    "not legal clean pace"
                ),
            },
            "within_event_prediction": {
                "status": "blocked" if blockers else "conditional_proposal_only",
                "blockers": blockers,
                "limits": [
                    "no experiment performed",
                    "freeze target and time-ordered validation before fitting",
                    "selection is retrospective",
                    "no random adjacent-lap split or held-out-event claim",
                    "parameter identifiability is distinct from conditional prediction",
                ],
            },
            "whole_race_calibration_and_strategy": {
                "status": "not_supported",
                "blockers": [
                    "selected late-stint single-event observations",
                    "no intervention or counterfactual pit-loss evidence",
                    "fuel_traffic_track_and_tire_effects_not_isolated",
                    "no_whole_race_or_held_out_event_validation",
                ],
            },
        },
    }


def audit_snapshot(snapshot: Path, output: Path, selection_path: Path):
    snapshot, output = Path(snapshot).resolve(), Path(output).resolve()
    if output == snapshot or snapshot in output.parents or output in snapshot.parents:
        raise ValueError("cohort output must be separate from the raw snapshot")
    if output.exists():
        raise FileExistsError(output)
    selection_bytes = Path(selection_path).read_bytes()
    selection = json.loads(selection_bytes)
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    manifest, raw = load_snapshot(snapshot)
    config = manifest["config"]
    _validate_quality_config(config)
    tables = normalize_tables(raw)
    quality = build_report(tables, manifest, config)
    quality["provenance"] = {
        "source_manifest_sha256": digest((snapshot / "manifest.json").read_bytes()),
        "source_snapshot_id": manifest["snapshot_id"],
        "config": config,
    }
    members, exclusions = partition_rows(quality, selection)
    audit = audit_cohort(tables, quality, manifest, config, selection)
    code = {p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))}
    provenance = {
        **quality["provenance"],
        "config_sha256": digest(canonical(config)),
        "selection_file_sha256": digest(selection_bytes),
        "selection_sha256": digest(canonical(selection)),
        "quality_version": QUALITY_VERSION,
        "cohort_version": COHORT_VERSION,
        "quality_report_sha256": digest(canonical(quality)),
        "implementation_sha256": code,
        "implementation_bundle_sha256": digest(canonical(code)),
        "python_version": platform.python_version(),
    }
    audit["provenance"] = provenance
    artifacts = {
        "membership.json": canonical({"provenance": provenance, "rows": members}),
        "exclusions.json": canonical({"provenance": provenance, "rows": exclusions}),
        "audit.json": canonical(audit),
    }
    output.mkdir(parents=True, exist_ok=False)
    build = {"status": "building", "provenance": provenance}
    build_path = output / "manifest.json"
    build_path.write_bytes(canonical(build))
    try:
        for name, body in artifacts.items():
            (output / name).write_bytes(body)
        build["artifacts"] = {name: digest(body) for name, body in artifacts.items()}
        build["status"] = "complete"
    except OSError:
        build["status"] = "failed"
        raise
    finally:
        build_path.write_bytes(canonical(build))
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline retrospective cohort audit; no fitting")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        audit = audit_snapshot(args.snapshot, args.output, args.selection)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"Cohort audit failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": str(args.output),
                "source_status": audit["source_snapshot_status"],
                "full_circuit_gate": audit["full_circuit_gate"]["status"],
                "included_rows": audit["reconciliation"]["included_rows"],
                "descriptive_suitability": audit["suitability"]["descriptive_late_race"]["status"],
            }
        )
    )
    return (
        0
        if audit["source_snapshot_status"] == "complete"
        and audit["suitability"]["descriptive_late_race"]["status"] != "blocked"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
