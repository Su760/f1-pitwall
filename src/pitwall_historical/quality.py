"""Deterministic, row-preserving retrospective suitability audit.

No value from this module is a policy observation. Event dates do not establish
publication/availability dates, and completed stint joins are retrospective.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from . import QUALITY_VERSION
from .schema import LOGICAL_KEYS, REQUIRED_FIELDS, SCHEMAS

_METADATA = {"source_request", "source_row", "raw_json", "validation_errors"}
_DRIVER_TABLES = {"drivers", "laps", "stints", "pit", "session_result"}
_SLICKS = {"SOFT", "MEDIUM", "HARD"}
_WETS = {"INTERMEDIATE", "WET"}


def _json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value


def _canonical(value):
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _ref(row):
    return {"source_request": row["source_request"], "source_row": row["source_row"]}


def _fingerprint(row):
    # raw_json preserves unknown source fields and distinguishes absent from null.
    return row.get("raw_json") or _canonical({k: v for k, v in row.items() if k not in _METADATA})


def _sort_key(value):
    return (value is None, str(value))


def _counts(values):
    return dict(sorted(Counter(values).items()))


class _Audit:
    def __init__(self, tables):
        self.tables = {name: tables.get(name, []) for name in SCHEMAS}
        self.flags = {name: [set() for _ in rows] for name, rows in self.tables.items()}
        self.groups = {}
        self.summaries = {}
        for table, rows in self.tables.items():
            groups = defaultdict(list)
            for index, row in enumerate(rows):
                key = tuple(row.get(field) for field in LOGICAL_KEYS[table])
                groups[key].append(index)
            self.groups[table] = groups
            for indices in groups.values():
                fingerprints = {_fingerprint(rows[index]) for index in indices}
                if len(fingerprints) > 1:
                    for index in indices:
                        self.flags[table][index].add("conflicting_record")
                elif len(indices) > 1:
                    for index in indices:
                        self.flags[table][index].add("duplicate_record")
        self._joins()
        for table, rows in self.tables.items():
            self.summaries[table] = self.summary(table, list(range(len(rows))))

    def canonical(self, table, key):
        indices = self.groups[table].get(key, [])
        if not indices or "conflicting_record" in self.flags[table][indices[0]]:
            return None
        return self.tables[table][indices[0]]

    def flags_for(self, table, row):
        # Source metadata identify each retained physical row within a request.
        for index, candidate in enumerate(self.tables[table]):
            if candidate is row:
                return self.flags[table][index]
        raise ValueError("row is not part of the audited table")

    def _joins(self):
        for table, rows in self.tables.items():
            for index, row in enumerate(rows):
                flags = self.flags[table][index]
                if table == "meetings":
                    continue
                if table == "sessions":
                    meeting = self.canonical("meetings", (row.get("meeting_key"),))
                    if meeting is None or meeting.get("circuit_key") != row.get("circuit_key"):
                        flags.add("unmatched_meeting")
                    continue
                session = self.canonical("sessions", (row.get("session_key"),))
                if session is None:
                    flags.add("unmatched_session")
                meeting = self.canonical("meetings", (row.get("meeting_key"),))
                if (
                    session is None
                    or meeting is None
                    or row.get("meeting_key") != session.get("meeting_key")
                    or meeting.get("circuit_key") != session.get("circuit_key")
                ):
                    flags.add("unmatched_meeting")
                if table in _DRIVER_TABLES - {"drivers"}:
                    driver = self.canonical(
                        "drivers", (row.get("session_key"), row.get("driver_number"))
                    )
                    if driver is None:
                        flags.add("unmatched_driver")

    def summary(self, table, indices):
        rows = self.tables[table]
        present = set(indices)
        selected_groups = [
            [index for index in group if index in present]
            for group in self.groups[table].values()
            if any(index in present for index in group)
        ]
        exact_extra = 0
        conflict_groups = 0
        for group in selected_groups:
            occurrences = Counter(_fingerprint(rows[index]) for index in group)
            exact_extra += sum(count - 1 for count in occurrences.values())
            conflict_groups += len(occurrences) > 1
        missing = {
            field: sum(rows[index].get(field) is None for index in indices)
            for field in REQUIRED_FIELDS[table]
        }
        return {
            "rows": len(indices),
            "missing_required": missing,
            "rows_with_missing_required": sum(
                any(rows[index].get(field) is None for field in REQUIRED_FIELDS[table])
                for index in indices
            ),
            "validation_errors": _counts(
                error for index in indices for error in rows[index].get("validation_errors", [])
            ),
            "exact_duplicate_extra_rows": exact_extra,
            "duplicate_rows": sum("duplicate_record" in self.flags[table][i] for i in indices),
            "conflicting_key_groups": conflict_groups,
            "conflicting_rows": sum("conflicting_record" in self.flags[table][i] for i in indices),
            "unmatched_joins": {
                target: sum(f"unmatched_{target}" in self.flags[table][i] for i in indices)
                for target in ("session", "meeting", "driver")
            },
        }

    def row_flags(self, table, index):
        row = self.tables[table][index]
        flags = set(self.flags[table][index])
        if row.get("validation_errors"):
            flags.add("invalid_source_fields")
        for field in REQUIRED_FIELDS[table]:
            if row.get(field) is None:
                flags.add(f"missing:{field}")
        return flags

    def joinable(self, table, row):
        flags = self.flags_for(table, row)
        return not any(
            flag.startswith("unmatched_") or flag == "conflicting_record" for flag in flags
        )


def _driver_coverage(audit, session, number, max_lap_number):
    laps = [
        row
        for row in audit.tables["laps"]
        if row.get("session_key") == session and row.get("driver_number") == number
    ]
    numbers = sorted({row["lap_number"] for row in laps if (row.get("lap_number") or 0) > 0})
    timed = {
        row["lap_number"]
        for row in laps
        if (row.get("lap_number") or 0) > 0 and (row.get("lap_duration") or 0) > 0
    }
    result = audit.canonical("session_result", (session, number))
    flags = []
    expected = None
    participation = "unknown"
    statuses_known = False
    if result is not None and audit.joinable("session_result", result):
        expected = result.get("number_of_laps")
        statuses_known = all(result.get(field) is not None for field in ("dnf", "dns", "dsq"))
        if result.get("dns"):
            participation = "dns"
            if expected not in (None, 0):
                flags.append("dns_with_completed_laps")
            expected = 0
            if numbers:
                flags.append("dns_with_lap_records")
        elif result.get("dsq"):
            participation = "dsq"
        elif result.get("dnf"):
            participation = "dnf"
        elif statuses_known:
            participation = "finished"
    if expected is not None and expected < 0:
        flags.append("invalid_completed_lap_count")
        expected = None
    if any(number > max_lap_number for number in numbers) or (
        expected is not None and expected > max_lap_number
    ):
        flags.append("unsupported_lap_number_range")
    if expected is not None and expected > max_lap_number:
        expected = None
    if expected is None:
        missing = None
        extra = []
        trailing = "unknown"
    else:
        missing = sorted(set(range(1, expected + 1)) - set(numbers))
        extra = [number for number in numbers if number > expected]
        trailing = "supported_by_result"
    started_tail = [
        number
        for number in extra
        if participation == "dnf" and number == expected + 1 and number not in timed
    ]
    unexpected_extra = sorted(set(extra) - set(started_tail))
    if unexpected_extra:
        flags.append("unexplained_extra_laps")
    conflicts = any("conflicting_record" in audit.flags_for("laps", row) for row in laps)
    if conflicts:
        flags.append("conflicting_lap_records")
    if expected is None:
        flags.append("completed_lap_coverage_unknown")
    if not statuses_known:
        flags.append("participation_status_unknown")
    if missing:
        flags.append("missing_completed_laps")
    internal_missing = None
    if not numbers:
        internal_missing = []
    elif numbers[-1] <= max_lap_number:
        internal_missing = sorted(set(range(numbers[0], numbers[-1] + 1)) - set(numbers))
    return {
        "observed_unique_laps": len(numbers),
        "observed_lap_numbers": numbers,
        "positive_timed_unique_laps": len(timed),
        "observed_first_lap": numbers[0] if numbers else None,
        "observed_last_lap": numbers[-1] if numbers else None,
        "internal_missing_laps": internal_missing,
        "expected_completed_laps": expected,
        "missing_completed_laps": missing,
        "extra_lap_numbers": extra,
        "retirement_started_lap_numbers": started_tail,
        "participation_status": participation,
        "trailing_coverage": trailing,
        "result_source": _ref(result) if result is not None else None,
        "coverage_complete": expected is not None and statuses_known and not flags,
        "flags": sorted(flags),
    }


def _stint_audits(audit):
    result = []
    for index, row in enumerate(audit.tables["stints"]):
        flags = audit.row_flags("stints", index)
        start, end = row.get("lap_start"), row.get("lap_end")
        identity = (row.get("session_key"), row.get("driver_number"))
        laps = [
            lap
            for lap in audit.tables["laps"]
            if (lap.get("session_key"), lap.get("driver_number")) == identity
        ]
        numbers = {lap.get("lap_number") for lap in laps}
        valid = start is not None and end is not None and 0 < start <= end
        if not valid:
            flags.add("invalid_stint_range")
        else:
            if start not in numbers or end not in numbers:
                flags.add("missing_boundary_lap")
            peers = [
                peer
                for peer in audit.tables["stints"]
                if (peer.get("session_key"), peer.get("driver_number")) == identity
                and peer.get("stint_number") != row.get("stint_number")
                and peer.get("lap_start") is not None
                and peer.get("lap_end") is not None
            ]
            if any(peer["lap_start"] <= end and peer["lap_end"] >= start for peer in peers):
                flags.add("stint_overlap")
            previous = [peer["lap_end"] for peer in peers if peer["lap_end"] < start]
            if previous and max(previous) < start - 1:
                flags.add("stint_gap")
            if start > 1:
                pits = [
                    pit
                    for pit in audit.tables["pit"]
                    if (pit.get("session_key"), pit.get("driver_number")) == identity
                    and pit.get("lap_number") in {start - 1, start}
                ]
                if not pits:
                    flags.add("stint_start_without_pit_evidence")
                else:
                    flags.add("pit_boundary_semantics_uncertain")
                first = [lap for lap in laps if lap.get("lap_number") == start]
                if first and not any(lap.get("is_pit_out_lap") is True for lap in first):
                    flags.add("stint_start_pit_out_disagreement")
        if row.get("tyre_age_at_start") is None:
            flags.add("tyre_age_unavailable")
        result.append(
            {
                **_ref(row),
                "session_key": row.get("session_key"),
                "driver_number": row.get("driver_number"),
                "stint_number": row.get("stint_number"),
                "lap_start": start,
                "lap_end": end,
                "flags": sorted(flags),
            }
        )
    return result


def _control_event(row):
    """Return a state transition; unknown control instructions remain uncertain."""
    if any(row.get(field) is None for field in ("category", "message")):
        return "uncertain", "global"
    message = (row.get("message") or "").upper()
    category = (row.get("category") or "").upper()
    flag = (row.get("flag") or "").upper()
    scope = (row.get("scope") or "").upper()
    key = f"{scope}:{row.get('sector')}:{row.get('driver_number')}"
    control_instruction = category in {"SAFETYCAR", "VIRTUALSAFETYCAR"} or message.startswith(
        ("SAFETY CAR ", "VIRTUAL SAFETY CAR ", "VSC ")
    )
    if control_instruction and ("VIRTUAL SAFETY CAR" in message or "VSC" in message):
        if "ENDED" in message:
            return "end", "vsc"
        if "DEPLOYED" in message:
            return "start", "vsc"
        if "ENDING" in message:
            return "retain", "vsc"
        return "uncertain", "global"
    if control_instruction:
        if "DEPLOYED" in message:
            return "start", "sc"
        if "RETURNED TO PITS" in message or "SAFETY CAR ENDED" in message:
            return "end", "sc"
        if "IN THIS LAP" in message:
            return "retain", "sc"
        # Messages about lights, pit exit and procedural instructions do not end SC.
        return "uncertain", "global"
    if flag == "RED" or message.startswith("RED FLAG"):
        return "start", "red"
    if flag in {"YELLOW", "DOUBLE YELLOW", "TRACK SURFACE SLIPPERY"}:
        if scope not in {"TRACK", "SECTOR", "DRIVER"}:
            return "uncertain", "global"
        if (scope == "SECTOR" and row.get("sector") is None) or (
            scope == "DRIVER" and row.get("driver_number") is None
        ):
            return "uncertain", "global"
        return ("start", "yellow:track") if scope == "TRACK" else ("start", f"yellow:{key}")
    if flag in {"GREEN", "CLEAR"}:
        if "PIT EXIT" in message or "PIT ENTRY" in message:
            return "ignore", "global"
        if scope == "TRACK":
            return "clear", "global"
        if scope in {"SECTOR", "DRIVER"}:
            return "end", f"yellow:{key}"
        return "uncertain", "global"
    if category in {"SAFETYCAR", "VIRTUALSAFETYCAR"}:
        return "uncertain", "global"
    return "ignore", "global"


def _neutralization(audit, session, driver_number, start, duration):
    if start is None or duration is None or duration <= 0:
        return "unknown", []
    try:
        end = start + timedelta(seconds=duration)
    except OverflowError:
        return "unknown", []
    rows = [
        row
        for row in audit.tables["race_control"]
        if row.get("session_key") == session
        and not (
            (row.get("scope") or "").upper() == "DRIVER"
            and row.get("driver_number") is not None
            and row["driver_number"] != driver_number
        )
    ]
    malformed = any(
        row.get("date") is None
        or not audit.joinable("race_control", row)
        or row.get("validation_errors")
        for row in rows
    )
    ordered = sorted([row for row in rows if row.get("date") is not None], key=lambda r: r["date"])
    active = set()
    known = False
    uncertain = malformed
    affected = False
    interval_unknown = False
    sources = []
    for row in ordered:
        if row["date"] >= end:
            break
        if row["date"] > start:
            if active:
                affected = True
            if not known or uncertain:
                interval_unknown = True
        action, target = _control_event(row)
        if action != "ignore":
            sources.append(_ref(row))
        if action == "clear":
            active.clear()
            known = True
            if not malformed:
                uncertain = False
        elif action == "start":
            active.add(target)
        elif action == "end":
            if target not in active:
                if target.startswith("yellow:"):
                    # An unmatched local clear is evidence about its scope now;
                    # it cannot explain the earlier part of this lap or taint
                    # a later lap after the clear indefinitely.
                    if row["date"] > start:
                        interval_unknown = True
                else:
                    uncertain = True
            active.discard(target)
        elif action == "retain":
            if target not in active:
                uncertain = True
        elif action == "uncertain":
            uncertain = True
        if row["date"] >= start and active:
            affected = True
        if row["date"] >= start and (not known or uncertain):
            # Retain uncertainty for the whole lap even if cleared later in it.
            malformed = True
    if active:
        affected = True
    if affected:
        return "affected", sources
    return (
        "clear" if known and not uncertain and not malformed and not interval_unknown else "unknown"
    ), sources


def _weather(audit, session, start, compound, max_age):
    wet_compound = compound in _WETS
    if start is None:
        return ("wet_evidence" if wet_compound else "unknown"), None, None
    rows = [
        row
        for row in audit.tables["weather"]
        if row.get("session_key") == session
        and row.get("date") is not None
        and row["date"] <= start
    ]
    if not rows:
        return ("wet_evidence" if wet_compound else "unknown"), None, None
    latest = max(row["date"] for row in rows)
    candidates = [row for row in rows if row["date"] == latest]
    row = audit.canonical("weather", (session, latest))
    age = (start - latest).total_seconds()
    source = _ref(candidates[0]) if len(candidates) == 1 else None
    if wet_compound:
        return "wet_evidence", source, age
    if row is None or not audit.joinable("weather", row) or age > max_age:
        return "unknown", source, age
    if row.get("rainfall") == 1:
        return "wet_evidence", _ref(row), age
    if row.get("rainfall") == 0 and compound in _SLICKS:
        return "dry_candidate", _ref(row), age
    return "unknown", _ref(row), age


def _lap_audits(audit, config, stint_audits):
    result = []
    for index, row in enumerate(audit.tables["laps"]):
        flags = audit.row_flags("laps", index)
        session, number, lap = (
            row.get("session_key"),
            row.get("driver_number"),
            row.get("lap_number"),
        )
        descriptive = set(flags)
        stints = [
            stint
            for stint in audit.tables["stints"]
            if stint.get("session_key") == session
            and stint.get("driver_number") == number
            and lap is not None
            and stint.get("lap_start") is not None
            and stint.get("lap_end") is not None
            and stint["lap_start"] <= lap <= stint["lap_end"]
        ]
        distinct = {}
        for stint in stints:
            distinct.setdefault(_fingerprint(stint), stint)
        joined = next(iter(distinct.values())) if len(distinct) == 1 else None
        if joined is not None and not audit.joinable("stints", joined):
            joined = None
        stint_join = "matched" if joined is not None else "ambiguous" if stints else "unmatched"
        compound = joined.get("compound") if joined is not None else None
        age = None
        if joined is None:
            descriptive.add(f"{stint_join}_stint")
        else:
            for field in REQUIRED_FIELDS["stints"]:
                if joined.get(field) is None:
                    descriptive.add(f"missing_stint:{field}")
            if joined.get("validation_errors"):
                descriptive.add("invalid_stint_fields")
            if joined.get("tyre_age_at_start") is not None:
                age = joined["tyre_age_at_start"] + lap - joined["lap_start"]
        for stint_audit in stint_audits:
            if (
                stint_audit["session_key"] == session
                and stint_audit["driver_number"] == number
                and stint_audit["lap_start"] is not None
                and lap in {stint_audit["lap_start"] - 1, stint_audit["lap_start"]}
                and set(stint_audit["flags"])
                & {
                    "stint_start_without_pit_evidence",
                    "stint_start_pit_out_disagreement",
                    "stint_gap",
                    "stint_overlap",
                    "invalid_stint_range",
                }
            ):
                descriptive.add("stint_boundary_inconsistent")
        if age is None:
            flags.add("tyre_age_unavailable")
        if compound is None:
            flags.add("compound_unavailable")
        if lap == 1:
            flags.add("opening_lap")
        if row.get("is_pit_out_lap") is True:
            flags.add("observed_pit_out_lap")
        pits = [
            pit
            for pit in audit.tables["pit"]
            if pit.get("session_key") == session
            and pit.get("driver_number") == number
            and pit.get("lap_number") is not None
            and lap in (pit["lap_number"], pit["lap_number"] + 1)
        ]
        if pits:
            flags.add("pit_associated_lap")
            flags.add("pit_boundary_semantics_uncertain")
            if any(pit.get("lap_number") == lap - 1 for pit in pits):
                if row.get("is_pit_out_lap") is False:
                    flags.add("pit_out_evidence_disagreement")
        duration = row.get("lap_duration")
        if duration is None or duration <= 0:
            flags.add("invalid_lap_duration")
            descriptive.add("invalid_lap_duration")
        elif (
            not config["min_lap_duration_seconds"] <= duration <= config["max_lap_duration_seconds"]
        ):
            flags.add("extreme_lap_duration")
        sectors = [row.get(f"duration_sector_{sector}") for sector in (1, 2, 3)]
        if any(sector is None for sector in sectors):
            flags.add("sector_timing_unavailable")
        elif (
            duration is not None
            and abs(sum(sectors) - duration) > config["sector_tolerance_seconds"]
        ):
            flags.add("sector_total_disagreement")
        if row.get("date_start") is None:
            flags.add("lap_start_unavailable")
        if lap is not None:
            previous = audit.canonical("laps", (session, number, lap - 1))
            if (
                previous
                and previous.get("date_start") is not None
                and row.get("date_start") is not None
            ):
                if previous.get("lap_duration") is not None and previous["lap_duration"] > 0:
                    gap = (row["date_start"] - previous["date_start"]).total_seconds() - previous[
                        "lap_duration"
                    ]
                    if gap < -config["timing_tolerance_seconds"]:
                        flags.add("lap_timing_overlap")
                    elif gap > config["timing_tolerance_seconds"]:
                        flags.add("lap_timing_gap")
        weather, weather_source, weather_age = _weather(
            audit, session, row.get("date_start"), compound, config["weather_max_age_seconds"]
        )
        control_duration = duration
        if duration is not None and duration > config["max_lap_duration_seconds"]:
            control_duration = None
        neutralization, control_sources = _neutralization(
            audit, session, number, row.get("date_start"), control_duration
        )
        if weather != "dry_candidate":
            flags.add("wet_condition_evidence" if weather == "wet_evidence" else "weather_unknown")
        if neutralization != "clear":
            flags.add(f"neutralization_{neutralization}")
        flags.update(descriptive)
        exclusions = set(flags)
        result.append(
            {
                **_ref(row),
                "session_key": session,
                "driver_number": number,
                "lap_number": lap,
                "observed": {
                    "date_start": row.get("date_start"),
                    "lap_duration": duration,
                    "is_pit_out_lap": row.get("is_pit_out_lap"),
                },
                "stint_join": stint_join,
                "stint_sources": [_ref(stint) for stint in stints],
                "compound": compound,
                "tyre_age_before_lap": age,
                "weather_classification": weather,
                "weather_source": weather_source,
                "weather_sample_age_seconds": weather_age,
                "neutralization": neutralization,
                "control_sources": control_sources,
                "pit_sources": [_ref(pit) for pit in pits],
                "flags": sorted(flags),
                "descriptive_exclusion_reasons": sorted(descriptive),
                "exclusion_reasons": sorted(exclusions),
                "descriptive_eligible": not descriptive,
                "dry_pace_eligible": not exclusions,
            }
        )
    return result


def _pit_audits(audit, config):
    result = []
    for index, row in enumerate(audit.tables["pit"]):
        flags = audit.row_flags("pit", index)
        if "pit_duration_alias_conflict" in row.get("validation_errors", []):
            flags.add("pit_duration_alias_conflict")
        lane = row.get("effective_lane_duration")
        stop = row.get("stop_duration")
        if lane is None or lane <= 0:
            flags.add("lane_duration_unavailable")
        if stop is None:
            flags.add("stop_duration_unavailable")
        elif stop <= 0:
            flags.add("invalid_stop_duration")
        lap = audit.canonical(
            "laps", (row.get("session_key"), row.get("driver_number"), row.get("lap_number"))
        )
        if lap is None:
            flags.add("unmatched_lap")
        if row.get("date") is not None and lap is not None:
            start, duration = lap.get("date_start"), lap.get("lap_duration")
            if (
                start is not None
                and duration is not None
                and 0 < duration <= config["max_lap_duration_seconds"]
            ):
                tolerance = timedelta(seconds=config["timing_tolerance_seconds"])
                try:
                    lower = start - tolerance
                    upper = start + timedelta(seconds=duration) + tolerance
                    if not lower <= row["date"] <= upper:
                        flags.add("pit_timestamp_outside_reported_lap")
                except OverflowError:
                    flags.add("pit_timestamp_alignment_unavailable")
            else:
                flags.add("pit_timestamp_alignment_unavailable")
        lane_exclusions = flags - {
            "stop_duration_unavailable",
            "invalid_stop_duration",
            "pit_timestamp_outside_reported_lap",
            "pit_timestamp_alignment_unavailable",
        }
        stop_exclusions = flags - {
            "lane_duration_unavailable",
            "pit_duration_alias_conflict",
            "pit_timestamp_outside_reported_lap",
            "pit_timestamp_alignment_unavailable",
        }
        # Alias conflict concerns lane measurements; retain independently observed stop time.
        if row.get("validation_errors") == ["pit_duration_alias_conflict"]:
            stop_exclusions.discard("invalid_source_fields")
        result.append(
            {
                **_ref(row),
                "session_key": row.get("session_key"),
                "driver_number": row.get("driver_number"),
                "lap_number": row.get("lap_number"),
                "date": row.get("date"),
                "lane_duration_seconds": lane,
                "lane_duration_source": row.get("lane_duration_source"),
                "stationary_duration_seconds": stop,
                "duration_meaning": (
                    "observed pit-lane/stationary duration; not incremental race-time loss"
                ),
                "timestamp_semantics": "source date does not establish pit entry or exit",
                "flags": sorted(flags),
                "lane_exclusion_reasons": sorted(lane_exclusions),
                "stationary_exclusion_reasons": sorted(stop_exclusions),
                "lane_eligible": not lane_exclusions,
                "stationary_eligible": not stop_exclusions,
            }
        )
    return result


def _exclusions(laps):
    return {
        "purpose": "dry_pace_investigation",
        "distinct_excluded_rows": sum(bool(lap["exclusion_reasons"]) for lap in laps),
        "reasons": _counts(reason for lap in laps for reason in lap["exclusion_reasons"]),
        "reason_counts_overlap": True,
    }


def _purpose(eligible, total, blockers, *, unconditional=None):
    blockers = sorted(set(blockers))
    if unconditional:
        status = "blocked"
        blockers.append(unconditional)
    elif not eligible:
        status = "blocked"
        blockers.append("no_eligible_rows")
    elif blockers:
        status = "limited"
    else:
        status = "ready"
    return {
        "status": status,
        "counts": {"eligible_rows": eligible, "total_rows": total},
        "blockers": blockers,
    }


def _readiness(audit, session, driver_reports, laps, pits, complete):
    common = []
    if not complete:
        common.append("source_import_not_complete")
    metadata = audit.canonical("sessions", (session,))
    if metadata is None or any(
        metadata.get(field) is None for field in REQUIRED_FIELDS["sessions"]
    ):
        common.append("session_metadata_missing_or_conflicting")
    elif not audit.joinable("sessions", metadata):
        common.append("session_meeting_join_unresolved")
    if metadata is not None:
        meeting = audit.canonical("meetings", (metadata.get("meeting_key"),))
        if meeting is None or any(
            meeting.get(field) is None for field in REQUIRED_FIELDS["meetings"]
        ):
            common.append("meeting_metadata_missing_or_conflicting")
    if any(item["driver_join"] != "matched" for item in driver_reports):
        common.append("driver_metadata_join_unresolved")
    if any(
        item["tables"]["drivers"]["rows_with_missing_required"]
        or item["tables"]["drivers"]["validation_errors"]
        for item in driver_reports
    ):
        common.append("driver_metadata_missing_or_invalid")
    coverage = [item["coverage"] for item in driver_reports]
    if not coverage or any(not item["coverage_complete"] for item in coverage):
        common.append("completed_lap_coverage_unresolved")
    if any(lap["descriptive_exclusion_reasons"] for lap in laps):
        common.append("excluded_or_ambiguous_lap_stint_rows")
    descriptive = _purpose(sum(lap["descriptive_eligible"] for lap in laps), len(laps), common)
    dry_blockers = list(common)
    if any(lap["weather_classification"] == "unknown" for lap in laps):
        dry_blockers.append("weather_unknown_for_some_laps")
    if any(lap["neutralization"] == "unknown" for lap in laps):
        dry_blockers.append("neutralization_unknown_for_some_laps")
    dry = _purpose(sum(lap["dry_pace_eligible"] for lap in laps), len(laps), dry_blockers)
    dry["interpretation"] = (
        "Eligible rows are dry candidates only; no certified dry track or causal tire model."
    )
    pit_common = [
        reason
        for reason in common
        if reason
        not in {"completed_lap_coverage_unresolved", "excluded_or_ambiguous_lap_stint_rows"}
    ]
    lane_blockers = pit_common + (
        ["excluded_pit_lane_rows"] if any(not pit["lane_eligible"] for pit in pits) else []
    )
    stop_blockers = pit_common + (
        ["missing_or_excluded_stationary_rows"]
        if any(not pit["stationary_eligible"] for pit in pits)
        else []
    )
    lane = _purpose(sum(pit["lane_eligible"] for pit in pits), len(pits), lane_blockers)
    stationary = _purpose(sum(pit["stationary_eligible"] for pit in pits), len(pits), stop_blockers)
    lane["counts"]["measured_rows"] = sum(pit["lane_duration_seconds"] is not None for pit in pits)
    lane["counts"]["missing_rows"] = sum(pit["lane_duration_seconds"] is None for pit in pits)
    stationary["counts"]["measured_rows"] = sum(
        pit["stationary_duration_seconds"] is not None for pit in pits
    )
    stationary["counts"]["missing_rows"] = sum(
        pit["stationary_duration_seconds"] is None for pit in pits
    )
    return {
        "descriptive_lap_stint": descriptive,
        "dry_pace_investigation": dry,
        "pit_lane_description": lane,
        "stationary_stop_description": stationary,
        "incremental_pit_loss": _purpose(
            0, len(pits), [], unconditional="no_stay_on_track_counterfactual_measurement"
        ),
        "decision_time_features": _purpose(
            0, len(laps), [], unconditional="publication_times_and_availability_delays_unverified"
        ),
    }


def _download_status(manifest, session_key, metadata):
    metadata = metadata or {}
    requests = [
        request
        for request in manifest.get("requests", [])
        if request.get("params", {}).get("session_key") == session_key
        or (
            request.get("endpoint") == "meetings"
            and request.get("params", {}).get("meeting_key") == metadata.get("meeting_key")
        )
        or (
            request.get("endpoint") == "sessions"
            and request.get("params", {}).get("year") == metadata.get("year")
        )
    ]
    expected = set(SCHEMAS)
    present = {request.get("endpoint") for request in requests}
    missing = sorted(expected - present)
    failures = [
        {key: request.get(key) for key in ("id", "endpoint", "params", "status", "error")}
        for request in requests
        if request.get("status") != "success"
    ]
    return {
        "status": "unverified"
        if not requests
        else "partial"
        if failures or missing
        else "complete",
        "missing_request_endpoints": missing,
        "failures": failures,
    }


def build_report(tables: dict[str, list[dict]], manifest: dict, config: dict) -> dict:
    """Audit normalized rows without mutation, source deletion, clock, or network."""
    audit = _Audit(tables)
    stints = _stint_audits(audit)
    laps = _lap_audits(audit, config, stints)
    pits = _pit_audits(audit, config)
    session_keys = sorted(
        {
            row["session_key"]
            for rows in audit.tables.values()
            for row in rows
            if row.get("session_key") is not None
        },
        key=_sort_key,
    )
    sessions = []
    complete = manifest.get("status") == "complete"
    for session_key in session_keys:
        metadata = audit.canonical("sessions", (session_key,))
        numbers = sorted(
            {
                row["driver_number"]
                for table in _DRIVER_TABLES
                for row in audit.tables[table]
                if row.get("session_key") == session_key and row.get("driver_number") is not None
            }
        )
        driver_reports = []
        session_laps = [lap for lap in laps if lap["session_key"] == session_key]
        session_pits = [pit for pit in pits if pit["session_key"] == session_key]
        session_tables = {}
        for table, rows in audit.tables.items():
            selected = [
                index
                for index, row in enumerate(rows)
                if row.get("session_key") == session_key
                or (
                    table == "meetings"
                    and metadata
                    and row.get("meeting_key") == metadata.get("meeting_key")
                )
            ]
            session_tables[table] = audit.summary(table, selected)
        for number in numbers:
            source_driver = audit.canonical("drivers", (session_key, number))
            driver_laps = [lap for lap in session_laps if lap["driver_number"] == number]
            driver_tables = {
                table: audit.summary(
                    table,
                    [
                        index
                        for index, row in enumerate(audit.tables[table])
                        if row.get("session_key") == session_key
                        and row.get("driver_number") == number
                    ],
                )
                for table in sorted(_DRIVER_TABLES)
            }
            driver_reports.append(
                {
                    "driver_number": number,
                    "full_name": source_driver.get("full_name") if source_driver else None,
                    "driver_join": "matched"
                    if source_driver is not None and audit.joinable("drivers", source_driver)
                    else "unmatched",
                    "coverage": _driver_coverage(
                        audit, session_key, number, config["max_lap_number"]
                    ),
                    "tables": driver_tables,
                    "lap_flags": _counts(flag for lap in driver_laps for flag in lap["flags"]),
                    "lap_exclusions": _exclusions(driver_laps),
                    "descriptive_eligible_rows": sum(
                        lap["descriptive_eligible"] for lap in driver_laps
                    ),
                    "dry_pace_eligible_rows": sum(lap["dry_pace_eligible"] for lap in driver_laps),
                    "tyre_age_available_rows": sum(
                        lap["tyre_age_before_lap"] is not None for lap in driver_laps
                    ),
                }
            )
        readiness = _readiness(
            audit, session_key, driver_reports, session_laps, session_pits, complete
        )
        sessions.append(
            {
                "session_key": session_key,
                "source_download": _download_status(manifest, session_key, metadata),
                "identity": {
                    field: metadata.get(field) if metadata else None
                    for field in SCHEMAS["sessions"]
                },
                "tables": session_tables,
                "drivers": driver_reports,
                "lap_flags": _counts(flag for lap in session_laps for flag in lap["flags"]),
                "lap_exclusions": _exclusions(session_laps),
                "wet_condition_evidence_rows": sum(
                    lap["weather_classification"] == "wet_evidence" for lap in session_laps
                ),
                "dry_session_certified": False,
                "readiness": readiness,
            }
        )
    blockers = []
    if any(
        any(flag.startswith("unmatched_") or flag == "conflicting_record" for flag in flags)
        for rows in audit.flags.values()
        for flags in rows
    ):
        blockers.append("orphan_or_ambiguous_source_rows")
    if not complete:
        blockers.append("source_import_not_complete")
    if not sessions:
        blockers.append("no_resolved_sessions")
    if any(
        session["readiness"]["descriptive_lap_stint"]["status"] != "ready" for session in sessions
    ):
        blockers.append("descriptive_coverage_or_joins_not_ready")
    row_issues = {
        table: [
            {**_ref(row), "flags": sorted(audit.row_flags(table, index))}
            for index, row in enumerate(rows)
            if audit.row_flags(table, index)
        ]
        for table, rows in audit.tables.items()
    }
    result = {
        "quality_version": QUALITY_VERSION,
        "schema_version": manifest.get("schema_version", 1),
        "snapshot": {
            "snapshot_id": manifest.get("snapshot_id"),
            "status": manifest.get("status"),
            "source_url": manifest.get("source_url"),
            "manifest_content_sha256": hashlib.sha256(_canonical(manifest).encode()).hexdigest(),
        },
        "source_errors": manifest.get("errors", []),
        "source_failures": [
            {key: request.get(key) for key in ("id", "endpoint", "params", "status", "error")}
            for request in manifest.get("requests", [])
            if request.get("status") != "success"
        ],
        "assumptions": dict(config),
        "limitations": [
            "Historical event timestamps are not necessarily publication timestamps.",
            (
                "Pit-exit green lights and session-start messages alone do not certify "
                "a track-clear baseline; unknown neutralization is an audit uncertainty, "
                "not evidence of wet weather."
            ),
            (
                "Completed stint outcomes and derived tire ages are retrospective; "
                "no decision-time backfill."
            ),
            (
                "Zero rainfall plus a slick compound means dry candidate, "
                "not certified dry conditions."
            ),
            "Pit lane and stationary durations are not incremental race-time pit loss.",
            (
                "Source pit dates do not establish entry/exit; "
                "reported pit lap and following lap are conservatively flagged."
            ),
            "Lap start timestamps are approximate; timing tolerances are audit assumptions.",
            (
                "All source rows are retained; overlapping exclusion reason counts "
                "do not sum to distinct exclusions."
            ),
        ],
        "table_audits": audit.summaries,
        "source_row_issues": row_issues,
        "sessions": sessions,
        "lap_audit": laps,
        "stint_audit": stints,
        "pit_audit": pits,
        "circuit_gate": {
            "status": "blocked" if blockers else "passed",
            "purpose": "descriptive_lap_stint_suitability_only",
            "blockers": blockers,
            "does_not_establish": [
                "dry_session",
                "causal_tire_model",
                "incremental_pit_loss",
                "decision_time_features",
                "historical_arena_calibration",
            ],
        },
    }
    return _json_safe(result)


def render_markdown(report: dict) -> str:
    """Render the same evidence and limitations without an independent calculation."""
    snapshot = report["snapshot"]
    lines = [
        "# PitWall historical completeness and quality audit",
        "",
        f"Snapshot: `{snapshot['snapshot_id']}`. Import: **{snapshot['status']}**.",
        f"Source: {snapshot['source_url']}. Quality version: {report['quality_version']}.",
        "",
        f"Circuit gate: **{report['circuit_gate']['status']}** "
        "(descriptive lap/stint suitability only).",
        "",
    ]
    for failure in report["source_failures"]:
        lines.append(
            f"- Source failure: `{failure['endpoint']}` `{failure['params']}`: "
            f"{failure['error'] or failure['status']}"
        )
    for error in report["source_errors"]:
        lines.append(f"- Import error: {error}")
    for blocker in report["circuit_gate"]["blockers"]:
        lines.append(f"- Blocker: `{blocker}`")
    lines.extend(
        [
            "",
            "## Source tables",
            "",
            "| Table | Rows | Missing required rows | Duplicate extras | "
            "Conflicting rows | Unmatched joins |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for table, counts in report["table_audits"].items():
        lines.append(
            f"| {table} | {counts['rows']} | {counts['rows_with_missing_required']} | "
            f"{counts['exact_duplicate_extra_rows']} | {counts['conflicting_rows']} | "
            f"{sum(counts['unmatched_joins'].values())} |"
        )
    for session in report["sessions"]:
        identity = session["identity"]
        lines.extend(
            [
                "",
                f"## Session {session['session_key']} — "
                f"{identity['country_name']} {identity['year']}",
                "",
                f"Meeting `{identity['meeting_key']}`, circuit `{identity['circuit_key']}`, "
                f"{identity['session_name']}; start {identity['date_start']}.",
                "",
                "| Driver | Participation | Expected completed | Observed unique | "
                "Missing completed | Extra laps | Coverage | Dry candidates eligible |",
                "| --- | --- | ---: | ---: | --- | --- | --- | ---: |",
            ]
        )
        for driver in session["drivers"]:
            coverage = driver["coverage"]
            lines.append(
                f"| {driver['driver_number']} {driver['full_name'] or '(unmatched)'} | "
                f"{coverage['participation_status']} | {coverage['expected_completed_laps']} | "
                f"{coverage['observed_unique_laps']} | {coverage['missing_completed_laps']} | "
                f"{coverage['extra_lap_numbers']} | "
                f"{'supported' if coverage['coverage_complete'] else 'unresolved'} | "
                f"{driver['dry_pace_eligible_rows']} |"
            )
        lines.extend(
            [
                "",
                "| Purpose | Readiness | Eligible / total | Blockers |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for purpose, readiness in session["readiness"].items():
            counts = readiness["counts"]
            lines.append(
                f"| {purpose} | **{readiness['status']}** | "
                f"{counts['eligible_rows']} / {counts['total_rows']} | "
                f"{', '.join(readiness['blockers']) or 'none under this contract'} |"
            )
        exclusions = session["lap_exclusions"]
        lines.extend(
            [
                "",
                f"Dry-pace exclusions: **{exclusions['distinct_excluded_rows']} "
                "distinct source rows**. Reasons overlap:",
                "",
            ]
        )
        for reason, count in exclusions["reasons"].items():
            lines.append(f"- `{reason}`: {count}")
        lines.extend(
            ["", "Per-table missing required fields (null and absent remain unknown):", ""]
        )
        for table, summary in session["tables"].items():
            missing = {
                field: count for field, count in summary["missing_required"].items() if count
            }
            if missing:
                lines.append(
                    f"- {table}: "
                    + ", ".join(f"`{field}`={count}" for field, count in missing.items())
                )
    lines.extend(["", "## Interpretation and provenance", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.extend(
        [
            "",
            "The JSON report includes every per-lap flag/exclusion and source reference, "
            "every stint/pit audit, per-driver/table counts, and the source manifest content hash. "
            "Raw observations and normalized tables retain every row. "
            "No tire fitting or simulator calibration was performed.",
            "",
        ]
    )
    return "\n".join(lines)
