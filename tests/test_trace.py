"""Offline trace/HTTP regressions: no sponsor runtime or model calls."""
import json

import httpx
import pytest

from app.trace import Trace, _mask


def events(trace):
    return [json.loads(line) for line in trace.path.read_text().splitlines()]


def test_numeric_usage_and_nested_details_survive_while_secrets_are_masked():
    usage = {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19,
             "completion_tokens_details": {"reasoning_tokens": 3, "api_key": "private"},
             "prompt_tokens_details": {"cached_tokens": 4}}
    masked = _mask({"usage": usage, "runtime_token": "private", "Authorization": "Bearer private",
                    "nested": [{"apiKey": "private", "password": "private"}], "max_tokens": 8})
    assert masked["usage"]["completion_tokens_details"] == {"reasoning_tokens": 3, "api_key": "...redacted"}
    assert masked["usage"]["prompt_tokens_details"] == {"cached_tokens": 4}
    assert masked["usage"]["prompt_tokens"] == 12 and masked["usage"]["completion_tokens"] == 7
    assert masked["usage"]["total_tokens"] == 19 and masked["max_tokens"] == 8
    assert "private" not in json.dumps(masked)


@pytest.mark.parametrize("value", ["credential", True, -1, {"runtime_token": "private"}])
def test_token_count_names_do_not_exempt_credentials(value):
    assert _mask({"prompt_tokens": value})["prompt_tokens"] == "...redacted"


def test_trace_redacts_file_stderr_and_final_without_losing_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "short-secret-value")
    trace = Trace("trace-fixture", "live", str(tmp_path))
    digest = "a" * 64
    model = "provider/" + "long-model-name-" * 4
    trace.event("Analyst", "request", model=model, requested_model=model, operation_id="request-123",
                output_summary="short-secret-value Authorization=abc runtime_token=xyz Bearer bearer-secret",
                extra={"usage": {"prompt_tokens": 20, "completion_tokens_details": {"reasoning_tokens": 2}},
                       "adapter_revision": digest})
    trace.final({"secret": "private", "detail": "short-secret-value"})
    captured = capsys.readouterr()
    combined = trace.path.read_text() + captured.err + captured.out
    assert all(secret not in combined for secret in ("short-secret-value", "abc", "xyz", "bearer-secret", "private"))
    row = events(trace)[0]
    assert row["model"] == model and row["extra"]["adapter_revision"] == digest
    assert row["extra"]["usage"]["completion_tokens_details"]["reasoning_tokens"] == 2
    assert row["operation_id"] == "request-123" and "confidence" not in row


def test_secret_redaction_precedes_summary_truncation(tmp_path, monkeypatch):
    secret = "sensitive-" * 20
    monkeypatch.setenv("RUNTIME_TOKEN", secret)
    trace = Trace("truncate", "live", str(tmp_path), echo=False)
    trace.event("Analyst", "request", output_summary="x" * 480 + secret)
    assert events(trace)[0]["output_summary"] == "x" * 480 + "...redacted"


@pytest.fixture
def live_env(monkeypatch):
    for key, value in {"METERLESS_BASE_URL": "https://runtime.test/v1", "METERLESS_RUNTIME_TOKEN": "fixture-secret",
                       "ZETARIS_REST_URL": "https://zetaris.test/api", "ZETARIS_ORG_ID": "1",
                       "ZETARIS_API_KEY": "fixture-key"}.items():
        monkeypatch.setenv(key, value)


def assert_pair(trace, action, status):
    attempt, terminal = events(trace)
    assert attempt["action"] == action + "_attempt" and attempt["status"] == "pending"
    assert terminal["action"] == action and terminal["status"] == status
    assert attempt["operation_id"] == terminal["operation_id"] and terminal["operation_id"]
    assert terminal["extra"]["elapsed_s"] >= 0
    for key in ("adapter_revision", "configuration_ref"):
        assert len(terminal["extra"][key]) == 64 and terminal["extra"][key] == attempt["extra"][key]
    return attempt, terminal


