"""Frozen-cohort descriptive statistics and standalone HTML/SVG; never a pace model."""

# Inline SVG/HTML intentionally keeps markup together.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import base64
import json
import math
import platform
import sys
from collections import defaultdict
from html import escape
from pathlib import Path

from .cache import load_snapshot
from .cohort import COHORT_VERSION, partition_rows
from .normalize import canonical, digest, normalize_tables
from .quality import build_report

VERSION = "f1.3-descriptive-v1"
QUANTILES = "Hyndman-Fan type 7: sorted x, h=(n-1)*p, linear interpolation; IQR=Q3-Q1"
LIMITS = (
    "Recorded elapsed laps from one selected late-race window; laps are dependent observations. "
    "Race-lap alignment is not simultaneous clock time. Deletion notices are retrospective "
    "annotations, not a determination of final legal status. The sensitivity subset is not "
    "certified clean. No intrinsic compound ranking, causal degradation, whole-race extrapolation "
    "or calibration is supported. The full circuit gate remains blocked."
)


def key(row):
    return row["source_request"], row["source_row"]


def ref(row):
    return dict(zip(("source_request", "source_row"), key(row), strict=True))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verified_inputs(snapshot, cohort, pin_path):
    """Validate a versioned trust anchor, every artifact and its raw/code provenance."""
    pin_bytes = pin_path.read_bytes()
    pin = json.loads(pin_bytes)
    require(pin["version"] == VERSION, "unsupported descriptive version")
    body = (cohort / "manifest.json").read_bytes()
    require(digest(body) == pin["cohort_manifest_sha256"], "frozen manifest hash mismatch")
    build = json.loads(body)
    require(build["status"] == "complete", "incomplete cohort artifacts")
    require(
        set(build["artifacts"]) == {"membership.json", "exclusions.json", "audit.json"},
        "unexpected cohort artifact set",
    )
    docs = {}
    for name, expected in build["artifacts"].items():
        content = (cohort / name).read_bytes()
        require(digest(content) == expected, f"artifact hash mismatch: {name}")
        docs[name] = json.loads(content)
    provenance = build["provenance"]
    require(all(d["provenance"] == provenance for d in docs.values()), "provenance disagreement")
    require(provenance["cohort_version"] == COHORT_VERSION, "unsupported frozen cohort version")
    require(
        digest((snapshot / "manifest.json").read_bytes()) == provenance["source_manifest_sha256"],
        "source manifest mismatch",
    )
    manifest, raw = load_snapshot(snapshot)
    require(manifest["snapshot_id"] == provenance["source_snapshot_id"], "snapshot ID mismatch")
    require(manifest["config"] == provenance["config"], "snapshot config mismatch")
    require(digest(canonical(manifest["config"])) == provenance["config_sha256"], "config hash")
    code = provenance["implementation_sha256"]
    require(digest(canonical(code)) == provenance["implementation_bundle_sha256"], "code bundle")
    for name, expected in code.items():
        require(Path(name).name == name and name.endswith(".py"), "unsafe code reference")
        require(
            digest(Path(__file__).with_name(name).read_bytes()) == expected, f"code drift: {name}"
        )
    audit = docs["audit.json"]
    require(
        digest(canonical(audit["selection"])) == provenance["selection_sha256"], "selection hash"
    )
    tables = normalize_tables(raw)
    quality = build_report(tables, manifest, manifest["config"])
    quality["provenance"] = {
        k: provenance[k] for k in ("source_manifest_sha256", "source_snapshot_id", "config")
    }
    require(digest(canonical(quality)) == provenance["quality_report_sha256"], "quality mismatch")
    members, excluded = partition_rows(quality, audit["selection"])
    require(members == docs["membership.json"]["rows"], "frozen membership changed")
    require(excluded == docs["exclusions.json"]["rows"], "frozen exclusions changed")
    require(audit["full_circuit_gate"] == quality["circuit_gate"], "circuit gate mismatch")
    require(audit["full_circuit_gate"]["status"] == "blocked", "expected blocked full gate")
    require(
        audit["suitability"]["descriptive_late_race"]["status"] == "suitable_with_limits",
        "frozen cohort not suitable for description",
    )
    evidence = {
        "frozen_cohort_provenance": provenance,
        "cohort_manifest_sha256": digest(body),
        "cohort_artifacts": build["artifacts"],
        "descriptive_config": pin,
        "descriptive_config_sha256": digest(pin_bytes),
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "python_version": platform.python_version(),
    }
    return tables, members, excluded, audit, evidence


