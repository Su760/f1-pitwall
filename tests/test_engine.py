from dataclasses import FrozenInstanceError, replace

import pytest
from conftest import make_config

from pitwall.actions import Action, Compound
from pitwall.engine import InvalidAction, Race, check_finish, simulate
from pitwall.policies import FixedSchedule, PitStop


def schedule(*stops):
    return FixedSchedule("test", tuple(PitStop(lap, compound) for lap, compound in stops))


def test_hand_calculated_components_and_single_pit_charge():
    config = make_config(laps=4, degradation=2.0, warmup=(3.0, 1.0))
    medium = replace(config.tires[1], pace_offset_s=1.0)
    config = replace(config, tires=(config.tires[0], medium, config.tires[2]))
    result = simulate(config, schedule((2, Compound.MEDIUM)))
    # Soft: 100+3, 100+2+1; medium: 100+1+3+10, 100+1+2+1.
    assert [lap.lap_time_s for lap in result.laps] == [103, 103, 114, 104]
    assert [lap.pit_loss_s for lap in result.laps] == [0, 0, 10, 0]
    assert result.total_elapsed_s == 424
    assert result.pit_boundaries == (2,)
    assert [(s.compound, s.first_lap, s.last_lap) for s in result.stints] == [
        (Compound.SOFT, 1, 2),
        (Compound.MEDIUM, 3, 4),
    ]
    assert result.legal
    assert result.legality_errors == ()


def test_fresh_age_warmup_and_degradation_cap():
    result = simulate(
        make_config(laps=6, degradation=4, cap=5, warmup=(2, 1)),
        schedule((3, Compound.HARD)),
    )
    assert [lap.tire_age_laps for lap in result.laps] == [0, 1, 2, 0, 1, 2]
    assert [lap.warmup_s for lap in result.laps] == [2, 1, 0, 2, 1, 0]
    assert [lap.degradation_s for lap in result.laps] == [0, 4, 5, 0, 4, 5]


def test_start_and_each_fit_consume_inventory_and_no_reuse():
    race = Race(make_config(laps=5))
    assert race.state.remaining_sets == (1, 2, 2)
    race.step(Action.STAY_OUT)
    race.step(Action.PIT_SOFT)
    assert race.state.remaining_sets == (0, 2, 2)
    assert not race.observe().allows(Action.PIT_SOFT)
    race.step(Action.PIT_HARD)
    assert race.state.remaining_sets == (0, 2, 1)
    assert race.state.tire_age_laps == 1
    assert race.state.pit_boundaries == (1, 2)
    assert race.observe().action_mask == (True, False, False, False)


def test_same_compound_stop_creates_new_stint():
    result = simulate(make_config(), schedule((2, Compound.SOFT), (4, Compound.HARD)))
    assert [(s.first_lap, s.last_lap) for s in result.stints] == [(1, 2), (3, 4), (5, 6)]
    assert [lap.tire_age_laps for lap in result.laps] == [0, 1, 0, 1, 0, 1]


def test_mask_initial_final_and_mandatory_change():
    race = Race(make_config(laps=2))
    assert race.observe().action_mask == (True, False, False, False)
    race.step(Action.STAY_OUT)
    assert race.observe().action_mask == (False, False, True, True)
    race.step(Action.PIT_MEDIUM)
    assert race.observe().action_mask == (False, False, False, False)
    assert race.result().legal


def test_mask_preserves_last_stop_for_required_compound():
    race = Race(make_config(max_stops=1))
    race.step(Action.STAY_OUT)
    assert not race.observe().allows(Action.PIT_SOFT)
    assert race.observe().allows(Action.PIT_MEDIUM)


def test_mask_preserves_enough_future_laps_for_three_compounds():
    race = Race(make_config(laps=3, min_compounds=3))
    race.step(Action.STAY_OUT)
    assert race.observe().action_mask == (False, False, True, True)
    race.step(Action.PIT_MEDIUM)
    assert race.observe().action_mask == (False, False, False, True)
    race.step(Action.PIT_HARD)
    assert race.result().legal


