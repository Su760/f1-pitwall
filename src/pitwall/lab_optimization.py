"""Explicit bounded synthetic lab search; engine/optimizer formats stay unchanged."""

import hashlib
from dataclasses import asdict
from pathlib import Path

from pitwall.optimizer import SearchLimits, optimize
from pitwall.sensitivity import (
    comparison,
    load_lab,
    resolve,
    scenario_document,
    validate_controls,
)
from pitwall.serialization import json_value, load_document
from pitwall.trace import trace_document


def load_search_settings(path: Path) -> dict:
    settings = load_document(path)
    if (
        set(settings) != {"optimization_version", "top_k", "max_candidates", "max_lap_evaluations"}
        or type(settings["optimization_version"]) is not int
        or settings["optimization_version"] != 1
        or type(settings["top_k"]) is not int
        or settings["top_k"] != 3
    ):
        raise ValueError("Unsupported lab search settings")
    SearchLimits(settings["max_candidates"], settings["max_lap_evaluations"])
    return settings


def optimize_lab(settings_path: Path, search_path: Path, controls: dict) -> dict:
    settings, base, identity = load_lab(settings_path)
    validate_controls(controls, settings)
    search_settings = load_search_settings(search_path)
    limits = SearchLimits(search_settings["max_candidates"], search_settings["max_lap_evaluations"])
    scenario = resolve(base, controls)
    # Preflight runs before any search or benchmark simulation. No partial winner.
    search = optimize(scenario.configuration, limits=limits, top_k=search_settings["top_k"])
    if not search.search_complete or not search.ranked or not search.best.result.legal:
        raise RuntimeError("No complete legal search result")
    best = search.best
    benchmarks = comparison(scenario, settings)["strategies"]
    return json_value(
        {
            "api_version": 1,
            "optimization_version": search_settings["optimization_version"],
            "controls": dict(controls),
            "source": {
                **identity,
                "optimization_settings_sha256": hashlib.sha256(
                    search_path.read_bytes()
                ).hexdigest(),
            },
            "label": "Best legal fixed schedule under these synthetic assumptions.",
            "search": {
                "search_complete": search.search_complete,
                "candidate_count": search.candidate_count,
                "legal_count": search.legal_count,
                "candidate_counts_by_stops": search.candidate_counts_by_stops,
                "legal_counts_by_stops": search.legal_counts_by_stops,
                "max_lap_evaluations_required": search.max_lap_evaluations_required,
                "benchmark_lap_evaluations": len(benchmarks) * scenario.configuration.laps,
                "limits": asdict(limits),
                "top_k": search_settings["top_k"],
                "scope": "All fixed schedules for the resolved start, inventory and rules",
                "tie_break": (
                    "Full-precision elapsed time; exact ties: fewer stops, increasing "
                    "boundary tuple, compound order soft/medium/hard"
                ),
                "ranked": [
                    {
                        "schedule": asdict(entry.schedule),
                        "total_elapsed_s": entry.result.total_elapsed_s,
                        "gap_s": entry.gap_s,
                    }
                    for entry in search.ranked
                ],
            },
            "best": {
                "schedule": asdict(best.schedule),
                "total_elapsed_s": best.result.total_elapsed_s,
                "legal": best.result.legal,
                "stints": [asdict(stint) for stint in best.result.stints],
                "pit_boundaries": best.result.pit_boundaries,
            },
            "benchmarks": [
                {
                    "name": outcome["name"],
                    "total_elapsed_s": outcome["total_elapsed_s"],
                    "improvement_s": outcome["total_elapsed_s"] - best.result.total_elapsed_s,
                }
                for outcome in benchmarks
            ],
            "scenario": scenario_document(scenario),
            "trace": trace_document(scenario.configuration, best.schedule, best.result),
        }
    )
