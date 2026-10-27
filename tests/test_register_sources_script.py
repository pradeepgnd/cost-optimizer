"""Registration must work from a clean clone and say why it stopped."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from app.adapters.base import SetupIncomplete

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("register_sources", ROOT / "scripts" / "register_sources.py")
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)


class FakeLayer:
    seen_bindings_env = "unset"

    def __init__(self):
        FakeLayer.seen_bindings_env = os.getenv("ZETARIS_BINDINGS_FILE")
        self.client = type("Client", (), {"close": lambda self: None})()


@pytest.fixture
def apply_args(tmp_path, monkeypatch):
    storage = tmp_path / "storage.json"
    storage.write_text((ROOT / "data/source_examples/aws.oah.json").read_text())
    monkeypatch.setattr(script, "bundle_plan", lambda bundle, config: {"status": "plan"})
    monkeypatch.setattr(script, "ZetarisDataLayer", FakeLayer)
    output = tmp_path / "bindings.json"
    monkeypatch.setattr(sys, "argv", ["register_sources.py", "--bundle", str(tmp_path / "bundle"), "--storage", str(storage),
                                      "--apply", "--no-dotenv", "--bindings-output", str(output)])
    return output


def test_apply_ignores_a_bindings_file_that_does_not_exist_yet(apply_args, monkeypatch):
    # README step 3 names the file in .env before step 4 creates it; registration must not try to read it.
    monkeypatch.setenv("ZETARIS_BINDINGS_FILE", "data/localstack/does-not-exist.json")
    monkeypatch.setattr(script, "register_bundle", lambda layer, bundle, config: {"status": "pass", "bindings": {"snapshot_id": "x"}})
    assert script.main() == 0
    assert FakeLayer.seen_bindings_env is None
    assert json.loads(apply_args.read_text()) == {"snapshot_id": "x"}


def test_a_setup_failure_names_the_missing_setting(apply_args, monkeypatch, capsys):
    def missing_key(layer, bundle, config):
        raise SetupIncomplete("AWS registration needs ZETARIS_S3_ACCESS_KEY_ID and ZETARIS_S3_SECRET_ACCESS_KEY")
    monkeypatch.setattr(script, "register_bundle", missing_key)
    assert script.main() == 1
    failure = json.loads(capsys.readouterr().err)
    assert failure["error_type"] == "SetupIncomplete" and "ZETARIS_S3_ACCESS_KEY_ID" in failure["setup_issue"]
    assert not apply_args.exists()


def test_a_missing_file_is_named(apply_args, monkeypatch, capsys):
    def missing_file(layer, bundle, config):
        raise FileNotFoundError(2, "No such file or directory", "bundle/manifest.json")
    monkeypatch.setattr(script, "register_bundle", missing_file)
    assert script.main() == 1
    failure = json.loads(capsys.readouterr().err)
    assert failure["error_type"] == "FileNotFoundError" and failure["missing_file"] == "bundle/manifest.json"