def summarize(rows):
    values = sorted(r["lap_duration_seconds"] for r in rows)
    require(
        all(type(v) in (float, int) and math.isfinite(v) and v > 0 for v in values),
        "missing or invalid observed lap duration",
    )

    def quantile(p):
        if not values:
            return None
        h = (len(values) - 1) * p
        lo, hi = math.floor(h), math.ceil(h)
        return values[lo] + (h - lo) * (values[hi] - values[lo])

    q1, median, q3 = [quantile(p) for p in (0.25, 0.5, 0.75)]
    return {
        "n": len(rows),
        "race_laps": sorted(r["lap_number"] for r in rows),
        "source_rows": [ref(r) for r in rows],
        "q1_seconds": q1,
        "median_seconds": median,
        "q3_seconds": q3,
        "iqr_seconds": None if q1 is None else q3 - q1,
        "sample_note": "empty" if not rows else "small sample (n<5)" if len(rows) < 5 else None,
    }


def statistics(tables, members, excluded, audit, provenance):
    session = audit["selection"]["session_key"]
    raw_laps = [r for r in tables["laps"] if r["session_key"] == session]
    lap_map = {key(r): r for r in raw_laps}
    require(len(lap_map) == len(raw_laps), "duplicate physical source identity")
    require(
        len({key(r) for r in members + excluded}) == len(members + excluded), "partition overlap"
    )
    require(set(lap_map) == {key(r) for r in members + excluded}, "source partition mismatch")
    tags = defaultdict(list)
    for message in audit["deletions"]["messages"]:
        for source in message["included_source_rows"]:
            tags[key(source)].append(
                {**ref(message), "date": message["date"], "message": message["message"]}
            )
    require(set(tags) <= {key(r) for r in members}, "deletion outside membership")
    require(
        len(tags) == audit["deletions"]["included_rows_with_explicit_deletion"], "deletion count"
    )
    stints = {key(r): r for r in tables["stints"]}
    drivers = defaultdict(list)
    for r in tables["drivers"]:
        if r["session_key"] == session:
            drivers[r["driver_number"]].append(r)
    rows = []
    for member in members:
        lap = lap_map[key(member)]
        require(
            all(lap[f] == member[f] for f in ("session_key", "driver_number", "lap_number")),
            "lap identity join mismatch",
        )
        require(len(member["stint_sources"]) == 1, "ambiguous stint")
        stint = stints[key(member["stint_sources"][0])]
        require(
            stint["session_key"] == session
            and stint["driver_number"] == lap["driver_number"]
            and stint["lap_start"] <= lap["lap_number"] <= stint["lap_end"],
            "stint identity join mismatch",
        )
        names = drivers[lap["driver_number"]]
        require(len(names) == 1 and names[0]["full_name"], "ambiguous driver name")
        rows.append(
            {
                **ref(lap),
                "session_key": session,
                "driver_number": lap["driver_number"],
                "driver_name": names[0]["full_name"],
                "lap_number": lap["lap_number"],
                "date_start": lap["date_start"],
                "lap_duration_seconds": lap["lap_duration"],
                "stint_source": ref(stint),
                "stint_number": stint["stint_number"],
                "compound": stint["compound"],
                "deletion_notices": tags.get(key(lap), []),
            }
        )
    require(bool(rows), "empty primary cohort")
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["driver_number"], key(row["stint_source"]))].append(row)
    groups = []
    bounds = [min(r["lap_number"] for r in rows), max(r["lap_number"] for r in rows)]
    for _, group in sorted(grouped.items()):
        group.sort(key=lambda r: r["lap_number"])
        require(len({r["lap_number"] for r in group}) == len(group), "duplicate driver/stint lap")
        first = group[0]
        omitted = [r for r in group if r["deletion_notices"]]
        groups.append(
            {
                **{
                    f: first[f]
                    for f in (
                        "driver_number",
                        "driver_name",
                        "stint_number",
                        "stint_source",
                        "compound",
                    )
                },
                "primary": summarize(group),
                "sensitivity": summarize([r for r in group if not r["deletion_notices"]]),
                "omitted_tagged_rows": [ref(r) for r in omitted],
                "tagged_race_laps": [r["lap_number"] for r in omitted],
                "absent_from_primary_in_cohort_window": sorted(
                    set(range(bounds[0], bounds[1] + 1)) - {r["lap_number"] for r in group}
                ),
            }
        )
    # Validate every primary duration before computing any rendered statistics.
    summarize(rows)
    return {
        "version": VERSION,
        "provenance": provenance,
        "quantile_convention": QUANTILES,
        "small_sample_convention": "n<5 is a display caution only, never an eligibility rule",
        "limitations": LIMITS,
        "full_circuit_gate": audit["full_circuit_gate"],
        "source_snapshot_status": audit["source_snapshot_status"],
        "session_identity": audit["session_identity"],
        "race_lap_bounds": bounds,
        "reconciliation": {
            "source_laps": len(raw_laps),
            "primary": len(rows),
            "excluded": len(excluded),
            "deletion_tagged": len(tags),
            "sensitivity": len(rows) - len(tags),
        },
        "excluded_source_rows": [ref(r) for r in excluded],
        "rows": rows,
        "driver_stints": groups,
    }


