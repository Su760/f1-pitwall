"""Independent scoring and state-isolation checks for the three synthetic calls."""

from copy import deepcopy
from dataclasses import replace

import pytest

from apps.api.challenges import (
    ChallengeError,
    challenge_detail,
    challenge_summaries,
    evaluate,
    evaluate_boundary,
    load_challenge,
)
from pitwall.actions import Action, Compound
from pitwall.config import RaceConfig, Rules, TireParameters
from pitwall.engine import InvalidAction, Race
from pitwall.snapshots import fork, snapshot_document

IDS = ("closing-laps", "stint-choice", "final-stint")


def altered_parent(challenge_id, change):
    original = load_challenge(challenge_id, 1).race
    config = change(original.configuration)
    altered = Race(config)
    for record in original.result().actions:
        altered.step(record.action)
    return altered


@pytest.mark.parametrize("challenge_id", IDS)
def test_every_masked_choice_finishes_with_frozen_continuation(challenge_id):
    parent = load_challenge(challenge_id, 1).race
    before = snapshot_document(parent)
    for action in Action:
        if parent.observe().allows(action):
            result = evaluate(challenge_id, 1, action)
            assert result["selected"]["legal"]
            assert result["selected"]["laps"][0]["lap"] == parent.state.completed_laps + 1
            assert result["selected"]["laps"][-1]["lap"] == parent.configuration.laps
            assert all(item["legal"] for item in result["alternatives"])
            assert result == evaluate(challenge_id, 1, action)
    assert snapshot_document(parent) == before


def test_independent_hand_calculated_score():
    # Boundary after lap 1: soft age 1, elapsed 10. Remaining laps 2,3.
    # Stay: 12 + 14 = 26. Medium: (10 + 1 pace + 1 warm + 3 pit) + 11 = 26.
    # Hard: (10 - 1 pace + 2 warm + 3 pit) + 9 = 23. Excess stay = 3.
    race = Race(
        RaceConfig(
            "hand calculation",
            3,
            10,
            3,
            Compound.SOFT,
            (
                TireParameters(Compound.SOFT, 0, 2, 20, (), 2),
                TireParameters(Compound.MEDIUM, 1, 0, 0, (1,), 2),
                TireParameters(Compound.HARD, -1, 0, 0, (2,), 2),
            ),
            Rules(1, 1),
        )
    )
    race.step(Action.STAY_OUT)
    result = evaluate_boundary(race, Action.STAY_OUT)
    assert result["score_s"] == 3
    assert result["best_action"] == "pit_hard"
    assert result["best_remaining_elapsed_s"] == 23
    assert result["selected"]["components"] == {
        "base_s": 20,
        "pace_s": 0,
        "degradation_s": 6,
        "warmup_s": 0,
        "pit_s": 0,
    }
    assert result["debrief"]["delta_components"] == {
        "base_s": 0,
        "pace_s": 2,
        "degradation_s": 6,
        "warmup_s": -2,
        "pit_s": -3,
    }
    # Exact tie at 26 s ranks stay before medium according to enum order.
    tied = [item["action"] for item in result["alternatives"] if item["remaining_elapsed_s"] == 26]
    assert tied == ["stay_out", "pit_medium"]


def test_second_stop_tradeoff_changes_when_pit_loss_increases():
    original = evaluate("closing-laps", 1, Action.STAY_OUT)
    assert original["best_action"] != "stay_out"
    costly = altered_parent("closing-laps", lambda c: replace(c, pit_loss_s=c.pit_loss_s + 30))
    assert evaluate_boundary(costly, Action.STAY_OUT)["best_action"] == "stay_out"
    flat = altered_parent(
        "closing-laps",
        lambda c: replace(c, tires=tuple(replace(t, degradation_s_per_lap=0) for t in c.tires)),
    )
    assert evaluate_boundary(flat, Action.STAY_OUT)["best_action"] == "stay_out"


def test_compound_choice_changes_with_pace_warmup_and_degradation():
    assert evaluate("stint-choice", 1, Action.PIT_MEDIUM)["best_action"] == "pit_medium"
    for field, value in (("warmup_s", ()), ("degradation_s_per_lap", 0)):
        changed = altered_parent(
            "stint-choice",
            lambda c, field=field, value=value: replace(
                c, tires=tuple(replace(t, **{field: value}) for t in c.tires)
            ),
        )
        result = evaluate_boundary(changed, Action.PIT_MEDIUM)
        assert result["best_action"] != "pit_medium"
    no_pace = altered_parent(
        "stint-choice",
        lambda c: replace(c, tires=tuple(replace(t, pace_offset_s=0) for t in c.tires)),
    )
    original = evaluate("stint-choice", 1, Action.PIT_SOFT)
    assert evaluate_boundary(no_pace, Action.PIT_SOFT)["score_s"] != original["score_s"]


