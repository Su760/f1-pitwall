"""Bounded, synthetic two-schedule comparisons. No optimizer or historical input."""

import argparse
import hashlib
import math
import sys
from dataclasses import asdict, replace
from pathlib import Path

from pitwall.engine import simulate
from pitwall.scenario import Scenario, load_scenario
from pitwall.serialization import (
    MODEL_VERSION,
    json_value,
    load_document,
    verify_equal,
    write_document,
)


def load_lab(settings_path: Path) -> tuple[dict, Scenario, dict]:
    settings = load_document(settings_path)
    source_path = settings_path.parent / settings["scenario_file"]
    scenario = load_scenario(source_path)
    if (
        settings["lab_version"] != 1
        or not 2 <= settings["grid_max"] <= 21
        or scenario.configuration.laps > settings["max_laps"]
        or [s.name for s in scenario.strategies] != ["one-stop", "two-stop"]
    ):
        raise ValueError("Unsupported or unbounded lab configuration")
    identity = {
        "model_version": MODEL_VERSION,
        "scenario_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "settings_sha256": hashlib.sha256(settings_path.read_bytes()).hexdigest(),
    }
    return settings, scenario, identity


def validate_controls(controls: dict, settings: dict) -> None:
    if type(controls) is not dict or set(controls) != set(settings["controls"]):
        raise ValueError("Expected exactly the three lab controls")
    for name, bounds in settings["controls"].items():
        value = controls[name]
        if (
            type(value) not in (int, float)
            or not bounds["min"] <= value <= bounds["max"]
            or not math.isfinite(value)
        ):
            raise ValueError(f"{name} must be finite and within its illustrative range")


def resolve(base: Scenario, controls: dict) -> Scenario:
    """Scale slope AND cap and every warm-up entry, without modifying the baseline."""
    config = base.configuration
    tires = tuple(
        replace(
            tire,
            degradation_s_per_lap=tire.degradation_s_per_lap * controls["degradation_multiplier"],
            degradation_cap_s=tire.degradation_cap_s * controls["degradation_multiplier"],
            warmup_s=tuple(w * controls["warmup_multiplier"] for w in tire.warmup_s),
        )
        for tire in config.tires
    )
    return Scenario(
        replace(config, pit_loss_s=controls["pit_loss_s"], tires=tires), base.strategies
    )


def classification(delta: float, settings: dict) -> dict:
    if abs(delta) <= settings["tie_tolerance_s"]:
        return {"winner": "tie", "label": "Numerical tie", "symbol": "=", "near_tie": False}
    winner = "one-stop" if delta > 0 else "two-stop"
    near = abs(delta) < settings["near_tie_s"]
    return {
        "winner": winner,
        "label": f"{winner} faster among these two schedules" + (" (near-tie)" if near else ""),
        "symbol": "1" if delta > 0 else "2",
        "near_tie": near,
    }


def comparison(scenario: Scenario, settings: dict) -> dict:
    if [s.name for s in scenario.strategies] != ["one-stop", "two-stop"]:
        raise ValueError("Expected fixed one-stop and two-stop schedules in that order")
    outcomes = []
    for schedule in scenario.strategies:
        result = simulate(scenario.configuration, schedule)
        if not result.legal:
            raise ValueError(f"Illegal fixed strategy: {schedule.name}")
        components = {
            name: math.fsum(getattr(lap, field) for lap in result.laps)
            for name, field in {
                "base_s": "base_lap_time_s",
                "pace_s": "pace_offset_s",
                "pit_s": "pit_loss_s",
                "degradation_s": "degradation_s",
                "warmup_s": "warmup_s",
            }.items()
        }
        outcomes.append(
            json_value(
                {
                    "name": schedule.name,
                    "total_elapsed_s": result.total_elapsed_s,
                    "legal": result.legal,
                    "pit_count": len(result.pit_boundaries),
                    "pit_boundaries": result.pit_boundaries,
                    "stints": [asdict(s) for s in result.stints],
                    "components": components,
                    "laps": [asdict(lap) for lap in result.laps],
                }
            )
        )
    delta = outcomes[1]["total_elapsed_s"] - outcomes[0]["total_elapsed_s"]
    return {
        "strategies": outcomes,
        "delta_s": delta,
        "sign_convention": "two-stop minus one-stop; positive means one-stop faster",
        **classification(delta, settings),
    }