def segments(rows):
    result = []
    for row in sorted(rows, key=lambda r: r["lap_number"]):
        if not result or row["lap_number"] != result[-1][-1]["lap_number"] + 1:
            result.append([])
        result[-1].append(row)
    return result


def chart(group, rows, bounds, y_bounds, evidence=None):
    """SVG export uses shared axes and breaks lines at every missing race lap."""
    evidence = evidence or {}
    session = evidence.get("session_identity", {}).get("session_key", "fixture")
    x0, x1 = bounds
    y0, y1 = y_bounds
    x = lambda lap: 85 + (lap - x0) / max(1, x1 - x0) * 865  # noqa: E731
    y = lambda seconds: 320 - (seconds - y0) / (y1 - y0) * 245  # noqa: E731
    title = f"{group['driver_number']} {group['driver_name']} · stint {group['stint_number']} · {group['compound']}"
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 440" role="img" aria-label="{escape(title)} elapsed lap times">',
        f"<title>{escape(title)}</title><desc>Recorded elapsed laps; gaps are not filled. Amber diamonds denote retrospective deletion notices, not final legal status.</desc>",
        f"<metadata>{escape(json.dumps(evidence, sort_keys=True))}</metadata>",
        '<rect width="1000" height="440" fill="white"/>',
        '<g font-family="Arial, sans-serif" font-size="15" fill="#243746">',
        f'<text x="85" y="28" font-size="19">{escape(title)}</text>',
        '<text x="85" y="54">Elapsed lap time (seconds) · shared, nonzero y-axis</text>',
    ]
    for i in range(6):
        value = y0 + (y1 - y0) * i / 5
        yy = y(value)
        out += [
            f'<path d="M85 {yy:.3f} H950" stroke="#cbd5df"/>',
            f'<text x="73" y="{yy + 5:.3f}" text-anchor="end">{value:.1f}</text>',
        ]
    for lap in range(x0, x1 + 1):
        xx = x(lap)
        out.append(f'<path d="M{xx:.3f} 320 v5" stroke="#243746"/>')
        if lap == x0 or lap == x1 or lap % 2 == 0:
            out.append(f'<text x="{xx:.3f}" y="347" text-anchor="middle">{lap}</text>')
    out.append(
        '<text x="515" y="379" text-anchor="middle">Race lap number · not simultaneous clock time</text>'
    )
    for segment in segments(rows):
        if len(segment) > 1:
            points = " ".join(
                f"{x(r['lap_number']):.3f},{y(r['lap_duration_seconds']):.3f}" for r in segment
            )
            out.append(
                f'<polyline data-laps="{",".join(str(r["lap_number"]) for r in segment)}" points="{points}" fill="none" stroke="#087e8b" stroke-width="2"/>'
            )
    for row in rows:
        xx, yy = x(row["lap_number"]), y(row["lap_duration_seconds"])
        tip = escape(
            f"Lap {row['lap_number']}: {row['lap_duration_seconds']:.3f} s; {row['source_request']} row {row['source_row']}"
            + ("; deletion notice" if row["deletion_notices"] else "")
        )
        if row["deletion_notices"]:
            out.append(
                f'<path data-tagged-lap="{row["lap_number"]}" d="M{xx:.3f} {yy - 6:.3f} l6 6 -6 6 -6 -6 Z" fill="#b45309"><title>{tip}</title></path>'
            )
        else:
            out.append(
                f'<circle cx="{xx:.3f}" cy="{yy:.3f}" r="3.5" fill="#087e8b"><title>{tip}</title></circle>'
            )
    out += [
        '<text x="85" y="412">● Observed elapsed lap   ◆ Deletion notice (retained)   Gaps: no primary observation</text>',
        f'<text x="85" y="433" font-size="12">OpenF1 · session {session} · frozen F1.2 · descriptive only · full circuit gate blocked</text></g></svg>',
    ]
    return "\n".join(out)


