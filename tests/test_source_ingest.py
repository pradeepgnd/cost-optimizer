"""Loopback ingestion protocol and outbox retry tests without listening sockets or model calls."""
from io import BytesIO
import json
from types import SimpleNamespace

import pytest

from app.contracts import SourceRef, EvidenceStatus
from app.dispatch import Checkpoints
from app.source_contracts import SourceBindings
from app.source_snapshots import canonical, digest
from scripts.serve_source_ingest import ingest_handler
from tests.test_zetaris_adapter import bundle


@pytest.mark.parametrize("authorization,length,outcome,expected", [
    (None,None,None,401), ("Bearer wrong",None,None,401), ("Bearer fixture-token",None,None,200),
    ("Bearer fixture-token",2*1024*1024,None,413), ("Bearer fixture-token",None,ValueError("conflict secret-value"),409),
    ("Bearer fixture-token",None,OSError("private storage secret-value"),503)])
def test_ingest_protocol_auth_size_conflicts_and_redacted_errors(authorization,length,outcome,expected):
    calls = []
    def write(record):
        calls.append(record)
        if outcome:
            raise outcome
        return SourceRef(source_set="evaluation_evidence",record_id=record["id"],version="fixture",status=EvidenceStatus.unverified)
    handler_type = ingest_handler(SimpleNamespace(write=write),"fixture-token")
    handler = handler_type.__new__(handler_type)
    record = {"id": "fixture/sample","run_id": "fixture","kind": "integration_test_fixture","payload": {}}
    raw = canonical(record)
    handler.path, handler.rfile, handler.wfile = "/evidence", BytesIO(raw), BytesIO()
    handler.headers = {"Content-Length": str(length or len(raw))}
    if authorization:
        handler.headers["Authorization"] = authorization
    statuses=[]
    handler.send_response = lambda status: statuses.append(status)
    handler.send_error = lambda status: statuses.append(status)
    handler.send_header = lambda *a: None
    handler.end_headers = lambda: None
    handler.do_POST()
    assert statuses == [expected]
    assert b"secret-value" not in handler.wfile.getvalue() and b"fixture-token" not in handler.wfile.getvalue()
    if expected in {401,413}:
        assert calls == []


def test_retry_outbox_only_publishes_evidence_and_never_redispatches_models(tmp_path,monkeypatch,bundle,capsys):
    import scripts.retry_evidence as script
    from tests.test_zetaris_adapter import layer
    from app.adapters.live_nightshift import NightshiftInference
    monkeypatch.setattr(NightshiftInference,"complete",lambda **kwargs: pytest.fail("outbox retry generated a model response"))
    bindings = tmp_path / "bindings.json"
    bindings.write_text(bundle[2].model_dump_json())
    database = tmp_path / "runs.db"
    store = Checkpoints(str(database))
    store.claim("fixture")
    record = {"id": "fixture/result","run_id": "fixture","kind": "integration_test_fixture","payload": {"x": 1}}
    store.stage_evidence("fixture",record)
    calls = []
    sha = digest(canonical(record))
    ref = SourceRef(source_set="evaluation_evidence",record_id=record["id"],version=sha,content_sha256=sha,status=EvidenceStatus.unverified)
    class FakeLayer:
        client = SimpleNamespace(close=lambda: None)
        def __init__(self,**kwargs):
            pass
        def write_evidence(self,item):
            calls.append(item)
            return ref
        def read_evidence(self,rid):
            return record,ref
    monkeypatch.setattr(script,"ZetarisDataLayer",FakeLayer)
    monkeypatch.setattr("sys.argv",["retry_evidence.py","--runs-db",str(database),"--run-id","fixture","--bindings",str(bindings),"--no-dotenv"])
    assert script.main() == 0
    assert calls == [record] and store.pending_evidence("fixture") == []
    assert store.operations("fixture") == []
    assert json.loads(capsys.readouterr().out)["model_completions"] == 0
    assert script.main() == 0 and calls == [record]


def test_manual_fixture_staging_uses_new_db_and_no_private_setup(tmp_path,monkeypatch,capsys):
    import scripts.retry_evidence as script
    db = tmp_path / "fixture.db"
    monkeypatch.setattr("sys.argv",["retry_evidence.py","--runs-db",str(db),"--run-id","fixture","--stage-test-fixture"])
    assert script.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "pending" and report["model_completions"] == 0
    store = Checkpoints(str(db))
    assert len(store.pending_evidence("fixture")) == 1 and store.operations("fixture") == []
    with pytest.raises(SystemExit):
        script.main()
