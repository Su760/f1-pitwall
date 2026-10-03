from dataclasses import replace
from pathlib import Path

import pytest
from conftest import make_config

import pitwall.optimizer as optimizer
from pitwall.actions import Compound
from pitwall.engine import simulate
from pitwall.optimizer import SearchLimits, SearchTooLarge, optimize
from pitwall.policies import FixedSchedule, PitStop
from pitwall.scenario import load_scenario


def test_synthetic_exhaustive_counts_and_unique_optimum():
    scenario = load_scenario(Path("scenarios/synthetic.json"))
    search = optimize(scenario.configuration, limits=SearchLimits())
    # 0 stops + 11 boundaries * 3 compounds + C(11, 2) * 3**2.
    assert search.candidate_counts_by_stops == (1, 33, 495)
    assert search.candidate_count == 529
    # One-stop soft is illegal; two-stop soft/soft exhausts starting inventory.
    assert search.legal_counts_by_stops == (0, 22, 440)
    assert search.legal_count == 462
    assert search.search_complete
    assert search.max_lap_evaluations_required == 529 * 12
    assert search.best.schedule.stops == (PitStop(5, Compound.MEDIUM),)
    assert search.best.result.total_elapsed_s == pytest.approx(1113.550)
    assert search.best.gap_s == 0
    assert len(search.ranked) == 5
    assert search.ranked[1].gap_s > 0
    baseline = simulate(scenario.configuration, scenario.strategies[0])
    assert baseline.total_elapsed_s == pytest.approx(1113.850)
    assert baseline.total_elapsed_s - search.best.result.total_elapsed_s == pytest.approx(0.3)
    for ranked in search.ranked:
        assert ranked.result == simulate(scenario.configuration, ranked.schedule)
        assert ranked.gap_s == ranked.result.total_elapsed_s - search.best.result.total_elapsed_s


def test_tiny_independently_calculated_optimum():
    config = make_config(laps=4, pit_loss=3, max_stops=1)
    config = replace(
        config,
        tires=(
            replace(config.tires[0], degradation_s_per_lap=4),
            replace(config.tires[1], degradation_s_per_lap=1),
            replace(config.tires[2], pace_offset_s=5),
        ),
    )
    search = optimize(config, limits=SearchLimits(), top_k=6)
    # Medium after 1: 100 + (100+3) + 101 + 102 = 406.
    # Medium after 2/3: 408/415. Hard after 1/2/3: 418/417/420.
    assert [row.result.total_elapsed_s for row in search.ranked] == [
        406,
        408,
        415,
        417,
        418,
        420,
    ]
    assert search.best.schedule.stops == (PitStop(1, Compound.MEDIUM),)
    assert search.candidate_count == 10
    assert search.legal_count == 6


def test_fresh_same_compound_sets_are_enumerated_and_inventory_respected():
    config = make_config(laps=4, pit_loss=1, degradation=10, min_compounds=1, sets=(3, 0, 0))
    search = optimize(config, limits=SearchLimits())
    assert search.candidate_counts_by_stops == (1, 9, 27)
    assert search.legal_counts_by_stops == (1, 3, 3)
    assert search.best.result.total_elapsed_s == 412
    assert search.best.schedule.stops == (
        PitStop(1, Compound.SOFT),
        PitStop(2, Compound.SOFT),
    )


def test_no_stop_allowed_and_no_optional_stop_with_equal_pace():
    config = make_config(laps=4, min_compounds=1)
    search = optimize(config, limits=SearchLimits())
    assert search.best.schedule.stops == ()
    assert search.best.result.total_elapsed_s == 400
    assert search.legal_counts_by_stops[0] == 1


def test_all_configured_stop_counts_and_only_existing_boundaries():
    config = make_config(
        laps=4, pit_loss=1, degradation=10, min_compounds=1, max_stops=8, sets=(4, 0, 0)
    )
    search = optimize(config, limits=SearchLimits())
    assert search.candidate_counts_by_stops == (1, 9, 27, 27)
    assert search.legal_counts_by_stops == (1, 3, 3, 1)
    assert search.best.result.total_elapsed_s == 403
    assert search.best.result.pit_boundaries == (1, 2, 3)


def test_configured_start_compound_is_used():
    config = make_config(laps=2, max_stops=1)
    config = replace(config, start_compound=Compound.HARD)
    search = optimize(config, limits=SearchLimits())
    assert search.legal_count == 2
    assert search.best.result.stints[0].compound is Compound.HARD
    assert search.best.schedule.stops == (PitStop(1, Compound.SOFT),)


def test_exact_ties_use_stop_count_boundaries_and_declaration_order():
    config = make_config(laps=3, pit_loss=0, min_compounds=1, sets=(3, 3, 3))
    search = optimize(config, limits=SearchLimits(), top_k=16)
    expected = [()]
    expected += [(PitStop(lap, compound),) for lap in (1, 2) for compound in Compound]
    expected += [
        (PitStop(1, first), PitStop(2, second)) for first in Compound for second in Compound
    ]
    assert [row.schedule.stops for row in search.ranked] == expected
    assert all(row.gap_s == 0 for row in search.ranked)
    assert optimize(config, limits=SearchLimits(), top_k=16) == search


def test_near_ties_preserve_full_precision():
    config = make_config(laps=2, max_stops=1)
    config = replace(
        config,
        tires=(config.tires[0], replace(config.tires[1], pace_offset_s=1e-10), config.tires[2]),
    )
    search = optimize(config, limits=SearchLimits())
    assert search.best.schedule.stops == (PitStop(1, Compound.HARD),)
    assert 0 < search.ranked[1].gap_s < 1e-9


@pytest.mark.parametrize(
    "limits,match",
    [
        (SearchLimits(max_candidates=528), "max_candidates"),
        (SearchLimits(max_lap_evaluations=6347), "max_lap_evaluations"),
    ],
)
def test_rejects_unsupported_search_before_any_scoring(monkeypatch, limits, match):
    def unexpected_scoring(*args, **kwargs):
        pytest.fail("Unsupported search started scoring candidates")

    monkeypatch.setattr(optimizer, "simulate", unexpected_scoring)
    config = load_scenario(Path("scenarios/synthetic.json")).configuration
    with pytest.raises(SearchTooLarge, match=match):
        optimize(config, limits=limits)


def test_exact_search_limits_are_supported():
    config = make_config(laps=2, max_stops=1)
    result = optimize(config, limits=SearchLimits(max_candidates=4, max_lap_evaluations=8))
    assert result.candidate_count == 4
    assert result.search_complete


def test_interrupted_search_does_not_return_completed_result(monkeypatch):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(optimizer, "simulate", interrupted)
    with pytest.raises(KeyboardInterrupt):
        optimize(make_config(), limits=SearchLimits())


@pytest.mark.parametrize("field", ["max_candidates", "max_lap_evaluations"])
@pytest.mark.parametrize("value", [True, 0, -1, 1.0, float("inf"), "100"])
def test_invalid_limits_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        SearchLimits(**{field: value})


@pytest.mark.parametrize("value", [True, 0, -1, 1.0, "5"])
def test_invalid_ranked_count_rejected(value):
    with pytest.raises(ValueError, match="top_k"):
        optimize(make_config(), limits=SearchLimits(), top_k=value)


def test_zero_stop_one_lap_search():
    config = make_config(laps=1, min_compounds=1, max_stops=0)
    search = optimize(config, limits=SearchLimits())
    assert search.candidate_count == search.legal_count == 1
    assert search.candidate_counts_by_stops == search.legal_counts_by_stops == (1,)
    assert search.best.schedule == FixedSchedule("optimized-no-stops", ())
