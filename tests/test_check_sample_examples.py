"""The baseline helper must exercise the CLI safely even with a hostile parent mode."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_sample_checker_forces_offline_and_retains_isolated_artifacts(tmp_path):
    source_files = sorted((ROOT / "input_examples").glob("*.json"))
    before = {path: path.read_bytes() for path in source_files}
    artifact_dir = tmp_path / "artifacts"
    env = {**os.environ, "SAMPLE_MODE": "false", "METERLESS_RUNTIME_TOKEN": "test-only-parent-token"}
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_sample_examples.py"), "--output-dir", str(artifact_dir)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "pass" and manifest["sponsor_readiness"] == "not_verified"
    assert manifest["python_network_guard"] is True and manifest["dotenv_loading"] is False
    assert [case["feature_tables"] for case in manifest["results"]] == [4, 3, 2]
    assert all(case["status"] == "pass" for case in manifest["results"])
    for case in manifest["results"]:
        assert (artifact_dir / case["pack"]).exists()
        assert (artifact_dir / case["trace"]).exists()
        request = json.loads((artifact_dir / case["request"]).read_text(encoding="utf-8"))
        assert request["sample_mode"] is True
    assert all(path.read_bytes() == before[path] for path in source_files)
    assert "test-only-parent-token" not in result.stdout + result.stderr

    # A rerun must not overwrite the retained evidence or erase a run database.
    saved_manifest = (artifact_dir / "manifest.json").read_bytes()
    duplicate = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_sample_examples.py"), "--output-dir", str(artifact_dir)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    assert duplicate.returncode == 2
    assert (artifact_dir / "manifest.json").read_bytes() == saved_manifest
