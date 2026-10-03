"""Policy-facing values, separate from engine state and its transition machinery."""

from dataclasses import dataclass

from pitwall.actions import Action, Compound


@dataclass(frozen=True)
class Observation:
    completed_laps: int
    total_laps: int
    current_compound: Compound
    tire_age_laps: int
    remaining_sets: tuple[int, ...]
    used_compounds: frozenset[Compound]
    stops_remaining: int
    elapsed_s: float
    action_mask: tuple[bool, ...]

    def allows(self, action: Action) -> bool:
        return isinstance(action, Action) and self.action_mask[tuple(Action).index(action)]
