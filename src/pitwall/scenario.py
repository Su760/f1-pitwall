"""Strict versioned JSON scenario input; no hidden defaults or parameter calibration."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pitwall.actions import Compound
from pitwall.config import RaceConfig, fields
from pitwall.policies import FixedSchedule, PitStop


@dataclass(frozen=True)
class Scenario:
    configuration: RaceConfig
    strategies: tuple[FixedSchedule, ...]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Nonfinite JSON number: {value}")


def load_scenario(path: Path) -> Scenario:
    data = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
    fields(data, {"scenario_version", "configuration", "strategies"}, "scenario")
    if type(data["scenario_version"]) is not int or data["scenario_version"] != 1:
        raise ValueError("Only scenario_version 1 is supported")
    config = RaceConfig.from_dict(data["configuration"])
    if not isinstance(data["strategies"], list) or not data["strategies"]:
        raise ValueError("strategies must be a nonempty array")
    strategies = []
    for strategy in data["strategies"]:
        fields(strategy, {"name", "stops"}, "strategy")
        if not isinstance(strategy["stops"], list):
            raise ValueError("stops must be an array")
        stops = []
        for stop in strategy["stops"]:
            fields(stop, {"after_lap", "compound"}, "stop")
            stops.append(PitStop(stop["after_lap"], Compound(stop["compound"])))
        strategies.append(FixedSchedule(strategy["name"], tuple(stops)))
    if len({s.name for s in strategies}) != len(strategies):
        raise ValueError("Strategy names must be unique")
    return Scenario(config, tuple(strategies))