@pytest.mark.parametrize("action", list(Action)[1:] + ["pit_soft", None, 17])
def test_invalid_initial_action_is_atomic(action):
    race = Race(make_config())
    before = (race.state, race.observe(), race.result())
    with pytest.raises(InvalidAction):
        race.step(action)
    assert (race.state, race.observe(), race.result()) == before


def test_invalid_inventory_stop_limit_and_terminal_actions_are_atomic():
    race = Race(make_config(laps=4, sets=(1, 2, 2)))
    race.step(Action.STAY_OUT)
    for action in (Action.PIT_SOFT,):
        before = race.result(), race.state
        with pytest.raises(InvalidAction):
            race.step(action)
        assert (race.result(), race.state) == before
    race.step(Action.PIT_MEDIUM)
    race.step(Action.PIT_HARD)
    before = race.result(), race.state
    with pytest.raises(InvalidAction):
        race.step(Action.PIT_MEDIUM)
    assert (race.result(), race.state) == before
    race.step(Action.STAY_OUT)
    for action in Action:
        before = race.result(), race.state
        with pytest.raises(InvalidAction):
            race.step(action)
        assert (race.result(), race.state) == before


def test_rejected_illegal_finish_does_not_mutate():
    race = Race(make_config(laps=2))
    race.step(Action.STAY_OUT)
    before = race.result(), race.state
    with pytest.raises(InvalidAction):
        race.step(Action.STAY_OUT)
    assert (race.result(), race.state) == before


def test_state_and_observation_cannot_be_mutated_by_policy():
    race = Race(make_config())
    with pytest.raises(FrozenInstanceError):
        race.state.completed_laps = 100
    with pytest.raises(FrozenInstanceError):
        race.observe().completed_laps = 100


def test_terminal_legality_check_is_independent_of_mask():
    config = make_config(laps=2)
    race = Race(config)
    assert not race.result().legal
    invalid_finish = replace(
        race.state, completed_laps=2, used_compounds=frozenset({Compound.SOFT})
    )
    assert "At least 2 distinct compounds required" in check_finish(config, invalid_finish)
    bad_inventory = replace(invalid_finish, remaining_sets=(-1, 2, 2))
    assert "Invalid tire inventory" in check_finish(config, bad_inventory)


def test_same_inputs_produce_identical_results():
    config = make_config(degradation=0.7, warmup=(1.3,))
    policy = schedule((2, Compound.MEDIUM), (4, Compound.SOFT))
    assert simulate(config, policy) == simulate(config, policy)


def test_equal_pace_no_degradation_favors_no_optional_stop():
    config = make_config()
    one = simulate(config, schedule((3, Compound.MEDIUM)))
    two = simulate(config, schedule((2, Compound.MEDIUM), (4, Compound.HARD)))
    assert one.total_elapsed_s == 610
    assert two.total_elapsed_s == 620
    relaxed = replace(config, rules=replace(config.rules, min_distinct_compounds=1))
    assert simulate(relaxed, schedule()).total_elapsed_s == 600


def test_constructed_high_degradation_makes_second_stop_worthwhile():
    config = make_config(degradation=10, pit_loss=5)
    one = simulate(config, schedule((3, Compound.MEDIUM)))
    two = simulate(config, schedule((2, Compound.MEDIUM), (4, Compound.HARD)))
    assert one.total_elapsed_s == 665  # 600 + 2*(0+10+20) + 5
    assert two.total_elapsed_s == 640  # 600 + 3*(0+10) + 10
    assert two.total_elapsed_s < one.total_elapsed_s


@pytest.mark.parametrize(
    "stops", [((3, Compound.MEDIUM),), ((2, Compound.MEDIUM), (4, Compound.HARD))]
)
def test_increasing_pit_loss_never_improves_fixed_strategy(stops):
    policy = schedule(*stops)
    times = [
        simulate(make_config(pit_loss=p, degradation=2), policy).total_elapsed_s
        for p in (0, 5, 20, 100)
    ]
    assert times == sorted(times)
    assert times[-1] - times[0] == 100 * len(stops)
