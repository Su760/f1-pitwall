"""Compare, optimize, and inspect deterministic races without changing policy observations."""

import argparse
import sys
from pathlib import Path

from pitwall.actions import Compound
from pitwall.engine import Race, simulate
from pitwall.optimizer import SearchLimits, optimize
from pitwall.policies import FixedSchedule, PitStop
from pitwall.replay import load_trace, policy_from_actions
from pitwall.results import RaceResult
from pitwall.scenario import load_scenario
from pitwall.snapshots import fork, load_snapshot, save_snapshot
from pitwall.trace import save_trace


def _check_output(output: Path, *inputs: Path | None) -> None:
    for source in inputs:
        if source is not None and (
            output.resolve() == source.resolve()
            or (output.exists() and source.exists() and output.samefile(source))
        ):
            raise ValueError(f"Output would overwrite input: {source}")


def _print_result(name: str, result: RaceResult) -> None:
    boundaries = ",".join(map(str, result.pit_boundaries)) or "none"
    stints = "; ".join(f"{s.compound.value} {s.first_lap}-{s.last_lap}" for s in result.stints)
    legality = "LEGAL" if result.legal else "ILLEGAL: " + "; ".join(result.legality_errors)
    print(f"{name} | {result.total_elapsed_s:.3f} | {boundaries} | {stints} | {legality}")


def _compare(args: argparse.Namespace) -> int:
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
    # Finish the whole comparison before publishing any result.
    for path, _, _ in completed:
        _check_output(path, args.scenario)
    for path, policy, result in completed:
        save_trace(path, scenario.configuration, policy, result)
    print(
        f"SYNTHETIC assumptions | {scenario.configuration.name} | "
        f"{scenario.configuration.laps} laps"
    )
    print("Strategy | Total elapsed (s) | Pit after laps | Tire stints | Legality")
    for _, policy, result in completed:
        _print_result(policy.name, result)
    for path, policy, _ in completed:
        print(f"Trace ({policy.name}): {path}")
    return 0 if all(result.legal for _, _, result in completed) else 1


def _optimize(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.scenario)
    _check_output(args.output, args.scenario)
    limits = SearchLimits(args.max_candidates, args.max_lap_evaluations)
    report = optimize(scenario.configuration, limits=limits, top_k=args.top)
    best = report.best
    save_trace(args.output, scenario.configuration, best.schedule, best.result)
    print(
        f"COMPLETE exhaustive search | {report.candidate_count} candidates; "
        f"{report.legal_count} legal | SYNTHETIC assumptions"
    )
    for stops, count in enumerate(report.legal_counts_by_stops):
        print(f"{stops} stops: {count} legal")
    print("Rank | Total elapsed (s) | Gap (s) | Pit after lap:compound")
    for rank, item in enumerate(report.ranked, start=1):
        stops = (
            ", ".join(f"{s.after_lap}:{s.compound.value}" for s in item.schedule.stops) or "none"
        )
        print(f"{rank} | {item.result.total_elapsed_s:.3f} | {item.gap_s:.3f} | {stops}")
    for policy in scenario.strategies:
        try:
            baseline = simulate(scenario.configuration, policy)
        except ValueError as exc:
            print(f"Baseline {policy.name}: invalid ({exc})")
            continue
        if baseline.legal:
            gain = baseline.total_elapsed_s - best.result.total_elapsed_s
            print(f"Baseline {policy.name}: {gain:.3f} s improvement")
    print(f"Best trace: {args.output}")
    return 0


def _expected_config(args: argparse.Namespace):
    return load_scenario(args.scenario).configuration if args.scenario is not None else None


def _replay(args: argparse.Namespace) -> int:
    race = load_trace(args.trace, expected_config=_expected_config(args))
    print(
        f"VERIFIED trace v1 | {race.state.completed_laps} laps | "
        f"{race.state.elapsed_s:.3f} s | LEGAL"
    )
    return 0


def _snapshot(args: argparse.Namespace) -> int:
    _check_output(args.output, args.trace, args.scenario)
    verified = load_trace(args.trace, expected_config=_expected_config(args))
    if not 0 <= args.after_lap <= verified.configuration.laps:
        raise ValueError("Snapshot boundary must be between reset (0) and the finish")
    race = Race(verified.configuration)
    for record in verified.result().actions[: args.after_lap]:
        race.step(record.action)
    save_snapshot(args.output, race)
    print(f"Snapshot v1 at boundary {race.state.completed_laps}: {args.output}")
    return 0


