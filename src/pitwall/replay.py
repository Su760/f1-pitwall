"""Execute saved actions and verify every version-1 trace field against the engine."""

from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pitwall.actions import Action, Compound
from pitwall.config import RaceConfig, fields
from pitwall.engine import InvalidAction, Race
from pitwall.policies import FixedSchedule, PitStop
from pitwall.results import ActionRecord
from pitwall.serialization import (
    MODEL_VERSION,
    json_value,
    load_document,
    validate_json,
    verify_equal,
)


def read_configuration(data: Any, expected_config: RaceConfig | None = None) -> RaceConfig:
    try:
        config = RaceConfig.from_dict(data)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"configuration: {exc}") from exc
    if expected_config is not None:
        verify_equal(data, expected_config.to_dict(), "configuration")
    return config


def policy_from_actions(name: str, actions: Iterable[ActionRecord]) -> FixedSchedule:
    """Describe a completed or partial run's actual pit actions without changing them."""
    return FixedSchedule(
        name,
        tuple(
            PitStop(record.after_lap, record.action.compound)
            for record in actions
            if record.action.compound is not None
        ),
    )


def trace_policy(data: Any) -> FixedSchedule:
    """Read strict schedule metadata; replay_document also checks it against actions."""
    strategy = data["strategy"]
    fields(strategy, {"name", "stops"}, "strategy")
    if type(strategy["stops"]) is not list:
        raise ValueError("strategy.stops: expected an array")
    stops = []
    for index, stop in enumerate(strategy["stops"]):
        fields(stop, {"after_lap", "compound"}, f"strategy.stops[{index}]")
        if type(stop["compound"]) is not str:
            raise ValueError(f"strategy.stops[{index}].compound: expected a string")
        try:
            compound = Compound(stop["compound"])
        except ValueError as exc:
            raise ValueError(f"strategy.stops[{index}].compound: unknown compound") from exc
        stops.append(PitStop(stop["after_lap"], compound))
    return FixedSchedule(strategy["name"], tuple(stops))


def replay_prefix(config: RaceConfig, actions: Any, laps: Any) -> Race:
    """Replay a validated sequence; state is created only by accepted engine actions."""
    if type(actions) is not list or len(actions) > config.laps:
        raise ValueError(f"actions: expected an array of at most {config.laps} items")
    if type(laps) is not list or len(laps) != len(actions):
        raise ValueError("laps: expected one recorded lap per action")
    race = Race(config)
    for index, record in enumerate(actions):
        path = f"actions[{index}]"
        fields(record, {"after_lap", "action"}, path)
        verify_equal(record["after_lap"], index, f"{path}.after_lap")
        if type(record["action"]) is not str:
            raise ValueError(f"{path}.action: expected an action string")
        try:
            action = Action(record["action"])
        except ValueError as exc:
            raise ValueError(f"{path}.action: unknown action {record['action']!r}") from exc
        try:
            lap = race.step(action)
        except InvalidAction as exc:
            raise ValueError(f"{path}: {exc}") from exc
        verify_equal(laps[index], json_value(asdict(lap)), f"laps[{index}]")
    return race


def result_summary(race: Race) -> dict[str, Any]:
    result = asdict(race.result())
    result.pop("actions")
    result.pop("laps")
    return json_value(result)


def replay_document(data: Any, *, expected_config: RaceConfig | None = None) -> Race:
    """Verify an entire v1 trace, including strategy metadata, and return its finished race."""
    validate_json(data)
    fields(
        data,
        {
            "trace_version",
            "model_version",
            "configuration",
            "strategy",
            "actions",
            "laps",
            "result",
        },
        "trace",
    )
    verify_equal(data["trace_version"], 1, "trace_version")
    verify_equal(data["model_version"], MODEL_VERSION, "model_version")
    config = read_configuration(data["configuration"], expected_config)
    policy = trace_policy(data)
    race = replay_prefix(config, data["actions"], data["laps"])
    if not race.finished:
        raise ValueError(f"actions: a complete trace requires exactly {config.laps} actions")
    actual_policy = policy_from_actions(policy.name, race.result().actions)
    verify_equal(data["strategy"], json_value(asdict(actual_policy)), "strategy")
    verify_equal(data["result"], result_summary(race), "result")
    return race


def load_trace(path: Path, *, expected_config: RaceConfig | None = None) -> Race:
    return replay_document(load_document(path), expected_config=expected_config)