def number(value):
    return "—" if value is None else f"{value:.3f}"


def render(stats):
    all_rows = stats["rows"]
    durations = [r["lap_duration_seconds"] for r in all_rows]
    y_bounds = [math.floor(min(durations)) - 1, math.ceil(max(durations)) + 1]
    panels, options, table, exports = [], [], [], {}
    for index, group in enumerate(stats["driver_stints"]):
        label = f"{group['driver_number']} {group['driver_name']} / stint {group['stint_number']}"
        options.append(f'<option value="g{index}">{escape(label)}</option>')
        rows = [r for r in all_rows if key(r["stint_source"]) == key(group["stint_source"])]
        svg = chart(
            group,
            rows,
            stats["race_lap_bounds"],
            y_bounds,
            {
                "session_identity": stats["session_identity"],
                "cohort_manifest_sha256": stats["provenance"]["cohort_manifest_sha256"],
                "generator_sha256": stats["provenance"]["generator_sha256"],
            },
        )
        name = f"driver-{group['driver_number']}-stint-{group['stint_number']}.svg"
        exports[name] = svg.encode()
        download = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
        primary, sensitivity = group["primary"], group["sensitivity"]
        metrics = f"Primary n={primary['n']}; median {number(primary['median_seconds'])} s; IQR {number(primary['iqr_seconds'])} s. Sensitivity n={sensitivity['n']}; median {number(sensitivity['median_seconds'])} s; IQR {number(sensitivity['iqr_seconds'])} s."
        laps = ", ".join(map(str, primary["race_laps"]))
        absent = ", ".join(map(str, group["absent_from_primary_in_cohort_window"])) or "none"
        tagged = ", ".join(map(str, group["tagged_race_laps"])) or "none"
        details = "".join(
            f"<tr><td>{r['lap_number']}</td><td>{number(r['lap_duration_seconds'])}</td><td>{'Deletion notice' if r['deletion_notices'] else 'No mapped notice'}</td><td>{escape(r['source_request'])}:{r['source_row']}</td></tr>"
            for r in rows
        )
        caution = (
            " Small sample: interpret descriptively."
            if primary["sample_note"] or sensitivity["sample_note"]
            else ""
        )
        panels.append(f'''<section class="driver" id="g{index}"><h2>{escape(label)}</h2>
<p class="metrics">{metrics}{caution}</p><div class="chart-scroll">{svg}</div>
<p><a download="{name}" href="{download}">Export this chart as SVG</a></p>
<p><strong>Observed primary laps:</strong> {laps}.<br><strong>Absent within the cohort window:</strong> {absent}.<br><strong>Deletion-tagged laps retained:</strong> {tagged}.</p>
<details><summary>Observed values and source rows</summary><div class="table-scroll"><table><thead><tr><th>Race lap</th><th>Elapsed (s)</th><th>Annotation</th><th>Source row</th></tr></thead><tbody>{details}</tbody></table></div></details></section>''')
        table.append(
            f"<tr><th scope='row'>{escape(label)}<small>{escape(group['compound'])} · laps {min(primary['race_laps'])}–{max(primary['race_laps'])}</small></th><td>{primary['n']}</td><td>{number(primary['median_seconds'])}</td><td>{number(primary['iqr_seconds'])}</td><td>{len(group['omitted_tagged_rows'])}</td><td>{sensitivity['n']}</td><td>{number(sensitivity['median_seconds'])}</td><td>{number(sensitivity['iqr_seconds'])}</td><td>{escape(primary['sample_note'] or sensitivity['sample_note'] or '—')}</td></tr>"
        )
    counts = stats["reconciliation"]
    payload = base64.b64encode(canonical(stats)).decode()
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PitWall · Bahrain 2025 observed laps</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f8;color:#243746;font:17px/1.55 system-ui,sans-serif}}main{{max-width:1160px;margin:auto;padding:32px}}header{{border-top:6px solid #087e8b;padding:24px 0}}h1{{font:48px/1.12 Georgia,serif;margin:12px 0}}h2{{font-size:25px}}p{{max-width:85ch}}.intro{{font-size:21px}}.notice{{border-left:4px solid #b45309;padding:12px 18px;background:white}}select{{font:inherit;padding:10px;max-width:100%;border:1px solid #637c8c;background:white;color:#243746}}label{{display:block;font-weight:650;margin-bottom:8px}}.driver{{background:white;padding:24px;margin:24px 0}}.metrics{{font-variant-numeric:tabular-nums}}.chart-scroll,.table-scroll{{overflow:auto}}svg{{display:block;width:100%;min-width:1000px}}table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}th,td{{padding:12px;text-align:right;border-bottom:1px solid #cbd5df;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}thead{{background:#e1eaf0}}small{{display:block;font-weight:400}}a{{color:#086473}}a:focus-visible,select:focus-visible,summary:focus-visible{{outline:3px solid #b45309;outline-offset:3px}}summary{{cursor:pointer;padding:12px 0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}}.js .driver[hidden]{{display:none}}footer{{margin:32px 0}}@media(max-width:600px){{main{{padding:18px}}h1{{font-size:36px}}.driver{{padding:12px}}}}@media print{{.driver[hidden]{{display:block!important}}select,label{{display:none}}main{{max-width:none}}.driver{{break-inside:avoid}}svg{{min-width:0}}}}
</style></head><body><main>
<header><p>PitWall Arena / historical description / session {stats["session_identity"]["session_key"]}</p><h1>Bahrain 2025<br>Observed late-race laps</h1><p class="intro">{counts["primary"]} frozen observations across {len(stats["driver_stints"])} driver/stints. Explore recorded elapsed times and the gaps that shape this sample.</p></header>
<p class="notice"><strong>Full circuit gate: blocked. Calibration avenue: closed.</strong><br>{escape(LIMITS)}</p>
<p>Primary: <strong>{counts["primary"]} rows</strong>, including <strong>{counts["deletion_tagged"]} deletion-tagged rows</strong>. Separately labelled sensitivity: <strong>{counts["sensitivity"]} rows</strong> after omitting those tags. Primary membership never changes. Driver order is by number, not performance.</p>
<label for="driver">Select driver / stint</label><select id="driver">{"".join(options)}<option value="all">All driver/stints</option></select>
<p>Shared axes for every driver. Lines only connect consecutive observed race laps; gaps contain no invented values. On narrow screens, scroll the chart horizontally. Amber diamonds and the lap list identify deletion notices.</p>
{"".join(panels)}
<h2>Primary and deletion-omission sensitivity</h2><p>Seconds; display rounded to three decimals, full precision in JSON. This is a sensitivity comparison, not a certified-clean subset or an inference of final legal status. Counts differ by driver; shared conditions and selection prevent intrinsic compound comparisons.</p>
<div class="table-scroll"><table><thead><tr><th>Driver / stint</th><th>Primary n</th><th>Median (s)</th><th>IQR (s)</th><th>Omitted</th><th>Sensitivity n</th><th>Median (s)</th><th>IQR (s)</th><th>Sample caution</th></tr></thead><tbody>{"".join(table)}</tbody></table></div>
<h2>How to read these summaries</h2><p>{escape(QUANTILES)}. Empty groups return null statistics; a singleton has its observed value as all quantiles and zero IQR. A visible n&lt;5 caution is a display convention, not an eligibility threshold. IQR describes observed spread, not uncertainty or a confidence interval. No independence assumption is made.</p>
<p>The sample is selected from late stints in a single race. Fuel, traffic, tire age, driver/car differences and track evolution are not separated. Deletion notices and completed-stint evidence are retrospective; event times do not establish publication times. Missing stationary pit times do not invalidate elapsed-lap description; neither lane nor stationary time is incremental pit loss.</p>
<h2>Evidence and export</h2><p>{counts["source_laps"]} source laps = {counts["primary"]} primary + {counts["excluded"]} distinct exclusions. Source snapshot remains {escape(stats["source_snapshot_status"])}. Frozen artifact hashes and raw evidence were verified before analysis. Successful report generation does not pass the data gate.</p>
<p><a download="statistics.json" href="data:application/json;base64,{payload}">Export full statistics and source-row reconciliation</a>. SVG charts are standalone exports; this HTML also works when copied alone. With JavaScript disabled, all driver sections remain readable.</p>
<details><summary>Verified provenance and content hashes</summary><pre>{escape(json.dumps(stats["provenance"], indent=2, ensure_ascii=False))}</pre></details>
<footer>Source: <a href="https://openf1.org/">OpenF1</a>, retained historical evidence; <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">source-use terms</a>. No live requests, fitted model or calibrated arena. {VERSION}.</footer>
</main><script>document.body.classList.add('js');const choice=document.getElementById('driver');function show(){{document.querySelectorAll('.driver').forEach(p=>{{p.hidden=choice.value!=='all'&&p.id!==choice.value;}});}}choice.addEventListener('change',show);show();</script></body></html>"""
    return html.encode(), exports


def generate(snapshot: Path, cohort: Path, pin: Path, output: Path):
    snapshot, cohort, output = snapshot.resolve(), cohort.resolve(), output.resolve()
    for source in (snapshot, cohort):
        require(
            output != source and source not in output.parents and output not in source.parents,
            "output must be separate from input evidence",
        )
    if output.exists():
        raise FileExistsError(output)
    tables, members, excluded, audit, provenance = verified_inputs(snapshot, cohort, pin)
    stats = statistics(tables, members, excluded, audit, provenance)
    html, charts = render(stats)
    artifacts = {"statistics.json": canonical(stats), "report.html": html, **charts}
    output.mkdir(parents=True, exist_ok=False)
    build = {
        "version": VERSION,
        "status": "building",
        "provenance": provenance,
        "source_status": stats["source_snapshot_status"],
        "full_circuit_gate": "blocked",
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_bytes(canonical(build))
    try:
        for name, body in artifacts.items():
            (output / name).write_bytes(body)
        build.update(status="complete", artifacts={n: digest(b) for n, b in artifacts.items()})
    except OSError:
        build["status"] = "failed"
        raise
    finally:
        manifest_path.write_bytes(canonical(build))
    return stats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        stats = generate(args.snapshot, args.cohort, args.config, args.output)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(f"Descriptive report failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "report": str(args.output / "report.html"),
                **stats["reconciliation"],
                "source_status": stats["source_snapshot_status"],
                "full_circuit_gate": "blocked",
            }
        )
    )
    # This frozen workstream retains a partial source and a blocked full gate.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