def _pit(value: str) -> PitStop:
    try:
        boundary, compound = value.split(":")
        return PitStop(int(boundary), Compound(compound))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            "Expected AFTER_LAP:soft|medium|hard, e.g. 6:medium"
        ) from exc


def _continue(args: argparse.Namespace) -> int:
    _check_output(args.output, args.snapshot, args.scenario)
    parent = load_snapshot(args.snapshot, expected_config=_expected_config(args))
    race = fork(parent) if args.command == "fork" else parent
    name = args.name or ("forked" if args.command == "fork" else "restored")
    continuation = FixedSchedule(name, tuple(args.pit))
    for stop in continuation.stops:
        if stop.after_lap < race.state.completed_laps:
            raise ValueError("Continuation cannot change a past pit boundary; fork earlier")
        if stop.after_lap >= race.configuration.laps:
            raise ValueError("Cannot schedule a pit at or after the finish")
    while not race.finished:
        race.step(continuation.choose_action(race.observe()))
    result = race.result()
    if not result.legal:
        raise ValueError("Continuation produced an illegal finish")
    policy = policy_from_actions(name, result.actions)
    save_trace(args.output, race.configuration, policy, result)
    if args.command == "fork":
        print(f"Parent unchanged at boundary {parent.state.completed_laps}")
    _print_result(name, result)
    print(f"New trace: {args.output}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PitWall Arena F0 — SYNTHETIC dry-race simulator")
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("compare", help="compare configured fixed schedules")
    compare.add_argument("scenario", type=Path)
    compare.add_argument("--strategy", help="run only this strategy name")
    compare.add_argument("--trace-dir", type=Path, default=Path("traces"))
    compare.set_defaults(handler=_compare)

    search = commands.add_parser("optimize", help="bounded exhaustive legal schedule search")
    search.add_argument("scenario", type=Path)
    search.add_argument("--top", type=int, default=5, help="number of ranked results to report")
    defaults = SearchLimits()
    search.add_argument("--max-candidates", type=int, default=defaults.max_candidates)
    search.add_argument("--max-lap-evaluations", type=int, default=defaults.max_lap_evaluations)
    search.add_argument("--output", type=Path, default=Path("traces/optimal.json"))
    search.set_defaults(handler=_optimize)

    replay = commands.add_parser("replay", help="verify a complete version-1 action trace")
    replay.add_argument("trace", type=Path)
    replay.add_argument("--scenario", type=Path, help="require this scenario configuration")
    replay.set_defaults(handler=_replay)

    snapshot = commands.add_parser("snapshot", help="save a boundary from a verified trace")
    snapshot.add_argument("trace", type=Path)
    snapshot.add_argument(
        "--after-lap", type=int, required=True, help="completed laps, including 0"
    )
    snapshot.add_argument("--scenario", type=Path, help="require this scenario configuration")
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.set_defaults(handler=_snapshot)

    for command in ("restore", "fork"):
        continuation = commands.add_parser(command, help=f"{command} a snapshot and run to finish")
        continuation.add_argument("snapshot", type=Path)
        continuation.add_argument(
            "--scenario", type=Path, help="require this scenario configuration"
        )
        continuation.add_argument(
            "--pit",
            type=_pit,
            action="append",
            default=[],
            metavar="AFTER_LAP:COMPOUND",
            help="remaining absolute pit boundaries, in increasing order; repeat for each stop",
        )
        continuation.add_argument("--name", help="name of the new complete trace")
        continuation.add_argument("--output", type=Path, required=True)
        continuation.set_defaults(handler=_continue)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    commands = {"compare", "optimize", "replay", "snapshot", "restore", "fork"}
    # Preserve `pitwall scenario.json [options]` as a comparison alias.
    if arguments and arguments[0] not in commands | {"-h", "--help"}:
        arguments.insert(0, "compare")
    parser = _parser()
    args = parser.parse_args(arguments)
    try:
        return args.handler(args)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        print("Interrupted; no completed result is being reported.", file=sys.stderr)
        return 130
    return 2
