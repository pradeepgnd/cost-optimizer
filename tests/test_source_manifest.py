"""M05 offline collection/bundle regressions. Public live collection is separate evidence."""
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from app.source_contracts import RouteMap, StorageConfig
from app.source_snapshots import (SOURCE_URL, build_bundle, canonical, collect_snapshot, digest, fetch_pages,
                                  json_load, normalize_pages, validate_bundle, validate_snapshot)
from app.contracts import FounderBrief

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/source_examples/openrouter.fixture.json"
ROUTES = ROOT / "data/source_examples/routes.fixture.json"


@pytest.fixture
def snapshot(tmp_path):
    return collect_snapshot(tmp_path / "catalog", from_file=FIXTURE)[0]


def test_exact_units_unknown_zero_and_conditional_terms_are_retained():
    data = {"data": [{"id": "~unbiased/route-latest", "pricing": {"prompt": "0.000000123456789123456789", "completion": "0",
        "input_cache_read": None, "overrides": [{"min_prompt_tokens": 200000, "prompt": "0.000001"}]}}]}
    record = normalize_pages([canonical(data)])[0]
    assert record.input_usd_per_m == Decimal("0.123456789123456789") and record.output_usd_per_m == 0
    assert record.pricing["input_cache_read"] is None and record.pricing_overrides[0]["min_prompt_tokens"] == 200000
    assert not hasattr(record, "intelligence")
    numeric = normalize_pages([b'{"data":[{"id":"fixture/numeric","pricing":{"prompt":0.000000123456789123456789}}]}'])[0]
    assert numeric.input_usd_per_m == Decimal("0.123456789123456789")


@pytest.mark.parametrize("price", ["-1", "NaN", "Infinity", "not a price", True, {"wrong": "shape"}])
def test_bad_prices_cannot_be_valid_normalized_rates(price):
    with pytest.raises(ValueError):
        normalize_pages([canonical({"data": [{"id": "bad/price", "pricing": {"prompt": price}}]})])


def test_quarantine_is_explicit_and_raw_response_remains_replayable(tmp_path):
    body = json_load(FIXTURE.read_bytes())
    body["data"].append({"id": "unsupported/router", "pricing": {"prompt": "-1"}})
    raw = tmp_path / "raw.json"
    raw.write_bytes(canonical(body))
    target, manifest = collect_snapshot(tmp_path / "catalog", from_file=raw)
    assert manifest.record_count == 3 and manifest.rejected_record_count == 1 and manifest.upstream_record_count == 4
    rejected = json.loads((target / "rejected.json").read_text())
    assert rejected == [{"catalog_id": "unsupported/router", "reason": "invalid_or_unbounded_pricing", "fields": ["prompt"]}]
    assert (target / "raw/page-001.json").read_bytes() == raw.read_bytes()
    validate_snapshot(target)


@pytest.mark.parametrize("body", [{"data": []}, {"error": "bad", "data": []}, {"data": [{"id": "same"}, {"id": "same"}]},
    {"data": [{"id": "bad' UNION SELECT"}]}, {"data": [{"id": "x", "pricing": {"overrides": [1]}}]},
    {"data": [{"id": "x", "context_length": -1}]}, {"data": [1]}])
def test_malformed_or_duplicate_catalog_is_rejected(body):
    with pytest.raises(ValueError):
        normalize_pages([canonical(body)])


def test_duplicate_keys_and_nonfinite_json_are_rejected():
    for raw in ('{"data":[],"data":[]}', '{"data":NaN}'):
        with pytest.raises(ValueError):
            json_load(raw)


