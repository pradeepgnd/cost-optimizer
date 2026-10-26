"""M08 response-shape gate: only attributable, metered completions may be priced."""
import copy

import pytest

from app.adapters.live_nightshift import parse_completion_response


def _response():
    return {"id": "completion-123", "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4,
                      "completion_tokens_details": {"reasoning_tokens": 2}}}


def test_valid_response_preserves_raw_usage_and_response_identity():
    body = _response()
    parsed = parse_completion_response(body, {"x-request-id": "nightshift-456"})
    assert parsed["text"] == "OK" and parsed["resolved_model"] == body["model"]
    assert parsed["usage"] == body["usage"] and parsed["route_id"] == "nightshift-456"
    assert parsed["usage"]["completion_tokens"] == 4  # reasoning is part of completion
    assert parsed["usage"]["completion_tokens_details"]["reasoning_tokens"] == 2


@pytest.mark.parametrize("change", [
    lambda b: b.update(choices=[]),
    lambda b: b.update(choices=[{"message": {"content": None}}]),
    lambda b: b.update(model=None),
    lambda b: b.update(usage=None),
    lambda b: b["usage"].update(prompt_tokens=True),
    lambda b: b["usage"].update(completion_tokens=-1),
    lambda b: b["usage"].update(completion_tokens_details=[]),
    lambda b: b["usage"]["completion_tokens_details"].update(reasoning_tokens=5),
    lambda b: b.update(error={"message": "failed"}),
    lambda b: b.update(meterless=[]),
    lambda b: b.update(meterless={"winning_route": []}),
    lambda b: b.update(meterless={"receipt_id": 7}),
    lambda b: b.update(meterless={"winning_route": {"provider": None, "model": " "}}),
    lambda b: b.update(meterless={"requires_review": "yes"}),
])
def test_malformed_or_unpriced_response_is_rejected(change):
    body = copy.deepcopy(_response())
    change(body)
    with pytest.raises(ValueError):
        parse_completion_response(body, {"x-request-id": "nightshift-456"})


def test_response_request_id_is_required_and_alias_remains_visible():
    body = _response()
    body.pop("id")
    with pytest.raises(ValueError, match="request ID"):
        parse_completion_response(body, {})
    body["id"] = "generation-789"
    body["model"] = "nvidia/another-variant"
    parsed = parse_completion_response(body, {})
    assert parsed["route_id"] == "generation-789"
    assert parsed["resolved_model"] == "nvidia/another-variant"
    # The dispatcher's exact-route check will mark this unresolved until a
    # correlated provider receipt proves a documented alias mapping.


def test_nightshift_winning_route_and_receipt_override_top_level_alias():
    body = _response()
    body["model"] = "meterless/auto"
    body["meterless"] = {"receipt_id": "rcpt_req_fixture",
                         "winning_route": {"provider": "nvidia", "kind": "cloud",
                                           "model": "nemotron-3.5-lightning-30b-a3b"}}
    parsed = parse_completion_response(body, {})
    assert parsed["response_model"] == "meterless/auto"
    assert parsed["resolved_model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert parsed["receipt_id"] == "rcpt_req_fixture"
    assert parsed["provider"] == "nvidia" and parsed["provider_kind"] == "cloud"


def test_review_and_truncation_flags_are_preserved_for_dispatch():
    body = _response()
    body["choices"][0]["finish_reason"] = "length"
    body["meterless"] = {"requires_review": True}
    parsed = parse_completion_response(body, {})
    assert parsed["requires_review"] is True and parsed["finish_reason"] == "length"


@pytest.mark.parametrize("content,expected", [
    ('I should output JSON.</think>\n{"summary": "s"}', '{"summary": "s"}'),          # closing tag only (Ultra)
    ('<think>plan</think>{"a": 1}', '{"a": 1}'),
    ('a</think>b</think> final', 'final'),
    ('{"no": "tags"}', '{"no": "tags"}'),
])
def test_inline_reasoning_is_removed_from_text_but_usage_is_unchanged(content, expected):
    body = _response()
    body["choices"][0]["message"]["content"] = content
    parsed = parse_completion_response(body, {"x-request-id": "nightshift-456"})
    assert parsed["text"] == expected and parsed["usage"] == body["usage"]
