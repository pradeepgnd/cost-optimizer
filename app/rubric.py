"""Deterministic rubric checks. These and human review decide pass/fail; no model ever does.

Checks run on live outputs only. In sample mode there are no outputs, so nothing here runs and
switch points stay pending.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from app.contracts import FeatureProfile, HumanReview, RubricCheck, RubricResult

_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*\n(.*?)\n\s*```\s*$", re.S)


def parse_json_object(text: str) -> Optional[dict]:
    """A JSON object from model text, tolerating one surrounding code fence. None if it is not an object."""
    m = _FENCE.match(text)
    body = m.group(1) if m else text
    try:
        obj = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def _target(check: RubricCheck, text: str) -> Optional[str]:
    """The text a check applies to: the whole output, or one field of a JSON output (None if absent)."""
    field = check.params.get("json_field")
    if field is None:
        return text
    obj = parse_json_object(text)
    if obj is None or field not in obj:
        return None
    v = obj[field]
    return v if isinstance(v, str) else json.dumps(v)


def run_check(check: RubricCheck, text: str) -> Optional[bool]:
    """Machine result for one check on one output; None for human_review (no machine result)."""
    p = check.params
    if check.kind == "human_review":
        return None
    if check.kind == "required_json_fields":
        obj = parse_json_object(text)
        return obj is not None and all(f in obj and obj[f] not in (None, "", [], {}) for f in p["fields"])
    target = _target(check, text)
    if target is None:
        return False
    if check.kind == "max_words":
        return len(target.split()) <= p["limit"]
    if check.kind == "forbidden_terms":
        low = target.lower()
        return not any(t.lower() in low for t in p["terms"])
    if check.kind == "regex":
        found = re.search(p["pattern"], target, re.I if p.get("ignore_case") else 0) is not None
        return found if p.get("must_match", True) else not found
    raise ValueError(f"unknown check kind {check.kind}")


def evaluate(feature: FeatureProfile, model_id: str, outputs: list[str],
             reviews: Optional[list[HumanReview]] = None, truncated: Optional[list[bool]] = None) -> RubricResult:
    """A machine check passes only if it passes on every sample, and fails if any sample was cut at the token cap
    (an incomplete answer). A human review overrides the machine result; a human_review check without a review
    stays pending."""
    machine: dict[str, bool] = {}
    cut = any(truncated or [])
    for c in feature.rubric_checks:
        results = [run_check(c, o) for o in outputs]
        if outputs and all(r is not None for r in results):
            machine[c.check_id] = all(results) and not cut
    ids = {c.check_id for c in feature.rubric_checks}
    overrides = {r.check_id: r.passed for r in (reviews or [])
                 if r.feature_id == feature.feature_id and r.model_id == model_id and r.check_id in ids}
    checks = {**machine, **overrides}
    pending = [c.check_id for c in feature.rubric_checks if c.check_id not in checks]
    return RubricResult(feature_id=feature.feature_id, model_id=model_id, checks=checks, machine=machine,
                        overrides=overrides, pending=pending, execution_kind="live_inference")


def json_fields_requested(feature: FeatureProfile) -> list[str]:
    """Fields the feature's checks expect in a JSON output, so the prompt can ask for them."""
    fields: list[str] = []
    for c in feature.rubric_checks:
        fields += c.params.get("fields", []) if c.kind == "required_json_fields" else []
        if c.params.get("json_field"):
            fields.append(c.params["json_field"])
    return list(dict.fromkeys(fields))
