"""Fixed schedules use exactly the same observation/action interface as any policy."""

from dataclasses import dataclass
from typing import Protocol

from pitwall.actions import Action, Compound
from pitwall.config import integer
from pitwall.observations import Observation


class Policy(Protocol):
    def choose_action(self, observation: Observation) -> Action: ...


@dataclass(frozen=True)
class PitStop:
    after_lap: int
    compound: Compound


@dataclass(frozen=True)
class FixedSchedule:
    name: str
    stops: tuple[PitStop, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Schedule name must be nonempty")
        if not isinstance(self.stops, tuple):
            raise ValueError("stops must be an immutable tuple")
        previous = 0
        for stop in self.stops:
            if not isinstance(stop, PitStop) or not isinstance(stop.compound, Compound):
                raise ValueError("Schedule must contain typed PitStop values")
            integer(stop.after_lap, "after_lap", 1)
            if stop.after_lap <= previous:
                raise ValueError("Pit boundaries must be strictly increasing")
            previous = stop.after_lap

    def choose_action(self, observation: Observation) -> Action:
        if self.stops and self.stops[-1].after_lap >= observation.total_laps:
            raise ValueError("Cannot schedule a pit at or after the finish")
        if observation.completed_laps == 0 and len(self.stops) > observation.stops_remaining:
            raise ValueError("Schedule exceeds the pit stop limit")
        for stop in self.stops:
            if stop.after_lap == observation.completed_laps:
                return Action.pit(stop.compound)
        return Action.STAY_OUT
