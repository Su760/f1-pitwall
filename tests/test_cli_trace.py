import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import make_config

from pitwall.actions import Compound
from pitwall.engine import simulate
from pitwall.policies import FixedSchedule, PitStop

ROOT = Path(__file__).resolve().parents[1]


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "pitwall", *map(str, args)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_cli_compares_schedules_and_saves_deterministic_auditable_traces(tmp_path):
    command = ("scenarios/synthetic.json", "--trace-dir", tmp_path)
    first = cli(*command)
    assert first.returncode == 0, first.stderr
    assert "SYNTHETIC" in first.stdout
    assert "one-stop" in first.stdout and "two-stop" in first.stdout
    assert first.stdout.count("LEGAL") == 2
    paths = sorted(tmp_path.glob("*.json"))
    assert len(paths) == 2
    first_bytes = [p.read_bytes() for p in paths]
    from pitwall.config import RaceConfig

    for path in paths:
        trace = json.loads(path.read_text())
        assert trace["trace_version"] == 1
        assert trace["model_version"] == "f0a-linear-capped-v1"
        config = RaceConfig.from_dict(trace["configuration"])
        strategy = trace["strategy"]
        policy = FixedSchedule(
            strategy["name"],
            tuple(
                PitStop(stop["after_lap"], Compound(stop["compound"])) for stop in strategy["stops"]
            ),
        )
        replayed = simulate(config, policy)  # Rerun from initial config, not snapshot restoration.
        assert replayed.total_elapsed_s == trace["result"]["total_elapsed_s"]
        assert trace["result"]["legal"] is True
        assert len(trace["actions"]) == len(trace["laps"]) == config.laps
        assert [a["after_lap"] for a in trace["actions"]] == list(range(config.laps))
        assert trace["actions"][0]["action"] == "stay_out"
        cumulative_s = 0.0
        for lap in trace["laps"]:
            assert lap["lap_time_s"] == pytest.approx(
                sum(
                    lap[key]
                    for key in (
                        "base_lap_time_s",
                        "pace_offset_s",
                        "degradation_s",
                        "warmup_s",
                        "pit_loss_s",
                    )
                )
            )
            cumulative_s += lap["lap_time_s"]
            assert lap["elapsed_s"] == pytest.approx(cumulative_s, rel=0, abs=1e-10)
        assert trace["result"]["total_elapsed_s"] == pytest.approx(cumulative_s, rel=0, abs=1e-10)
        assert sum(lap["pit_loss_s"] for lap in trace["laps"]) == (
            config.pit_loss_s * len(strategy["stops"])
        )
    second = cli(*command)
    assert second.returncode == 0, second.stderr
    assert second.stdout == first.stdout
    assert [p.read_bytes() for p in paths] == first_bytes


def test_cli_rounding_does_not_change_trace_accounting(tmp_path):
    config = replace(make_config(laps=2), base_lap_time_s=100.000123)
    scenario = {
        "scenario_version": 1,
        "configuration": config.to_dict(),
        "strategies": [{"name": "precision", "stops": [{"after_lap": 1, "compound": "medium"}]}],
    }
    source = tmp_path / "precision.json"
    source.write_text(json.dumps(scenario))
    output = tmp_path / "traces"
    result = cli(source, "--trace-dir", output)
    assert result.returncode == 0, result.stderr
    assert "precision | 210.000 |" in result.stdout
    trace = json.loads((output / "01.json").read_text())
    # Independently: 100.000123 + (100.000123 + 10), without display rounding.
    assert [lap["lap_time_s"] for lap in trace["laps"]] == pytest.approx(
        [100.000123, 110.000123], rel=0, abs=1e-12
    )
    assert trace["result"]["total_elapsed_s"] == pytest.approx(210.000246, rel=0, abs=1e-12)


def test_cli_can_run_one_named_strategy(tmp_path):
    result = cli("scenarios/synthetic.json", "--strategy", "one-stop", "--trace-dir", tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("LEGAL") == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_cli_refuses_to_overwrite_input_scenario(tmp_path):
    source = tmp_path / "01.json"
    original = (ROOT / "scenarios/synthetic.json").read_bytes()
    source.write_bytes(original)
    result = cli(source, "--trace-dir", tmp_path)
    assert result.returncode == 2
    assert "overwrite" in result.stderr
    assert source.read_bytes() == original
    assert not (tmp_path / "02.json").exists()


def test_cli_reports_unwritable_trace_destination(tmp_path):
    output = tmp_path / "file-not-directory"
    output.write_text("preserve existing work")
    result = cli("scenarios/synthetic.json", "--trace-dir", output)
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert output.read_text() == "preserve existing work"


@pytest.mark.parametrize(
    "args", [(), ("missing-scenario.json",), ("scenarios/synthetic.json", "--strategy", "unknown")]
)
def test_cli_errors_are_nonzero_and_concise(args):
    result = cli(*args)
    assert result.returncode != 0
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_invalid_schedule_does_not_write_partial_comparison(tmp_path):
    scenario = {
        "scenario_version": 1,
        "configuration": make_config().to_dict(),
        "strategies": [
            {"name": "good", "stops": [{"after_lap": 2, "compound": "medium"}]},
            {"name": "bad", "stops": []},
        ],
    }
    source = tmp_path / "bad.json"
    source.write_text(json.dumps(scenario))
    output = tmp_path / "traces"
    result = cli(source, "--trace-dir", output)
    assert result.returncode != 0
    assert "bad" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        "[]",
        "{",
        '{"scenario_version": 1, "scenario_version": 1}',
        '{"scenario_version": NaN}',
    ],
)
def test_malformed_scenarios_rejected(tmp_path, text):
    from pitwall.scenario import load_scenario

    path = tmp_path / "bad.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        load_scenario(path)


@pytest.mark.parametrize(
    "mutation", ["version", "duplicate_names", "missing_strategies", "bad_stop"]
)
def test_scenario_schema_rejects_invalid_values(tmp_path, mutation):
    from pitwall.scenario import load_scenario

    data = json.loads((ROOT / "scenarios/synthetic.json").read_text())
    if mutation == "version":
        data["scenario_version"] = True
    elif mutation == "duplicate_names":
        data["strategies"][1]["name"] = data["strategies"][0]["name"]
    elif mutation == "missing_strategies":
        data["strategies"] = []
    else:
        data["strategies"][0]["stops"][0]["after_lap"] = 1.5
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_scenario(path)
