"""R3a: candidates are chosen per feature from the offered, priced routes that cover the modality; nothing is pinned."""
from decimal import Decimal

import pytest

from app.adapters.sample import SampleDataLayer
from app.contracts import FeatureProfile, MarketReference
from app.controller import CANDIDATE_TIERS, Controller
from app.dispatch import StopRun


class _Trace:
    def event(self, *args, **kwargs):
        pass


def _ctl(open_model=""):
    c = Controller.__new__(Controller)
    c.trace, c.open_model, c.limitations, c.feature_candidates = _Trace(), open_model, [], {}
    return c


def _model(mid, price, *, inp=("text",), out=("text",), open_weights=False, tier=None, score=None, rank=None):
    base = SampleDataLayer().read_models()[0]
    market = MarketReference(snapshot_date="2026-10-25", list_price_input_usd_per_m=Decimal(price),
                             list_price_output_usd_per_m=Decimal(price), usage_rank=rank,
                             input_modalities=None if inp is None else list(inp),
                             output_modalities=None if out is None else list(out),
                             open_weights_signal=open_weights if inp is not None else None)
    intelligence = None if score is None else base.intelligence.model_copy(update={"score": Decimal(score)})
    return base.model_copy(update={"model_id": mid, "tier": tier, "required": False, "market": market,
                                   "intelligence": intelligence})


def _feature(fid, modality):
    return FeatureProfile(feature_id=fid, description="d", example_input="x", mode="interactive", modality=modality)


VISION = ("image", "text")
POOL = [_model("lab/big-text", 20), _model("lab/small-text", 1), _model("lab/big-vision", 25, inp=VISION),
        _model("lab/small-vision", 2, inp=VISION), _model("lab/open-text", 3, open_weights=True),
        _model("lab/open-vision", 4, inp=VISION, open_weights=True)]


def _choose(features, models=POOL, routes=None, tiers=CANDIDATE_TIERS, open_model=""):
    c = _ctl(open_model)
    union, shortlist = c._candidates(models, routes, tiers, features)
    return c, union, shortlist


def _ids(c, fid):
    return [m.model_id for m in c.feature_candidates[fid]]


def test_text_feature_may_use_any_priced_model_from_any_lab():
    c, _, _ = _choose([_feature("t", ["text"])])
    assert set(_ids(c, "t")) <= {m.model_id for m in POOL} and len(_ids(c, "t")) == 3


def test_image_input_feature_only_gets_vision_models():
    c, _, shortlist = _choose([_feature("v", ["image_in", "text"])])
    assert _ids(c, "v") and all("vision" in i for i in _ids(c, "v"))
    text_only = next(e for e in shortlist if e.model_id == "lab/big-text")
    assert not text_only.selected and "no support for image_in" in text_only.reason


def test_mixed_features_get_different_candidate_sets_from_the_same_pool():
    c, union, shortlist = _choose([_feature("t", ["text"]), _feature("v", ["image_in", "text"])])
    assert _ids(c, "t") != _ids(c, "v")
    assert {m.model_id for m in union} == set(_ids(c, "t")) | set(_ids(c, "v"))
    entry = next(e for e in shortlist if e.model_id == _ids(c, "v")[0])
    assert "v" in entry.selected_for


def test_feature_with_no_capable_model_gets_no_candidates_and_says_so():
    c, _, _ = _choose([_feature("a", ["audio_in", "text"])])
    assert c.feature_candidates["a"] == [] and any("No candidate route covers a" in l for l in c.limitations)


def test_unknown_catalog_modalities_are_kept_but_labeled_not_assumed():
    models = [_model("lab/unknown", 5, inp=None, out=None)]
    c, _, shortlist = _choose([_feature("v", ["image_in", "text"])], models)
    assert _ids(c, "v") == ["lab/unknown"]
    assert "unknown in the catalog reference" in shortlist[0].reason


def test_unpriced_router_and_non_nightshift_routes_are_never_chosen():
    bare = _model("lab/unpriced", 1).model_copy(update={"market": MarketReference(snapshot_date="2026-10-25")})
    models = [bare, _model("meterless/auto", 1), _model("lab/offline", 9), _model("lab/ok", 5)]
    c, _, shortlist = _choose([_feature("t", ["text"])], models, routes={"lab/unpriced", "meterless/auto", "lab/ok"})
    assert _ids(c, "t") == ["lab/ok"]
    reasons = {e.model_id: e.reason for e in shortlist}
    assert "no reference price" in reasons["lab/unpriced"] and "router alias" in reasons["meterless/auto"]
    assert "not a Nightshift route" in reasons["lab/offline"]


def test_tiers_are_derived_by_rule_and_nothing_is_pinned():
    c, _, shortlist = _choose([_feature("t", ["text"])])
    by_tier = {m.tier or "": m.model_id for m in c.feature_candidates["t"]}
    chosen = {e.model_id: e.tier for e in shortlist if e.selected}
    assert chosen["lab/big-text"] == "frontier" or chosen["lab/big-vision"] == "frontier"
    assert any(t == "open_source" for t in chosen.values()) and "lab/open-text" in chosen or "lab/open-vision" in chosen
    assert all(e.reason for e in shortlist)


def test_a_higher_ranked_open_model_wins_without_a_pin_and_the_override_forces_one():
    models = [_model("lab/open-a", 3, open_weights=True, score="90"), _model("lab/open-b", 3, open_weights=True, score="10"),
              _model("lab/closed", 9)]
    c, _, _ = _choose([_feature("t", ["text"])], models)
    assert "lab/open-a" in _ids(c, "t")
    c2, _, shortlist = _choose([_feature("t", ["text"])], models, open_model="lab/open-b")
    assert "lab/open-b" in _ids(c2, "t") and "lab/open-a" not in _ids(c2, "t")
    assert "founder override" in next(e for e in shortlist if e.model_id == "lab/open-b").reason


def test_override_that_is_unknown_or_not_offered_stops_before_any_call():
    with pytest.raises(StopRun):
        _choose([_feature("t", ["text"])], open_model="lab/missing")
    with pytest.raises(StopRun):
        _choose([_feature("t", ["text"])], routes={"lab/big-text"}, open_model="lab/open-text")


def test_validation_subset_honors_requested_tiers():
    c, _, shortlist = _choose([_feature("t", ["text"])], tiers=("frontier", "mid_tier"))
    assert all(m.model_id not in {"lab/open-text", "lab/open-vision"} for m in c.feature_candidates["t"])
    assert any("omitted from this validation comparison" in e.reason for e in shortlist)


def test_a_verified_dispatch_policy_ranks_first_within_its_tier():
    from tests.test_role_routes import ROLE_ROUTES, _routes
    verified = _routes()["nvidia/nemotron-3-ultra-550b-a55b"].billing_profile.model_copy(
        update={"tier": None, "market": MarketReference(snapshot_date="2026-10-25", list_price_input_usd_per_m=Decimal("1"),
                                                        list_price_output_usd_per_m=Decimal("1"), open_weights_signal=True,
                                                        input_modalities=["text"], output_modalities=["text"])})
    models = [_model("lab/popular-open", 1, open_weights=True, score="99", rank=1), verified]
    c, _, shortlist = _choose([_feature("t", ["text"])], models)
    assert _ids(c, "t") == [verified.model_id]
    assert "verified rate and dispatch policy" in next(e for e in shortlist if e.selected).reason
