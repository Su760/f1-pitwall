"""Immutable configuration. All physical/rule parameters are supplied by the scenario."""

import math
from dataclasses import asdict, dataclass
from typing import Any

from pitwall.actions import Compound


def integer(value: object, name: str, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def seconds(value: object, name: str, *, signed: bool = False) -> None:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (not signed and value < 0):
        raise ValueError(f"{name} must be finite {'signed' if signed else 'nonnegative'} seconds")


def fields(data: Any, expected: set[str], name: str) -> None:
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError(f"{name} must be an object with exactly these fields: {sorted(expected)}")


@dataclass(frozen=True)
class Rules:
    max_pit_stops: int
    min_distinct_compounds: int

    def __post_init__(self) -> None:
        integer(self.max_pit_stops, "max_pit_stops")
        integer(self.min_distinct_compounds, "min_distinct_compounds", 1)
        if self.min_distinct_compounds > len(Compound):
            raise ValueError("Cannot require more than three compounds")


@dataclass(frozen=True)
class TireParameters:
    compound: Compound
    pace_offset_s: float
    degradation_s_per_lap: float
    degradation_cap_s: float
    warmup_s: tuple[float, ...]
    fresh_sets: int

    def __post_init__(self) -> None:
        if not isinstance(self.compound, Compound):
            raise ValueError("compound must be a Compound")
        seconds(self.pace_offset_s, "pace_offset_s", signed=True)
        seconds(self.degradation_s_per_lap, "degradation_s_per_lap")
        seconds(self.degradation_cap_s, "degradation_cap_s")
        if not isinstance(self.warmup_s, tuple):
            raise ValueError("warmup_s must be an immutable tuple of age-indexed costs")
        for cost in self.warmup_s:
            seconds(cost, "warmup_s entry")
        integer(self.fresh_sets, "fresh_sets")


@dataclass(frozen=True)
class RaceConfig:
    name: str
    laps: int
    base_lap_time_s: float
    pit_loss_s: float
    start_compound: Compound
    tires: tuple[TireParameters, ...]
    rules: Rules

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be nonempty")
        integer(self.laps, "laps", 1)
        seconds(self.base_lap_time_s, "base_lap_time_s")
        seconds(self.pit_loss_s, "pit_loss_s")
        if self.base_lap_time_s <= 0:
            raise ValueError("base_lap_time_s must be positive")
        if not isinstance(self.start_compound, Compound) or not isinstance(self.rules, Rules):
            raise ValueError("start_compound and rules must be typed configuration values")
        if (
            not isinstance(self.tires, tuple)
            or len(self.tires) != len(Compound)
            or any(not isinstance(tire, TireParameters) for tire in self.tires)
            or tuple(t.compound for t in self.tires) != tuple(Compound)
        ):
            raise ValueError("tires must contain soft, medium, hard exactly once, in that order")
        for tire in self.tires:
            if self.base_lap_time_s + tire.pace_offset_s <= 0:
                raise ValueError("base pace plus compound offset must be positive")
            try:
                upper_bound = (
                    self.base_lap_time_s
                    + tire.pace_offset_s
                    + tire.degradation_cap_s
                    + max(tire.warmup_s, default=0)
                    + self.pit_loss_s
                ) * self.laps
                seconds(upper_bound, "maximum race time")
            except OverflowError as exc:
                raise ValueError("Race time exceeds finite numeric range") from exc
        if self.tire(self.start_compound).fresh_sets == 0:
            raise ValueError("Starting compound has no fresh sets")
        possible = min(
            sum(t.fresh_sets > 0 for t in self.tires),
            self.laps,
            self.rules.max_pit_stops + 1,
        )
        if possible < self.rules.min_distinct_compounds:
            raise ValueError("No legal finish is possible with these laps, inventory, and rules")

    def tire(self, compound: Compound) -> TireParameters:
        return self.tires[tuple(Compound).index(compound)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "laps": self.laps,
            "base_lap_time_s": self.base_lap_time_s,
            "pit_loss_s": self.pit_loss_s,
            "start_compound": self.start_compound.value,
            "rules": asdict(self.rules),
            "tires": {
                t.compound.value: {
                    "pace_offset_s": t.pace_offset_s,
                    "degradation_s_per_lap": t.degradation_s_per_lap,
                    "degradation_cap_s": t.degradation_cap_s,
                    "warmup_s": list(t.warmup_s),
                    "fresh_sets": t.fresh_sets,
                }
                for t in self.tires
            },
        }

    @classmethod
    def from_dict(cls, data: Any) -> "RaceConfig":
        fields(
            data,
            {"name", "laps", "base_lap_time_s", "pit_loss_s", "start_compound", "rules", "tires"},
            "config",
        )
        fields(data["rules"], {"max_pit_stops", "min_distinct_compounds"}, "rules")
        fields(data["tires"], {c.value for c in Compound}, "tires")
        tires = []
        for compound in Compound:
            spec = data["tires"][compound.value]
            fields(
                spec,
                {
                    "pace_offset_s",
                    "degradation_s_per_lap",
                    "degradation_cap_s",
                    "warmup_s",
                    "fresh_sets",
                },
                f"tires.{compound.value}",
            )
            if not isinstance(spec["warmup_s"], list):
                raise ValueError("warmup_s must be an array")
            tires.append(
                TireParameters(
                    compound=compound,
                    **{**spec, "warmup_s": tuple(spec["warmup_s"])},
                )
            )
        return cls(
            name=data["name"],
            laps=data["laps"],
            base_lap_time_s=data["base_lap_time_s"],
            pit_loss_s=data["pit_loss_s"],
            start_compound=Compound(data["start_compound"]),
            tires=tuple(tires),
            rules=Rules(**data["rules"]),
        )