@pytest.mark.parametrize("outcome", ["success", "http_error", "timeout", "invalid_json", "invalid_body"])
def test_nightshift_attempt_and_terminal_include_failure_evidence(tmp_path, monkeypatch, live_env, outcome):
    import app.adapters.live_nightshift as module
    trace = Trace("nightshift", "live", str(tmp_path), echo=False)

    def handle(request):
        assert events(trace)[0]["status"] == "pending"
        assert request.headers["X-Request-ID"] == events(trace)[0]["operation_id"]
        if outcome == "timeout":
            raise httpx.ReadTimeout("timed out with fixture-secret", request=request)
        if outcome == "http_error":
            return httpx.Response(401, json={"error": "denied"}, headers={"x-request-id": "runtime-request"})
        if outcome == "invalid_json":
            return httpx.Response(200, content="not JSON", headers={"x-request-id": "runtime-request"})
        body = {"id": "completion-id", "model": "nvidia/nemotron-fixture", "usage": {
            "prompt_tokens": 12, "completion_tokens": 4, "completion_tokens_details": {"reasoning_tokens": 2}}}
        if outcome == "success":
            body["choices"] = [{"message": {"content": "OK"}}]
        return httpx.Response(200, json=body, headers={"x-request-id": "runtime-request"})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(module.httpx, "post", client.post)
        adapter = module.NightshiftInference(trace)
        with adapter.dispatch_context("synthetic-fixture-operation"):
            if outcome == "success":
                result = adapter.complete(role="Analyst", model="route/alias", system="check", user="check", max_tokens=8)
                assert result["text"] == "OK" and result["route_id"] == "runtime-request"
            else:
                with pytest.raises((httpx.HTTPError, ValueError, KeyError)):
                    adapter.complete(role="Analyst", model="route/alias", system="check", user="check", max_tokens=8)
    _, terminal = assert_pair(trace, "nightshift_request", "success" if outcome == "success" else "error")
    assert terminal["requested_model"] == "route/alias"
    if outcome in {"success", "invalid_body"}:
        assert terminal["model"] == "nvidia/nemotron-fixture"
        assert terminal["extra"]["usage"]["completion_tokens_details"]["reasoning_tokens"] == 2
    assert "fixture-secret" not in trace.path.read_text()


@pytest.mark.parametrize("body,valid", [({"data": [{"id": "route/a"}]}, True), ({"data": []}, False),
    ({"data": [{"id": ""}]}, False), ({"data": [{"id": 5}]}, False), ({"data": ["route/a"]}, False),
    ({"data": [{"id": "a"}, {"id": "a"}]}, False), ({"models": []}, False),
    ({"data": [{"id": "a"}], "error": "denied"}, False), ([], False)])
def test_discovery_validates_structure_and_logs_parse_failures(tmp_path, monkeypatch, live_env, body, valid):
    import app.adapters.live_nightshift as module
    trace = Trace("discovery", "live", str(tmp_path), echo=False)
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))) as client:
        monkeypatch.setattr(module.httpx, "get", client.get)
        adapter = module.NightshiftInference(trace)
        if valid:
            assert adapter.list_models() == ["route/a"]
        else:
            with pytest.raises(ValueError):
                adapter.list_models()
    assert_pair(trace, "nightshift_models", "success" if valid else "error")


@pytest.mark.parametrize("outcome", ["success", "http_error", "timeout", "invalid_json", "wrong_cell", "sql_error"])
def test_zetaris_attempt_and_terminal_validate_sql_and_keep_query_id(tmp_path, monkeypatch, live_env, outcome):
    from app.adapters.live_zetaris import ZetarisDataLayer
    trace = Trace("zetaris", "live", str(tmp_path), echo=False)

    def handle(request):
        attempt = events(trace)[0]
        assert attempt["status"] == "pending"
        assert request.headers["X-Request-ID"] == attempt["query_id"] == attempt["operation_id"]
        assert json.loads(request.content)["queryId"] == attempt["query_id"]
        if outcome == "timeout":
            raise httpx.ReadTimeout("fixture-key", request=request)
        if outcome == "http_error":
            return httpx.Response(403)
        if outcome == "invalid_json":
            return httpx.Response(200, content="not JSON")
        body = {"rows": [[1 if outcome == "success" else 2]]}
        if outcome == "sql_error":
            body["error"] = "failed"
        return httpx.Response(200, json=body, headers={"x-request-id": "server-query"})

    adapter = ZetarisDataLayer(trace)
    adapter.client.close()
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        adapter.client = client
        if outcome == "success":
            assert adapter.select_one() == {"rows": [[1]]}
        else:
            with pytest.raises((httpx.HTTPError, ValueError)):
                adapter.select_one()
    attempt, terminal = assert_pair(trace, "zetaris_query", "success" if outcome == "success" else "error")
    assert terminal["query_id"] == attempt["query_id"]
    assert "fixture-key" not in trace.path.read_text()
