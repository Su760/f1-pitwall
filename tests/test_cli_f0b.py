import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "scenarios/synthetic.json"


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "pitwall", *map(str, args)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def baseline(tmp_path):
    result = cli(SCENARIO, "--trace-dir", tmp_path)
    assert result.returncode == 0, result.stderr
    return tmp_path / "01.json"


def test_optimize_reports_complete_counts_ranking_and_verified_best(tmp_path):
    output = tmp_path / "best.json"
    result = cli("optimize", SCENARIO, "--top", 3, "--output", output)
    assert result.returncode == 0, result.stderr
    assert "COMPLETE exhaustive search" in result.stdout
    assert "529 candidates; 462 legal" in result.stdout
    assert "1 stops: 22 legal" in result.stdout
    assert "2 stops: 440 legal" in result.stdout
    assert "1113.550" in result.stdout
    assert "5:medium" in result.stdout
    assert "one-stop: 0.300 s improvement" in result.stdout
    replay = cli("replay", output, "--scenario", SCENARIO)
    assert replay.returncode == 0, replay.stderr
    assert "VERIFIED" in replay.stdout


def test_restore_and_deliberate_fork_cli_keep_source_independent(tmp_path):
    source = baseline(tmp_path / "baseline")
    snapshot = tmp_path / "snapshot.json"
    result = cli("snapshot", source, "--after-lap", 4, "--output", snapshot)
    assert result.returncode == 0, result.stderr
    before = snapshot.read_bytes()
    restored = tmp_path / "restored.json"
    result = cli(
        "restore", snapshot, "--pit", "6:medium", "--name", "one-stop", "--output", restored
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(restored.read_text()) == json.loads(source.read_text())
    branch = tmp_path / "branch.json"
    result = cli("fork", snapshot, "--pit", "5:medium", "--output", branch)
    assert result.returncode == 0, result.stderr
    assert "Parent unchanged at boundary 4" in result.stdout
    assert json.loads(branch.read_text())["result"]["total_elapsed_s"] == pytest.approx(1113.55)
    assert cli("replay", branch).returncode == 0
    assert snapshot.read_bytes() == before


@pytest.mark.parametrize("boundary", [0, 12])
def test_reset_and_finished_snapshot_cli_roundtrip(tmp_path, boundary):
    source = baseline(tmp_path / "baseline")
    snapshot = tmp_path / "snapshot.json"
    result = cli("snapshot", source, "--after-lap", boundary, "--output", snapshot)
    assert result.returncode == 0, result.stderr
    continuation = ["--pit", "6:medium"] if boundary == 0 else []
    output = tmp_path / "continued.json"
    result = cli("restore", snapshot, *continuation, "--name", "one-stop", "--output", output)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text()) == json.loads(source.read_text())


@pytest.mark.parametrize("pits", [["3:medium"], ["4:soft", "5:soft"], ["6:wet"], []])
def test_invalid_continuation_writes_nothing_and_preserves_snapshot(tmp_path, pits):
    source = baseline(tmp_path / "baseline")
    snapshot = tmp_path / "snapshot.json"
    assert cli("snapshot", source, "--after-lap", 4, "--output", snapshot).returncode == 0
    before = snapshot.read_bytes()
    output = tmp_path / "invalid.json"
    options = [value for pit in pits for value in ("--pit", pit)]
    result = cli("restore", snapshot, *options, "--output", output)
    assert result.returncode == 2
    assert "error:" in result.stderr and "Traceback" not in result.stderr
    assert not output.exists()
    assert snapshot.read_bytes() == before


def test_unsupported_search_has_no_exhaustive_result_or_output(tmp_path):
    output = tmp_path / "unsupported.json"
    result = cli("optimize", SCENARIO, "--max-candidates", 1, "--output", output)
    assert result.returncode == 2
    assert "COMPLETE" not in result.stdout
    assert not output.exists()


def test_replay_rejects_changed_components_not_just_final_time(tmp_path):
    source = baseline(tmp_path)
    data = json.loads(source.read_text())
    data["laps"][6]["pit_loss_s"] = 0
    source.write_text(json.dumps(data))
    result = cli("replay", source)
    assert result.returncode == 2
    assert "pit_loss_s" in result.stderr
    assert "VERIFIED" not in result.stdout


def test_snapshot_rejects_overwriting_input_or_invalid_boundary(tmp_path):
    source = baseline(tmp_path)
    before = source.read_bytes()
    result = cli("snapshot", source, "--after-lap", 4, "--output", source)
    assert result.returncode == 2
    assert "overwrite" in result.stderr
    assert source.read_bytes() == before
    output = tmp_path / "bad.json"
    result = cli("snapshot", source, "--after-lap", 13, "--output", output)
    assert result.returncode == 2
    assert not output.exists()