def test_api_pagination_is_bounded_and_snapshot_is_content_addressed(tmp_path):
    calls = []
    def handle(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(200, json={"data": [{"id": "one/a", "pricing": {"prompt": "0.000001"}}],
                                           "links": {"next": SOURCE_URL + "?offset=1&limit=1"}})
        return httpx.Response(200, json={"data": [{"id": "two/b", "pricing": {"prompt": "0"}}], "links": {"next": None}})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        target, manifest = collect_snapshot(tmp_path / "catalog", client=client)
    assert len(calls) == 2 and manifest.acquisition == "https_api" and manifest.record_count == 2
    assert validate_snapshot(target)[0] == manifest


@pytest.mark.parametrize("next_url", ["https://evil.test/models", "http://openrouter.ai/api/v1/models",
    "https://openrouter.ai/other", SOURCE_URL, "https://user:secret@openrouter.ai/api/v1/models"])
def test_pagination_never_follows_unexpected_hosts_or_cycles(next_url):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": [{"id": "one/a"}], "links": {"next": next_url}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises(ValueError):
        fetch_pages(client)
    assert len(requests) == 1


def test_partial_file_import_does_not_publish_any_snapshot(tmp_path):
    file = tmp_path / "partial.json"
    file.write_bytes(canonical({"data": [{"id": "one/a"}], "links": {"next": SOURCE_URL + "?offset=1"}}))
    with pytest.raises(ValueError, match="incomplete"):
        collect_snapshot(tmp_path / "catalog", from_file=file)
    assert not (tmp_path / "catalog").exists()


def test_same_content_reuses_snapshot_and_tampering_is_not_overwritten(snapshot):
    initial = (snapshot / "manifest.json").read_bytes()
    target, _ = collect_snapshot(snapshot.parent, from_file=FIXTURE)
    assert target == snapshot and initial == (snapshot / "manifest.json").read_bytes()
    (snapshot / "catalog.json").write_text("[]")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_snapshot(snapshot)
    with pytest.raises(ValueError):
        collect_snapshot(snapshot.parent, from_file=FIXTURE)
    assert (snapshot / "catalog.json").read_text() == "[]"


def test_manifest_path_escape_and_false_page_chain_are_rejected(snapshot):
    path = snapshot / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files"]["../private.json"] = "0" * 64
    path.write_bytes(canonical(manifest))
    with pytest.raises(ValueError, match="expected"):
        validate_snapshot(snapshot)


def test_bundle_preserves_unknown_billing_and_has_exact_route_mapping(snapshot, tmp_path):
    mapping = RouteMap.model_validate_json(ROUTES.read_text())
    brief = FounderBrief.model_validate(json.loads((ROOT / "input_examples/example_3.json").read_text())["brief"])
    target, manifest = build_bundle(snapshot, mapping, tmp_path / "bundles", [brief])
    assert manifest["counts"] == {"catalog": 3, "models": 3, "briefs": 1}
    rows = json_load((target / "models.json").read_bytes())
    for row in rows:
        payload = json_load(row["payload_json"])
        assert row["integration_test_fixture"] is True
        assert payload["market"]["list_price_input_usd_per_m"] is not None
        assert all(rate["usd_per_unit"] is None for rate in payload["rates"])
        assert payload["dispatch_policy"] is None
    assert validate_bundle(target) == manifest
    again, _ = build_bundle(snapshot, mapping, target.parent, [brief])
    assert again == target


def test_bundle_tampering_or_missing_required_model_fails(snapshot, tmp_path):
    mapping = RouteMap.model_validate_json(ROUTES.read_text())
    mapping.routes[0].catalog_id = "missing/model"
    with pytest.raises(ValueError, match="missing"):
        build_bundle(snapshot, mapping, tmp_path / "bundles")
    assert not (tmp_path / "bundles").exists()


@pytest.mark.parametrize("mutation", ["duplicate_route", "missing_tier", "unpin_open_source"])
def test_route_mapping_is_validated(mutation):
    payload = json.loads(ROUTES.read_text())
    if mutation == "duplicate_route":
        payload["routes"][1]["route_id"] = payload["routes"][0]["route_id"]
    elif mutation == "missing_tier":
        payload["routes"][0]["tier"] = None
    else:
        payload["routes"][-1]["required"] = False
    with pytest.raises(ValueError):
        RouteMap.model_validate(payload)


def test_cli_offline_collection_and_validation_do_not_need_credentials(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "scripts/collect_sources.py"), "--from-file", str(FIXTURE),
        "--output-dir", str(tmp_path / "catalog")], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["acquisition"] == "file_import" and report["records"] == 3
    result = subprocess.run([sys.executable, str(ROOT / "scripts/collect_sources.py"), "--validate", report["snapshot_dir"]],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0


@pytest.mark.parametrize("updates", [{"publisher_endpoint": "http://remote.test:4566"},
    {"zetaris_endpoint": 'http://host\"inject:4566'}, {"prefix": "../escape"},
    {"backend": "aws"}, {"namespace": "foo; DROP DATABASE x"}])
def test_public_storage_config_cannot_embed_credentials_sql_or_remote_test_credentials(updates):
    payload = json.loads((ROOT / "data/source_examples/localstack.json").read_text())
    with pytest.raises(ValueError):
        StorageConfig.model_validate({**payload, **updates})


def test_selected_route_map_keeps_nemotron_as_the_required_open_route():
    mapping = RouteMap.model_validate_json((ROOT / "data/source_examples/routes.selected.json").read_text())
    tiers = {route.tier: route for route in mapping.routes}
    assert tiers["open_source"].required and tiers["open_source"].route_id.startswith("nvidia/nemotron")
    assert tiers["frontier"].label and not tiers["frontier"].required


def test_unset_route_label_is_omitted_so_existing_bundle_ids_do_not_change():
    mapping = RouteMap.model_validate_json(ROUTES.read_text())
    assert all("label" not in route for route in mapping.model_dump(mode="json")["routes"])
