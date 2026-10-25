import json

import pytest

from app.contracts import FeatureProfile, HumanReview, RubricCheck
from app.rubric import evaluate, json_fields_requested, parse_json_object, run_check

def _c(kind, critical=True, cid=None, **params):
    return RubricCheck(check_id=cid or kind, description=kind, kind=kind, params=params, critical=critical)

def test_max_words_whole_output_and_json_field():
    assert run_check(_c("max_words", limit=3), "one two three")
    assert not run_check(_c("max_words", limit=3), "one two three four")
    c = _c("max_words", limit=4, json_field="target_sentence")
    assert run_check(c, json.dumps({"target_sentence": "I want red ball.", "feedback": "Great try, well done today!"}))
    assert not run_check(c, json.dumps({"target_sentence": "I want the big red ball now."}))
    assert not run_check(c, "not json at all")                  # field absent -> fail, never pass

def test_required_json_fields_tolerates_one_code_fence_and_rejects_empty():
    c = _c("required_json_fields", fields=["service", "quantity"])
    assert run_check(c, '```json\n{"service": "geocoding", "quantity": 200}\n```')
    assert not run_check(c, '{"service": "geocoding"}')
    assert not run_check(c, '{"service": "", "quantity": 200}')
    assert not run_check(c, "[1, 2]") and parse_json_object("[1, 2]") is None

def test_forbidden_terms_case_insensitive():
    c = _c("forbidden_terms", terms=["diagnosis"])
    assert not run_check(c, "This is not a Diagnosis.") and run_check(c, "Great job saying ball!")

def test_regex_must_match_and_must_not_match():
    assert run_check(_c("regex", pattern=r"^\s*200\s*$", json_field="quantity"), '{"quantity": 200}')
    assert not run_check(_c("regex", pattern=r"^\s*200\s*$", json_field="quantity"), '{"quantity": 20}')
    assert run_check(_c("regex", pattern="guarantee", must_match=False, ignore_case=True), "No promises here.")

def test_params_must_fit_kind():
    for kind, params in (("max_words", {}), ("required_json_fields", {"fields": []}), ("forbidden_terms", {"terms": [""]}),
                         ("regex", {"pattern": "("})):
        with pytest.raises(ValueError):
            RubricCheck(check_id="x", description="x", kind=kind, params=params)

def _feature():
    return FeatureProfile(feature_id="f", description="d", example_input="i", mode="interactive",
                          rubric_checks=[_c("required_json_fields", cid="shape", fields=["answer"]),
                                         _c("max_words", cid="short", limit=3, json_field="answer"),
                                         _c("human_review", cid="tone", critical=False)])

def test_check_passes_only_if_it_passes_on_every_sample():
    r = evaluate(_feature(), "m", ['{"answer": "yes it is"}', '{"answer": "no, it is not true"}'])
    assert r.machine == {"shape": True, "short": False} and r.pending == ["tone"]
    assert r.execution_kind == "live_inference"

def test_human_review_overrides_machine_and_resolves_pending():
    reviews = [HumanReview(feature_id="f", model_id="m", check_id="short", passed=True, reviewer="r", note="field counted wrongly"),
               HumanReview(feature_id="f", model_id="m", check_id="tone", passed=False, reviewer="r"),
               HumanReview(feature_id="f", model_id="other", check_id="shape", passed=False, reviewer="r")]
    r = evaluate(_feature(), "m", ['{"answer": "no, it is not true"}'], reviews)
    assert r.machine["short"] is False and r.checks["short"] is True
    assert r.checks["tone"] is False and r.pending == [] and r.checks["shape"] is True

def test_no_outputs_means_no_machine_results():
    r = evaluate(_feature(), "m", [])
    assert r.machine == {} and r.pending == ["shape", "short", "tone"]

def test_prompt_fields_come_from_checks():
    assert json_fields_requested(_feature()) == ["answer"]
