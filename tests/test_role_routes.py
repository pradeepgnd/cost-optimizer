"""R1: the Planner and Critic routes carry curated, verified billing profiles; candidates need not."""
from decimal import Decimal
import json
from pathlib import Path

import pytest

from app.contracts import RateCategory
from app.dispatch import MAX_OUTPUT_TOKENS, StopRun, request_bound
from app.source_contracts import RouteMap

ROUTES = Path(__file__).resolve().parents[1] / "data" / "source_examples" / "routes.selected.json"
ROLE_ROUTES = {"nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3-ultra-550b-a55b"}


def _routes():
    return {r.route_id: r for r in RouteMap.model_validate(json.loads(ROUTES.read_text())).routes}


@pytest.mark.parametrize("route", sorted(ROLE_ROUTES))
def test_role_route_profile_passes_dispatch_gate(route):
    profile = _routes()[route].billing_profile
    bound, reserved, input_rate, output_rate, sources = request_bound(profile, "system", "user", MAX_OUTPUT_TOKENS)
    assert bound > 0 and reserved == Decimal("0")
    assert input_rate == output_rate == Decimal("0")
    assert profile.dispatch_policy.completion_limit_includes_reasoning is True
    assert all(s.origin_url.startswith("https://") and s.verified_at for s in sources)


@pytest.mark.parametrize("route", sorted(ROLE_ROUTES))
def test_role_route_rates_are_explicit_and_not_catalog_copies(route):
    profile = _routes()[route].billing_profile
    by_category = {rate.category: rate for rate in profile.rates}
    assert set(by_category) == {RateCategory.input_tokens, RateCategory.output_tokens}
    assert "free Developer Program" in profile.provider_label and "prototyping only" in profile.provider_label


def test_oversized_prompt_and_output_are_still_refused():
    profile = _routes()["nvidia/nemotron-3-ultra-550b-a55b"].billing_profile
    with pytest.raises(StopRun):
        request_bound(profile, "x" * (profile.dispatch_policy.max_prompt_bytes + 1), "", 8)
    with pytest.raises(StopRun):
        request_bound(profile, "", "", MAX_OUTPUT_TOKENS + 1)


def test_only_the_role_routes_carry_curated_profiles_and_none_is_pinned():
    routes = _routes()
    assert {rid for rid, r in routes.items() if r.billing_profile is not None} == ROLE_ROUTES
    assert not any(r.required for r in routes.values())
