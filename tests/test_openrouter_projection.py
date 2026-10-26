from decimal import Decimal

import pytest

from app.contracts import (EvidenceStatus, FeatureProfile, MarketReference, ModelProfile, Rate, RateCategory,
                           SourceRef, Stage, TokenUsage)
from app.economics import openrouter_projection_table, stage_cost_row
from app.source_contracts import CatalogModel


def _inputs(output_price="2.40"):
    source = SourceRef(source_set="catalog", record_id="nvidia/nemotron-3-ultra-550b-a55b",
                       version="snapshot-1", snapshot_id="snapshot-1", status=EvidenceStatus.verified,
                       origin_url="https://openrouter.ai/api/v1/models", verified_at="2026-10-25T22:27:42Z")
    unavailable = SourceRef(source_set="pricing_snapshots", record_id="nightshift-route", version="snapshot-1",
                            status=EvidenceStatus.unknown)
    model = ModelProfile(model_id="nvidia/nemotron-3-ultra-550b-a55b", provider_label="unverified route",
                         tier="frontier", source=unavailable,
                         market=MarketReference(catalog_id=source.record_id, snapshot_date="2026-10-25"),
                         rates=[Rate(category=cat, unit="1M tokens", usd_per_unit=None,
                                     status=EvidenceStatus.unknown, source=unavailable)
                                for cat in (RateCategory.input_tokens, RateCategory.output_tokens)])
    catalog = CatalogModel(catalog_id=source.record_id, name="Nemotron 3 Ultra", input_usd_per_m=Decimal("0.60"),
                           output_usd_per_m=None if output_price is None else Decimal(output_price))
    feature = FeatureProfile(feature_id="plan", description="make a plan", example_input="example", mode="interactive",
                             uses_per_user_month=Decimal("10"), calls_per_use=Decimal("1"),
                             expected_output_words=100)
    usage = TokenUsage(input_tokens=1000, output_tokens=100, reasoning_tokens=20, basis="measured", method="API usage")
    stage = Stage(name="Pilot", active_users=100)
    return source, model, catalog, feature, usage, stage


def test_openrouter_projection_uses_pinned_catalog_without_promoting_nightshift_rates():
    source, model, catalog, feature, usage, stage = _inputs()
    actual = stage_cost_row(feature, model, stage, usage)
    table = openrouter_projection_table(feature, [(model, catalog, source)], {model.model_id: usage}, [stage])
    row = table.rows[0]

    assert actual.monthly_with_levers_usd is None
    assert row.model_id == "openrouter/nvidia/nemotron-3-ultra-550b-a55b"
    assert row.monthly_with_levers_usd == Decimal("0.92")  # 1000 calls × (1000×0.60 + 100×2.40)/1M × 1.1
    assert row.token_basis == "measured" and row.lower_bound
    assert table.sources == [source] and table.pricing_scope == "openrouter_listed_token_scenario"
    assert model.rates[0].usd_per_unit is None and model.dispatch_policy is None


def test_openrouter_projection_preserves_unknown_price_and_rejects_wrong_mapping():
    source, model, catalog, feature, usage, stage = _inputs(output_price=None)
    table = openrouter_projection_table(feature, [(model, catalog, source)], {model.model_id: usage}, [stage])
    assert table.rows[0].monthly_with_levers_usd is None
    assert any("unknown" in warning.lower() for warning in table.rows[0].warnings)

    other = catalog.model_copy(update={"catalog_id": "another/model"})
    with pytest.raises(ValueError, match="mapping mismatch"):
        openrouter_projection_table(feature, [(model, other, source)], {model.model_id: usage}, [stage])
