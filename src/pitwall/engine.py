"""Deterministic lap transitions, independent of files, the CLI, and randomness."""

from dataclasses import replace

from pitwall.actions import Action, Compound
from pitwall.config import RaceConfig
from pitwall.observations import Observation
from pitwall.policies import Policy
from pitwall.results import ActionRecord, LapResult, RaceResult, Stint
from pitwall.state import RaceState


class InvalidAction(ValueError):
    """An action was rejected before any state or trace mutation."""


def check_finish(config: RaceConfig, state: RaceState) -> tuple[str, ...]:
    """Retain an independent terminal rule check even though the mask prevents dead ends."""
    errors = []
    if state.completed_laps != config.laps:
        errors.append("Race is not finished")
    if len(state.used_compounds) < config.rules.min_distinct_compounds:
        errors.append(f"At least {config.rules.min_distinct_compounds} distinct compounds required")
    if len(state.pit_boundaries) > config.rules.max_pit_stops:
        errors.append("Pit stop limit exceeded")
    if (
        any(not 1 <= lap < config.laps for lap in state.pit_boundaries)
        or tuple(sorted(set(state.pit_boundaries))) != state.pit_boundaries
    ):
        errors.append("Invalid pit boundaries")
    if len(state.remaining_sets) != len(config.tires) or any(
        not 0 <= count <= tire.fresh_sets
        for count, tire in zip(state.remaining_sets, config.tires, strict=True)
    ):
        errors.append("Invalid tire inventory")
    elif sum(t.fresh_sets for t in config.tires) - sum(state.remaining_sets) != (
        1 + len(state.pit_boundaries)
    ):
        errors.append("Tire consumption does not match fittings")
    return tuple(errors)


class Race:
    def __init__(self, config: RaceConfig):
        self._config = config
        inventory = tuple(
            t.fresh_sets - int(t.compound == config.start_compound) for t in config.tires
        )
        self._state = RaceState(0, config.start_compound, 0, inventory, frozenset(), (), 0.0)
        self._laps: list[LapResult] = []
        self._actions: list[ActionRecord] = []

    @property
    def state(self) -> RaceState:
        return self._state

    @property
    def finished(self) -> bool:
        return self._state.completed_laps == self._config.laps

    def _allowed(self, action: Action) -> bool:
        state, config = self._state, self._config
        if self.finished:
            return False
        compound = action.compound or state.current_compound
        inventory = list(state.remaining_sets)
        stops = len(state.pit_boundaries)
        if action is not Action.STAY_OUT:
            index = tuple(Compound).index(compound)
            if (
                state.completed_laps == 0
                or stops >= config.rules.max_pit_stops
                or inventory[index] == 0
            ):
                return False
            inventory[index] -= 1
            stops += 1
        used = state.used_compounds | {compound}
        missing = max(0, config.rules.min_distinct_compounds - len(used))
        # Each missing compound needs a fresh set, a stop, and a future lap.
        available_new = sum(
            count > 0 and c not in used for c, count in zip(Compound, inventory, strict=True)
        )
        future_boundaries = config.laps - state.completed_laps - 1
        return missing <= min(available_new, config.rules.max_pit_stops - stops, future_boundaries)

    def observe(self) -> Observation:
        state = self._state
        return Observation(
            state.completed_laps,
            self._config.laps,
            state.current_compound,
            state.tire_age_laps,
            state.remaining_sets,
            state.used_compounds,
            self._config.rules.max_pit_stops - len(state.pit_boundaries),
            state.elapsed_s,
            tuple(self._allowed(action) for action in Action),
        )

    def step(self, action: Action) -> LapResult:
        if not isinstance(action, Action) or not self._allowed(action):
            raise InvalidAction(
                f"Action {action!r} is not allowed after lap {self._state.completed_laps}"
            )
        state, config = self._state, self._config
        pitting = action is not Action.STAY_OUT
        compound = action.compound or state.current_compound
        age = 0 if pitting else state.tire_age_laps
        inventory = list(state.remaining_sets)
        boundaries = state.pit_boundaries
        if pitting:
            inventory[tuple(Compound).index(compound)] -= 1
            boundaries += (state.completed_laps,)
        tire = config.tire(compound)
        degradation = min(tire.degradation_cap_s, tire.degradation_s_per_lap * age)
        warmup = tire.warmup_s[age] if age < len(tire.warmup_s) else 0.0
        pit_loss = config.pit_loss_s if pitting else 0.0
        lap_time = config.base_lap_time_s + tire.pace_offset_s + degradation + warmup + pit_loss
        elapsed = state.elapsed_s + lap_time
        lap = LapResult(
            state.completed_laps + 1,
            compound,
            age,
            config.base_lap_time_s,
            tire.pace_offset_s,
            degradation,
            warmup,
            pit_loss,
            lap_time,
            elapsed,
        )
        next_state = RaceState(
            lap.lap,
            compound,
            age + 1,
            tuple(inventory),
            state.used_compounds | {compound},
            boundaries,
            elapsed,
        )
        self._state = next_state
        self._laps.append(lap)
        self._actions.append(ActionRecord(state.completed_laps, action))
        return lap

    def result(self) -> RaceResult:
        stints: list[Stint] = []
        for lap in self._laps:
            if lap.tire_age_laps == 0:
                stints.append(Stint(lap.compound, lap.lap, lap.lap))
            else:
                stints[-1] = replace(stints[-1], last_lap=lap.lap)
        errors = check_finish(self._config, self._state)
        return RaceResult(
            self._state.elapsed_s,
            self._state.completed_laps,
            self._state.pit_boundaries,
            tuple(stints),
            not errors,
            errors,
            tuple(self._actions),
            tuple(self._laps),
        )


def simulate(config: RaceConfig, policy: Policy) -> RaceResult:
    race = Race(config)
    while not race.finished:
        race.step(policy.choose_action(race.observe()))
    return race.result()
