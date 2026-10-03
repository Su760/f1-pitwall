"""Run configured fixed strategies and print a small, auditable comparison."""

import argparse
from pathlib import Path

from pitwall.engine import simulate
from pitwall.scenario import load_scenario
from pitwall.trace import save_trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PitWall Arena F0a — SYNTHETIC dry-race simulator")
    parser.add_argument("scenario", type=Path, help="version 1 scenario JSON")
    parser.add_argument("--strategy", help="run only this strategy name (default: compare all)")
    parser.add_argument("--trace-dir", type=Path, default=Path("traces"), help="trace directory")
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        selected = [
            (index, policy)
            for index, policy in enumerate(scenario.strategies, start=1)
            if args.strategy is None or policy.name == args.strategy
        ]
        if not selected:
            raise ValueError(f"Unknown strategy: {args.strategy}")
        completed = []
        for index, policy in selected:
            try:
                result = simulate(scenario.configuration, policy)
            except ValueError as exc:
                raise ValueError(f"Strategy {policy.name!r}: {exc}") from exc
            completed.append((args.trace_dir / f"{index:02d}.json", policy, result))
        # Complete/validate the whole comparison before writing or printing any results.
        for path, _, _ in completed:
            if path.resolve() == args.scenario.resolve():
                raise ValueError("Trace path would overwrite the input scenario")
        for path, policy, result in completed:
            save_trace(path, scenario.configuration, policy, result)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    print(
        f"SYNTHETIC assumptions | {scenario.configuration.name} | "
        f"{scenario.configuration.laps} laps"
    )
    print("Strategy | Total elapsed (s) | Pit after laps | Tire stints | Legality")
    for _, policy, result in completed:
        boundaries = ",".join(map(str, result.pit_boundaries)) or "none"
        stints = "; ".join(f"{s.compound.value} {s.first_lap}-{s.last_lap}" for s in result.stints)
        legality = "LEGAL" if result.legal else "ILLEGAL: " + "; ".join(result.legality_errors)
        print(
            f"{policy.name} | {result.total_elapsed_s:.3f} | {boundaries} | {stints} | {legality}"
        )
    for path, policy, _ in completed:
        print(f"Trace ({policy.name}): {path}")
    return 0 if all(result.legal for _, _, result in completed) else 1
