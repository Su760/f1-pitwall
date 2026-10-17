"""S2 acceptance, unchanged engine search and existing-format reproduction."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from pitwall.lab_optimization import optimize_lab
from pitwall.optimizer import SearchTooLarge
from pitwall.replay import replay_document
from pitwall.scenario import load_scenario
from pitwall.sensitivity import load_lab, resolve
from pitwall.serialization import write_document

LAB = Path("scenarios/sensitivity-lab.json")
SEARCH = Path("scenarios/lab-optimization.json")
CONTROLS = dict(pit_loss_s=18, degradation_multiplier=1, warmup_multiplier=1)


@pytest.mark.parametrize(
    "pit,total,stops,benchmarks",
    [
        (18, 1113.550, [(5, "medium")], [1113.850, 1124.700]),
        (7.15, 1102.700, [(5, "medium")], [1103, 1103]),
        (0, 1088.700, [(4, "soft"), (8, "medium")], [1095.850, 1088.700]),
    ],
)
def test_acceptance_and_replay(pit, total, stops, benchmarks, tmp_path):
    controls = {**CONTROLS, "pit_loss_s": pit}
    record = optimize_lab(LAB, SEARCH, controls)
    search = record["search"]
    assert search["search_complete"] is True
    assert (search["candidate_count"], search["legal_count"]) == (529, 462)
    assert search["candidate_counts_by_stops"] == [1, 33, 495]
    assert search["legal_counts_by_stops"] == [0, 22, 440]
    assert search["max_lap_evaluations_required"] == 6348
    assert search["benchmark_lap_evaluations"] == 24
    assert len(search["ranked"]) == search["top_k"] == 3
    assert record["best"]["total_elapsed_s"] == pytest.approx(total, abs=1e-9, rel=0)
    assert [(s["after_lap"], s["compound"]) for s in record["best"]["schedule"]["stops"]] == stops
    assert [b["total_elapsed_s"] for b in record["benchmarks"]] == pytest.approx(
        benchmarks, abs=1e-9, rel=0
    )
    for baseline, expected in zip(record["benchmarks"], benchmarks, strict=True):
        assert baseline["improvement_s"] == pytest.approx(expected - total, abs=1e-9, rel=0)
    assert (
        record["source"]["optimization_settings_sha256"]
        == hashlib.sha256(SEARCH.read_bytes()).hexdigest()
    )
    scenario_path = tmp_path / "scenario.json"
    write_document(scenario_path, record["scenario"])
    scenario = load_scenario(scenario_path)
    replay_document(record["trace"], expected_config=scenario.configuration)
    assert record == optimize_lab(LAB, SEARCH, controls)
    assert json.loads(json.dumps(record)) == record


@pytest.mark.parametrize("budget,value", [("max_candidates", 528), ("max_lap_evaluations", 6347)])
def test_both_budgets_reject_before_any_simulation(budget, value, tmp_path):
    settings = json.loads(SEARCH.read_text())
    settings[budget] = value
    path = tmp_path / "search.json"
    write_document(path, settings)
    with (
        patch("pitwall.optimizer.simulate") as search_sim,
        patch("pitwall.sensitivity.simulate") as benchmark_sim,
    ):
        with pytest.raises(SearchTooLarge):
            optimize_lab(LAB, path, CONTROLS)
        search_sim.assert_not_called()
        benchmark_sim.assert_not_called()


def test_incomplete_search_is_not_an_optimum():
    from pitwall.optimizer import SearchLimits, optimize

    _, scenario, _ = load_lab(LAB)
    result = optimize(scenario.configuration, limits=SearchLimits(), top_k=3)
    illegal = replace(result.best, result=replace(result.best.result, legal=False))
    for broken in (
        replace(result, search_complete=False),
        replace(result, ranked=()),
        replace(result, ranked=(illegal,)),
    ):
        with (
            patch("pitwall.lab_optimization.optimize", return_value=broken),
            patch("pitwall.sensitivity.simulate") as benchmark,
        ):
            with pytest.raises(RuntimeError, match="complete legal"):
                optimize_lab(LAB, SEARCH, CONTROLS)
            benchmark.assert_not_called()


def test_resolution_scales_all_tires_and_starting_warmup():
    controls = {**CONTROLS, "degradation_multiplier": 2.5, "warmup_multiplier": 0.5}
    record = optimize_lab(LAB, SEARCH, controls)
    _, base, _ = load_lab(LAB)
    expected = resolve(base, controls).configuration.to_dict()
    assert record["scenario"]["configuration"] == expected
    assert record["trace"]["configuration"] == expected
    assert record["trace"]["laps"][0]["warmup_s"] == 0.5
