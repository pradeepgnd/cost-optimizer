import json
import uuid

import httpx
import pytest

from scripts.check_zetaris import verify_connection


def configure(monkeypatch, tmp_path, handler):
    monkeypatch.setenv("ZETARIS_REST_URL", "http://zetaris.test/api/v1.0")
    monkeypatch.setenv("ZETARIS_ORG_ID", "7")
    monkeypatch.setenv("ZETARIS_API_KEY", "test-private-credential")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(
        transport=httpx.MockTransport(handler), **kwargs))


def test_connection_uses_verified_contract_and_keeps_credential_out_of_artifacts(monkeypatch, tmp_path):
    def handler(request):
        assert str(request.url) == "http://zetaris.test/api/v1.0/sql-editor/sqls/run"
        assert request.headers["Authorization"] == "Bearer test-private-credential"
        assert request.headers["X-Org-ID"] == "7"
        uuid.UUID(request.headers["X-Request-ID"])
        body = json.loads(request.content)
        uuid.UUID(body["queryId"])
        assert body["source"] == "SqlEditor" and body["sql"] == "SELECT 1 AS one" and body["limit"] == 1
        return httpx.Response(200, json={"headers": ["one"], "data": [["1"]], "total": 1})

    configure(monkeypatch, tmp_path, handler)
    report, exit_code = verify_connection()
    assert exit_code == 0 and report["status"] == "passed"
    artifacts = json.dumps(report) + "".join(p.read_text() for p in (tmp_path / "logs").iterdir())
    assert "test-private-credential" not in artifacts


@pytest.mark.parametrize("body", [{"data": []}, {"data": [["0"]]}, {"error": "SQL failed"}])
def test_http_success_without_expected_sql_result_fails(monkeypatch, tmp_path, body):
    configure(monkeypatch, tmp_path, lambda request: httpx.Response(200, json=body))
    report, exit_code = verify_connection()
    assert exit_code == 3 and report["code"] == "UNEXPECTED_SQL_RESULT"


def test_authentication_error_does_not_echo_server_body(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, lambda request: httpx.Response(401, text="test-private-credential"))
    report, exit_code = verify_connection()
    assert exit_code == 3 and report["http_status"] == 401
    assert "test-private-credential" not in json.dumps(report)
