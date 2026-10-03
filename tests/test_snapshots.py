import json
from copy import deepcopy
from dataclasses import replace

import pytest
from conftest import make_config

from pitwall.actions import Action, Compound
from pitwall.engine import InvalidAction, Race, simulate
from pitwall.policies import FixedSchedule, PitStop
from pitwall.replay import replay_document
from pitwall.snapshots import (
    fork,
    load_snapshot,
    restore_snapshot,
    save_snapshot,
    snapshot_document,
)
from pitwall.trace import trace_document


def partial_race(completed_laps=2):
    config = make_config(laps=6, degradation=0.37, warmup=(0.7, 0.2))
    policy = FixedSchedule("one-stop", (PitStop(2, Compound.MEDIUM),))
    race = Race(config)
    for _ in range(completed_laps):
        race.step(policy.choose_action(race.observe()))
    return race, policy


@pytest.mark.parametrize("completed_laps", [0, 2, 3, 5, 6])
def test_restore_reset_before_and_after_pit_before_last_lap_and_finish(completed_laps, tmp_path):
    parent, policy = partial_race(completed_laps)
    original_document = snapshot_document(parent)
    path = tmp_path / "snapshot.json"
    save_snapshot(path, parent)
    restored = load_snapshot(path, expected_config=parent.configuration)
    assert restored.state == parent.state
    assert restored.observe() == parent.observe()
    assert restored.result() == parent.result()
    assert snapshot_document(restored) == original_document == json.loads(path.read_text())
    while not restored.finished:
        restored.step(policy.choose_action(restored.observe()))
    reference = simulate(parent.configuration, policy)
    full_trace = trace_document(parent.configuration, policy, reference)
    assert trace_document(restored.configuration, policy, restored.result()) == full_trace
    assert replay_document(full_trace).result() == restored.result()
    assert snapshot_document(parent) == original_document
    with pytest.raises(InvalidAction):
        restored.step(Action.STAY_OUT)


@pytest.mark.parametrize(
    "location,value,error",
    [
        (("snapshot_version",), True, "snapshot_version"),
        (("snapshot_version",), 2, "snapshot_version"),
        (("model_version",), "other", "model_version"),
        (("configuration_id",), "0" * 64, "configuration_id"),
        (("configuration", "pit_loss_s"), 11.0, "configuration_id"),
        (("state", "completed_laps"), 3, "state.completed_laps"),
        (("state", "current_compound"), "hard", "state.current_compound"),
        (("state", "tire_age_laps"), 0, "state.tire_age_laps"),
        (("state", "remaining_sets"), [2, 2, 2], "state.remaining_sets"),
        (("state", "used_compounds"), ["hard"], "state.used_compounds"),
        (("state", "pit_boundaries"), [1], "state.pit_boundaries"),
        (("state", "elapsed_s"), 1.0, "state.elapsed_s"),
        (("state", "elapsed_s"), float("nan"), "state.elapsed_s"),
        (("state", "completed_laps"), 2.0, "state.completed_laps"),
        (("state", "remaining_sets", 0), True, "state.remaining_sets"),
        (("actions", 0, "after_lap"), 1, r"actions\[0\].after_lap"),
        (("actions", 0, "action"), "pit_medium", r"actions\[0\]"),
        (("laps", 0, "elapsed_s"), 1.0, r"laps\[0\].elapsed_s"),
        (("result", "legal"), True, "result.legal"),
        (("result", "stints", 0, "last_lap"), 3, "result.stints"),
    ],
)
def test_restore_rejects_inconsistent_or_incompatible_snapshot(location, value, error):
    parent, _ = partial_race()
    document = snapshot_document(parent)
    target = document
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    with pytest.raises(ValueError, match=error):
        restore_snapshot(document)


