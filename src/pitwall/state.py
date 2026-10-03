"""Engine-owned immutable state; tire age is completed laps on the fitted set."""

from dataclasses import dataclass

from pitwall.actions import Compound


@dataclass(frozen=True)
class RaceState:
    completed_laps: int
    current_compound: Compound
    tire_age_laps: int
    remaining_sets: tuple[int, ...]
    used_compounds: frozenset[Compound]
    pit_boundaries: tuple[int, ...]
    elapsed_s: float