def scenario_document(scenario: Scenario) -> dict:
    return json_value(
        {
            "scenario_version": 1,
            "configuration": scenario.configuration.to_dict(),
            "strategies": [asdict(s) for s in scenario.strategies],
        }
    )


def evaluate_lab(settings_path: Path, controls: dict, grid_size: int) -> dict:
    settings, base, identity = load_lab(settings_path)
    validate_controls(controls, settings)
    if type(grid_size) is not int or not 2 <= grid_size <= settings["grid_max"]:
        raise ValueError("grid_size must be an integer from 2 to 21")
    lap_work = (grid_size**2 + 1) * len(base.strategies) * base.configuration.laps
    if lap_work > settings["max_lap_evaluations"]:
        raise ValueError("Requested grid exceeds the lap evaluation budget")
    selected = resolve(base, controls)
    axes = {}
    for name in ("pit_loss_s", "degradation_multiplier"):
        bounds = settings["controls"][name]
        axes[name] = [
            bounds["min"] + (bounds["max"] - bounds["min"]) * i / (grid_size - 1)
            for i in range(grid_size)
        ]
    points = []
    for degradation in axes["degradation_multiplier"]:
        row = []
        for pit in axes["pit_loss_s"]:
            sample = {**controls, "pit_loss_s": pit, "degradation_multiplier": degradation}
            compared = comparison(resolve(base, sample), settings)
            row.append(
                {
                    "pit_loss_s": pit,
                    "degradation_multiplier": degradation,
                    "warmup_multiplier": controls["warmup_multiplier"],
                    **{
                        k: compared[k] for k in ("delta_s", "winner", "label", "symbol", "near_tie")
                    },
                    "one_stop_s": compared["strategies"][0]["total_elapsed_s"],
                    "two_stop_s": compared["strategies"][1]["total_elapsed_s"],
                }
            )
        points.append(row)
    return {
        "api_version": 1,
        "lab_version": 1,
        "source": identity,
        "controls": controls,
        "assumptions": "Illustrative synthetic parameters; not historical calibration",
        "tie_tolerance_s": settings["tie_tolerance_s"],
        "near_tie_s": settings["near_tie_s"],
        "scenario": scenario_document(selected),
        "comparison": comparison(selected, settings),
        "grid": {
            "size": grid_size,
            "axes": axes,
            "rows": points,
            "lap_evaluations": lap_work,
            "interpretation": (
                "Sampled points only; not exact crossovers, probabilities or confidence"
            ),
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--scenario", type=Path, help="Recompute an exported scenario comparison")
    source.add_argument("--record", type=Path, help="Verify a full exported lab result record")
    parser.add_argument("--settings", type=Path, default=Path("scenarios/sensitivity-lab.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        for path in (args.scenario, args.record, args.settings):
            if path and args.output.resolve() == path.resolve():
                raise ValueError("Output must not overwrite an input")
        settings, _, _ = load_lab(args.settings)
        if args.record:
            saved = load_document(args.record)
            result = evaluate_lab(args.settings, saved["controls"], saved["grid"]["size"])
            verify_equal(saved, result, "lab_record")
        else:
            scenario = load_scenario(args.scenario)
            if scenario.configuration.laps > settings["max_laps"]:
                raise ValueError("Scenario exceeds lab lap limit")
            result = comparison(scenario, settings)
        write_document(args.output, result)
        print(f"Recomputed synthetic comparison: {args.output}")
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(f"Lab recomputation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