def test_final_stint_requires_a_new_compound_and_warmup_matters():
    detail = challenge_detail("final-stint", 1)
    mask = {entry["action"]: entry for entry in detail["actions"]}
    assert not mask["stay_out"]["available"]
    assert not mask["pit_soft"]["available"]
    assert "compound" in mask["stay_out"]["reason"]
    assert mask["pit_medium"]["available"] and mask["pit_hard"]["available"]
    assert evaluate("final-stint", 1, Action.PIT_MEDIUM)["best_action"] == "pit_hard"
    no_warmup = altered_parent(
        "final-stint", lambda c: replace(c, tires=tuple(replace(t, warmup_s=()) for t in c.tires))
    )
    assert evaluate_boundary(no_warmup, Action.PIT_MEDIUM)["best_action"] == "pit_medium"
    for action in (Action.STAY_OUT, Action.PIT_SOFT):
        with pytest.raises(ChallengeError, match="compound"):
            evaluate("final-stint", 1, action)


@pytest.mark.parametrize("challenge_id", IDS)
def test_component_totals_gaps_and_fork_comparison(challenge_id):
    parent = load_challenge(challenge_id, 1).race
    legal = [a for a in Action if parent.observe().allows(a)]
    original = evaluate(challenge_id, 1, legal[0])
    saved = deepcopy(original)
    compared = evaluate(challenge_id, 1, legal[-1], legal[0])
    assert original == saved == evaluate(challenge_id, 1, legal[0])
    comparison = compared["comparison"]
    assert comparison["delta_remaining_s"] == (
        compared["selected"]["remaining_elapsed_s"] - original["selected"]["remaining_elapsed_s"]
    )
    assert comparison["gap_series"][0] == {"lap": parent.state.completed_laps, "gap_s": 0}
    assert comparison["gap_series"][-1]["gap_s"] == comparison["delta_remaining_s"]
    assert sum(comparison["components_delta"].values()) == pytest.approx(
        comparison["delta_remaining_s"], abs=1e-10
    )
    for result in compared["alternatives"]:
        assert sum(result["components"].values()) == pytest.approx(result["remaining_elapsed_s"])
        assert result["cumulative"][-1]["gap_to_best_s"] == result["excess_s"]
        assert result["total_elapsed_s"] - parent.state.elapsed_s == result["remaining_elapsed_s"]


def test_parent_two_children_and_rejected_action_are_independent():
    parent = load_challenge("final-stint", 1).race
    child1, child2 = fork(parent), fork(parent)
    before = snapshot_document(parent)
    child1.step(Action.PIT_MEDIUM)
    child1_before = snapshot_document(child1)
    with pytest.raises(InvalidAction):
        child2.step(Action.STAY_OUT)
    assert snapshot_document(parent) == snapshot_document(child2) == before
    assert parent.observe() == child2.observe()
    child2.step(Action.PIT_HARD)
    assert snapshot_document(parent) == before
    assert snapshot_document(child1) == child1_before
    assert child1.result().total_elapsed_s != child2.result().total_elapsed_s


def test_public_payload_only_contains_present_past_and_assumptions():
    assert [item["id"] for item in challenge_summaries()] == list(IDS)
    forbidden = {"snapshot", "configuration", "score_s", "best_action", "alternatives", "laps"}
    for challenge_id in IDS:
        detail = challenge_detail(challenge_id, 1)
        assert not forbidden.intersection(detail)
        assert set(detail) == {
            "api_version",
            "id",
            "version",
            "title",
            "summary",
            "remaining_laps",
            "briefing",
            "objective",
            "continuation",
            "situation",
            "actions",
            "assumptions",
        }
        assert detail["assumptions"]["noise"] == "disabled"
        assert len(detail["assumptions"]["tires"]) == 3
        assert all(
            s["last_lap"] <= detail["situation"]["completed_laps"]
            for s in detail["situation"]["stints"]
        )
