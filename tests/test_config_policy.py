from dataclasses import replace

import pytest
from conftest import make_config

from pitwall.actions import Action, Compound
from pitwall.config import RaceConfig, Rules
from pitwall.engine import Race, simulate
from pitwall.policies import FixedSchedule, PitStop


@pytest.mark.parametrize(
    "changes",
    [
        {"laps": 0},
        {"laps": -1},
        {"laps": True},
        {"laps": 2.5},
        {"base_lap_time_s": 0},
        {"pit_loss_s": -1},
        {"pit_loss_s": float("nan")},
        {"pit_loss_s": float("inf")},
        {"base_lap_time_s": 1e308},
        {"start_compound": "soft"},
        {"name": ""},
    ],
)
def test_nonsensical_race_parameters_rejected(changes):
    with pytest.raises(ValueError):
        replace(make_config(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"degradation_s_per_lap": -1},
        {"degradation_cap_s": -1},
        {"warmup_s": (-1,)},
        {"warmup_s": (float("inf"),)},
        {"fresh_sets": -1},
        {"fresh_sets": True},
        {"pace_offset_s": float("nan")},
    ],
)
def test_nonsensical_tire_parameters_rejected(changes):
    with pytest.raises(ValueError):
        replace(make_config().tires[0], **changes)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"laps": 1},
        {"max_stops": 0},
        {"sets": (2, 0, 0)},
        {"sets": (0, 2, 2)},
        {"laps": 2, "min_compounds": 3},
        {"max_stops": 1, "min_compounds": 3},
    ],
)
def test_impossible_configurations_rejected(kwargs):
    with pytest.raises(ValueError):
        make_config(**kwargs)


@pytest.mark.parametrize("args", [(-1, 2), (2, 0), (2, 4), (True, 2), (2, 1.5)])
def test_invalid_rules_rejected(args):
    with pytest.raises(ValueError):
        Rules(*args)


def test_nonpositive_lap_time_and_duplicate_compounds_rejected():
    config = make_config()
    with pytest.raises(ValueError):
        replace(config, tires=(replace(config.tires[0], pace_offset_s=-100), *config.tires[1:]))
    with pytest.raises(ValueError):
        replace(config, tires=(config.tires[0], config.tires[0], config.tires[2]))


def test_json_config_roundtrip_and_strict_fields():
    config = make_config()
    assert RaceConfig.from_dict(config.to_dict()) == config
    invalid = config.to_dict()
    invalid["pit_loss_ms"] = invalid.pop("pit_loss_s")
    with pytest.raises(ValueError):
        RaceConfig.from_dict(invalid)


def test_fixed_policy_uses_observation_action_interface():
    race = Race(make_config())
    policy = FixedSchedule("one-stop", (PitStop(1, Compound.HARD),))
    assert policy.choose_action(race.observe()) == Action.STAY_OUT
    race.step(Action.STAY_OUT)
    assert policy.choose_action(race.observe()) == Action.PIT_HARD


@pytest.mark.parametrize(
    "stops",
    [
        (PitStop(0, Compound.MEDIUM),),
        (PitStop(6, Compound.MEDIUM),),
        (PitStop(7, Compound.MEDIUM),),
        (PitStop(2, Compound.MEDIUM), PitStop(2, Compound.HARD)),
        (PitStop(4, Compound.MEDIUM), PitStop(2, Compound.HARD)),
        (PitStop(1, Compound.MEDIUM), PitStop(2, Compound.HARD), PitStop(3, Compound.SOFT)),
    ],
)
def test_bad_fixed_schedules_rejected(stops):
    with pytest.raises(ValueError):
        simulate(make_config(), FixedSchedule("bad", stops))


def test_illegal_fixed_strategy_is_rejected_not_silently_repaired():
    with pytest.raises(ValueError):
        simulate(make_config(), FixedSchedule("never changes", ()))


def test_custom_policy_only_needs_choose_action():
    class LastChancePolicy:
        def choose_action(self, observation):
            if observation.allows(Action.STAY_OUT):
                return Action.STAY_OUT
            return Action.PIT_HARD

    result = simulate(make_config(laps=3), LastChancePolicy())
    assert result.pit_boundaries == (2,)
    assert result.total_elapsed_s == 310
    assert result.legal
