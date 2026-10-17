"""S1 math, legality, scaling, bounds, exports and deterministic recomputation."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from pitwall.actions import Compound
from pitwall.policies import FixedSchedule, PitStop
from pitwall.scenario import Scenario, load_scenario
from pitwall.sensitivity import (
    classification,
    comparison,
    evaluate_lab,
    load_lab,
    main,
    resolve,
    validate_controls,
)
from pitwall.serialization import write_document

SETTINGS = Path("scenarios/sensitivity-lab.json")


def controls(pit=18, degradation=1, warmup=1):
    return dict(pit_loss_s=pit, degradation_multiplier=degradation, warmup_multiplier=warmup)


@pytest.mark.parametrize(
    "pit,expected,winner",
    [
        (18, [1113.850, 1124.700], "one-stop"),
        (7.15, [1103, 1103], "tie"),
        (0, [1095.850, 1088.700], "two-stop"),
    ],
)
def test_acceptance_totals_and_components(pit, expected, winner):
    settings, base, _ = load_lab(SETTINGS)
    result = comparison(resolve(base, controls(pit)), settings)
    assert [s["total_elapsed_s"] for s in result["strategies"]] == pytest.approx(expected, abs=1e-9)
    assert result["winner"] == winner
    assert result["delta_s"] == pytest.approx(expected[1] - expected[0], abs=1e-9)
    for s in result["strategies"]:
        assert s["legal"]
        assert sum(s["components"].values()) == pytest.approx(s["total_elapsed_s"], abs=1e-9)
        assert sum(lap["lap_time_s"] for lap in s["laps"]) == s["total_elapsed_s"]


def test_scaling_both_slope_cap_all_warmup_and_no_baseline_mutation():
    settings, base, _ = load_lab(SETTINGS)
    before = deepcopy(base)
    adjusted = resolve(base, controls(4, 2.5, 3))
    assert base == before
    assert adjusted.strategies == base.strategies
    for old, new in zip(base.configuration.tires, adjusted.configuration.tires, strict=True):
        assert new.degradation_s_per_lap == old.degradation_s_per_lap * 2.5
        assert new.degradation_cap_s == old.degradation_cap_s * 2.5
        assert new.warmup_s == tuple(w * 3 for w in old.warmup_s)
        assert new.pace_offset_s == old.pace_offset_s and new.fresh_sets == old.fresh_sets
        for age in [0, 1, 5, 100]:
            assert min(new.degradation_cap_s, new.degradation_s_per_lap * age) == pytest.approx(
                2.5 * min(old.degradation_cap_s, old.degradation_s_per_lap * age)
            )
    result = comparison(adjusted, settings)
    for s in result["strategies"]:
        assert s["laps"][0]["warmup_s"] == 3  # Starting soft set, not only fitted pit sets.
    zero = comparison(resolve(base, controls(0, 0, 0)), settings)
    assert all(
        s["components"]["degradation_s"] == s["components"]["warmup_s"] == 0
        for s in zero["strategies"]
    )
    assert (
        replace(adjusted.configuration, tires=base.configuration.tires, pit_loss_s=18)
        == base.configuration
    )


def test_pit_marginal_cost_and_illegal_schedule_rejection():
    settings, base, _ = load_lab(SETTINGS)
    low, high = [comparison(resolve(base, controls(p, 2, 0.5)), settings) for p in (3, 11)]
    for a, b in zip(low["strategies"], high["strategies"], strict=True):
        assert b["total_elapsed_s"] - a["total_elapsed_s"] == pytest.approx(
            a["pit_count"] * 8, abs=1e-9
        )
    illegal = Scenario(
        base.configuration,
        (FixedSchedule("one-stop", (PitStop(12, Compound.MEDIUM),)), base.strategies[1]),
    )
    with pytest.raises(ValueError):
        comparison(illegal, settings)


@pytest.mark.parametrize("value", [-1, 41, True, None, "18", float("nan"), float("inf"), 10**500])
def test_invalid_pit_controls(value):
    settings, _, _ = load_lab(SETTINGS)
    with pytest.raises(ValueError):
        validate_controls(controls(value), settings)


@pytest.mark.parametrize("grid", [0, 1, 22, 100000, True, 2.0, "21", None])
def test_grid_work_bounds(grid):
    with pytest.raises(ValueError):
        evaluate_lab(SETTINGS, controls(), grid)


def test_grid_is_engine_computed_bounded_and_warmup_fixed():
    result = evaluate_lab(SETTINGS, controls(7.15, 1, 2), 21)
    assert result["grid"]["lap_evaluations"] == 10608
    rows = result["grid"]["rows"]
    assert len(rows) == 21 and all(len(r) == 21 for r in rows)
    assert result["grid"]["axes"]["pit_loss_s"][::20] == [0, 40]
    assert result["grid"]["axes"]["degradation_multiplier"][::20] == [0, 3]
    settings, base, _ = load_lab(SETTINGS)
    for r in (rows[0], rows[10], rows[-1]):
        for point in r:
            expected = comparison(
                resolve(base, controls(point["pit_loss_s"], point["degradation_multiplier"], 2)),
                settings,
            )
            assert point["delta_s"] == expected["delta_s"]
            assert point["winner"] == expected["winner"]
            assert point["warmup_multiplier"] == 2


def test_tie_and_near_tie_classification_uses_full_precision():
    settings, _, _ = load_lab(SETTINGS)
    assert classification(1e-10, settings)["winner"] == "tie"
    assert classification(-0.00001, settings)["winner"] == "two-stop"
    assert classification(-0.00001, settings)["near_tie"]
    assert not classification(0.01, settings)["near_tie"]


def test_export_loader_and_exact_offline_recomputation(tmp_path):
    a = evaluate_lab(SETTINGS, controls(7.15, 1.2, 0.5), 3)
    assert a == evaluate_lab(SETTINGS, controls(7.15, 1.2, 0.5), 3)
    scenario, record, out = (
        tmp_path / "scenario.json",
        tmp_path / "record.json",
        tmp_path / "out.json",
    )
    write_document(scenario, a["scenario"])
    write_document(record, a)
    settings, _, _ = load_lab(SETTINGS)
    assert comparison(load_scenario(scenario), settings) == a["comparison"]
    assert main(["--scenario", str(scenario), "--output", str(out)]) == 0
    assert json.loads(out.read_text()) == a["comparison"]
    assert main(["--record", str(record), "--output", str(out)]) == 0
    assert out.read_bytes() == record.read_bytes()
    assert main(["--record", str(record), "--output", str(record)]) == 1
    a["grid"]["rows"][0][0]["delta_s"] += 1
    write_document(record, a)
    assert main(["--record", str(record), "--output", str(out)]) == 1