def test_snapshot_requires_complete_history_and_expected_configuration():
    parent, _ = partial_race()
    document = snapshot_document(parent)
    with pytest.raises(ValueError, match="configuration.laps"):
        restore_snapshot(document, expected_config=replace(parent.configuration, laps=7))
    document["actions"].pop()
    with pytest.raises(ValueError, match="one recorded lap per action"):
        restore_snapshot(document)
    document["laps"].pop()
    with pytest.raises(ValueError, match="state.completed_laps"):
        restore_snapshot(document)


def test_terminal_legality_cannot_validate_an_invented_but_plausible_state():
    parent, _ = partial_race(6)
    document = snapshot_document(parent)
    # A terminal legality check cannot detect this forged elapsed time and tire age.
    document["state"]["elapsed_s"] += 1
    document["state"]["tire_age_laps"] += 1
    document["result"]["total_elapsed_s"] += 1
    with pytest.raises(ValueError, match="state.tire_age_laps"):
        restore_snapshot(document)


def test_snapshot_loader_rejects_duplicate_fields_and_unknown_fields(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"snapshot_version": 1, "snapshot_version": 1}')
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        load_snapshot(path)
    parent, _ = partial_race()
    document = snapshot_document(parent)
    document["state"]["invented"] = 0
    with pytest.raises(ValueError, match="state.*fields"):
        restore_snapshot(document)


def test_fork_children_parent_and_rejected_actions_are_independent():
    parent, _ = partial_race()
    parent_before = snapshot_document(parent)
    parent_observation = parent.observe()
    medium = fork(parent)
    hard = fork(parent)
    hard_before = snapshot_document(hard)
    hard_observation = hard.observe()
    medium.step(Action.PIT_MEDIUM)
    assert snapshot_document(parent) == parent_before
    assert parent.observe() == parent_observation
    assert snapshot_document(hard) == hard_before
    assert hard.observe() == hard_observation

    medium_before = snapshot_document(medium)
    hard.step(Action.PIT_HARD)
    assert snapshot_document(medium) == medium_before
    assert parent.observe() == parent_observation
    assert snapshot_document(parent) == parent_before
    assert medium.state.current_compound is Compound.MEDIUM
    assert hard.state.current_compound is Compound.HARD
    assert medium.result().actions != hard.result().actions

    # Consuming the second medium set is legal; trying a third stop is rejected.
    medium.step(Action.PIT_MEDIUM)
    snapshots = [snapshot_document(race) for race in (parent, medium, hard)]
    observations = [race.observe() for race in (parent, medium, hard)]
    with pytest.raises(InvalidAction):
        medium.step(Action.PIT_HARD)
    assert [snapshot_document(race) for race in (parent, medium, hard)] == snapshots
    assert [race.observe() for race in (parent, medium, hard)] == observations

    parent.step(Action.STAY_OUT)
    assert snapshot_document(medium) == snapshots[1]
    assert snapshot_document(hard) == snapshots[2]
    while not medium.finished:
        medium.step(Action.STAY_OUT)
    assert medium.result().legal
    assert snapshot_document(hard) == snapshots[2]
    assert len(parent.result().actions) == 3
    assert len(medium.result().actions) == 6
    assert len(hard.result().actions) == 3


def test_editing_saved_records_is_not_the_same_as_intentional_branching():
    parent, policy = partial_race(6)
    trace = trace_document(parent.configuration, policy, parent.result())
    trace["actions"][2]["action"] = "pit_hard"
    with pytest.raises(ValueError, match=r"laps\[2\].compound"):
        replay_document(trace)

    original, _ = partial_race(2)
    child = fork(original)
    child.step(Action.PIT_HARD)
    assert child.state.current_compound is Compound.HARD
    assert original.state.current_compound is Compound.SOFT


def test_snapshot_and_policy_information_are_not_added_to_observations():
    race, _ = partial_race()
    observation = deepcopy(race.observe())
    snapshot_document(race)
    fork(race)
    assert race.observe() == observation
    assert not hasattr(observation, "configuration")
    assert not hasattr(observation, "snapshot")
    assert not hasattr(observation, "history")
