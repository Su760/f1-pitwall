"""Immutable action, lap, stint, and race outputs. All time fields are seconds."""

from dataclasses import dataclass

from pitwall.actions import Action, Compound


@dataclass(frozen=True)
class ActionRecord:
    after_lap: int
    action: Action


@dataclass(frozen=True)
class LapResult:
    lap: int
    compound: Compound
    tire_age_laps: int
    base_lap_time_s: float
    pace_offset_s: float
    degradation_s: float
    warmup_s: float
    pit_loss_s: float
    lap_time_s: float
    elapsed_s: float


@dataclass(frozen=True)
class Stint:
    compound: Compound
    first_lap: int
    last_lap: int


@dataclass(frozen=True)
class RaceResult:
    total_elapsed_s: float
    completed_laps: int
    pit_boundaries: tuple[int, ...]
    stints: tuple[Stint, ...]
    legal: bool
    legality_errors: tuple[str, ...]
    actions: tuple[ActionRecord, ...]
    laps: tuple[LapResult, ...]
