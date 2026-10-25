"""Bounded catalog collection, hash validation and explicit application source bundles."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlparse, urljoin

import httpx

from app.contracts import (EvidenceStatus, FounderBrief, MarketReference, ModelProfile, Rate, RateCategory, SourceRef)
from app.source_contracts import CatalogModel, RecordEnvelope, RouteMap, SOURCE_URL, SourceManifest

MAX_BYTES = 16 * 1024 * 1024
MAX_RECORDS = 20_000
MAX_PAGES = 20


def canonical(value) -> bytes:
    def exact(item):
        if isinstance(item, Decimal):
            return str(item)
        raise TypeError("unsupported JSON value")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=exact).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def json_load(raw, *, exact=False):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, parse_float=Decimal if exact else float, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite JSON number")))


def token_price(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("invalid catalog price")
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("invalid catalog price") from error
    if not number.is_finite() or number < 0:
        raise ValueError("catalog prices must be finite and non-negative")
    return number


def normalize_pages(pages: list[bytes], *, rejected=None) -> list[CatalogModel]:
    found, seen = [], set()
    for raw in pages:
        body = json_load(raw, exact=True)
        if not isinstance(body, dict) or body.get("error") or not isinstance(body.get("data"), list):
            raise ValueError("catalog response must contain a data list without errors")
        for entry in body["data"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("pricing", {}), dict):
                raise ValueError("invalid catalog record/pricing")
            cid = entry.get("id")
            if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9~][A-Za-z0-9._:/~@+-]{0,255}", cid) or cid in seen:
                from app.trace import _mask
                raise ValueError(f"invalid or duplicate catalog model ID: {_mask(str(cid))[:120]}")
            seen.add(cid)
            if len(seen) > MAX_RECORDS:
                raise ValueError("catalog exceeded upstream record bound")
            pricing = entry.get("pricing", {})
            overrides = pricing.get("overrides", [])
            if not isinstance(overrides, list) or any(not isinstance(rule, dict) for rule in overrides):
                raise ValueError("invalid pricing overrides")
            # Validate all known monetary fields while preserving original conditions and units.
            invalid_prices = []
            for block in [pricing, *overrides]:
                for key in ("prompt", "completion", "request", "image", "web_search", "internal_reasoning", "input_cache_read", "input_cache_write"):
                    if key in block:
                        try:
                            token_price(block[key])
                        except ValueError as error:
                            if rejected is None:
                                raise ValueError(f"{cid}: invalid {key} price") from error
                            invalid_prices.append(key)
            if invalid_prices:
                rejected.append({"catalog_id": cid, "reason": "invalid_or_unbounded_pricing", "fields": sorted(set(invalid_prices))})
                continue
            inp, out = token_price(pricing.get("prompt")), token_price(pricing.get("completion"))
            found.append(CatalogModel(catalog_id=cid, name=entry.get("name") or cid,
                context_length=entry.get("context_length"), supported_parameters=entry.get("supported_parameters") or [],
                input_usd_per_m=None if inp is None else inp * 1_000_000,
                output_usd_per_m=None if out is None else out * 1_000_000,
                pricing=pricing, pricing_overrides=overrides))
            if len(found) > MAX_RECORDS:
                raise ValueError("catalog exceeded record bound")
    if not found:
        raise ValueError("empty catalog")
    return sorted(found, key=lambda record: record.catalog_id)


def checked_page_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.netloc != "openrouter.ai" or parsed.path != "/api/v1/models"
            or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("pagination may only target the expected OpenRouter HTTPS models endpoint")
    return url


def fetch_pages(client, *, max_pages=MAX_PAGES):
    pages, urls, url, total = [], [], SOURCE_URL, 0
    while url:
        checked_page_url(url)
        if url in urls or len(urls) >= max_pages:
            raise ValueError("catalog pagination cycle or page bound reached; no snapshot published")
        for attempt in range(3):
            try:
                with client.stream("GET", url, timeout=30, follow_redirects=False) as response:
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        time.sleep(0.1 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    chunks = []
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise ValueError("catalog exceeded response-size bound")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                break
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    raise
                time.sleep(0.1 * (attempt + 1))
        body = json_load(raw)
        if not isinstance(body, dict) or not isinstance(body.get("links", {}), dict):
            raise ValueError("invalid pagination response")
        next_url = body.get("links", {}).get("next")
        if next_url is not None and not isinstance(next_url, str):
            raise ValueError("invalid next-page link")
        pages.append(raw)
        urls.append(url)
        url = checked_page_url(urljoin(url, next_url)) if next_url else None
    return pages, urls


def collect_snapshot(output_dir: Path, *, client=None, from_file: Path | None = None):
    if from_file:
        if from_file.stat().st_size > MAX_BYTES:
            raise ValueError("catalog exceeded response-size bound")
        pages, urls, acquisition = [from_file.read_bytes()], [SOURCE_URL], "file_import"
        body = json_load(pages[0])
        if isinstance(body, dict) and (body.get("links") or {}).get("next"):
            raise ValueError("file import is incomplete: next-page link present")
    else:
        if client is None:
            with httpx.Client() as session:
                return collect_snapshot(output_dir, client=session)
        pages, urls = fetch_pages(client)
        acquisition = "https_api"
    rejected = []
    records = normalize_pages(pages, rejected=rejected)
    files = {f"raw/page-{number:03d}.json": page for number, page in enumerate(pages, 1)}
    files["catalog.json"] = canonical([record.model_dump(mode="json") for record in records])
    files["rejected.json"] = canonical(rejected)
    raw_identity = {"urls": urls, "pages": [digest(page) for page in pages], "acquisition": acquisition}
    snapshot_id = digest(canonical(raw_identity))[:24]
    target = output_dir / snapshot_id
    if target.exists():
        return target, validate_snapshot(target)[0]
    manifest = SourceManifest(snapshot_id=snapshot_id, acquisition=acquisition,
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), record_count=len(records),
        rejected_record_count=len(rejected), upstream_record_count=len(records) + len(rejected),
        files={name: digest(raw) for name, raw in files.items()}, page_urls=urls)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".collect-", dir=output_dir) as tmp:
        staging = Path(tmp)
        for name, raw in files.items():
            (staging / name).parent.mkdir(parents=True, exist_ok=True)
            (staging / name).write_bytes(raw)
        (staging / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
        validate_snapshot(staging)
        try:
            staging.rename(target)
        except FileExistsError:
            validate_snapshot(target)
    return target, manifest


def validate_snapshot(directory: Path):
    manifest = SourceManifest.model_validate_json((directory / "manifest.json").read_text(encoding="utf-8"))
    raw_names = sorted(name for name in manifest.files if re.fullmatch(r"raw/page-\d{3}.json", name))
    if (set(manifest.files) != {"catalog.json", "rejected.json", *raw_names} or not raw_names
            or len(raw_names) > MAX_PAGES or len(raw_names) != len(manifest.page_urls)):
        raise ValueError("snapshot must contain only the expected catalog and raw page files")
    for name, expected in manifest.files.items():
        file = directory / name
        if file.is_symlink() or file.stat().st_size > MAX_BYTES or digest(file.read_bytes()) != expected:
            raise ValueError(f"snapshot content hash mismatch: {name}")
    if sum((directory / name).stat().st_size for name in raw_names) > MAX_BYTES:
        raise ValueError("retained raw pages exceed the total byte bound")
    rejected = []
    records = normalize_pages([(directory / name).read_bytes() for name in raw_names], rejected=rejected)
    normalized = canonical([record.model_dump(mode="json") for record in records])
    if normalized != (directory / "catalog.json").read_bytes() or len(records) != manifest.record_count:
        raise ValueError("normalized catalog does not match the retained raw pages")
    if ((directory / "rejected.json").read_bytes() != canonical(rejected)
            or len(rejected) != manifest.rejected_record_count
            or manifest.upstream_record_count != len(records) + len(rejected)):
        raise ValueError("quarantined catalog records do not match the retained response")
    for url in manifest.page_urls:
        checked_page_url(url)
    if manifest.page_urls[0] != SOURCE_URL:
        raise ValueError("snapshot must start at the expected catalog endpoint")
    for index, name in enumerate(raw_names):
        body = json_load((directory / name).read_bytes())
        next_url = (body.get("links") or {}).get("next")
        expected_next = manifest.page_urls[index + 1] if index + 1 < len(raw_names) else None
        if (urljoin(manifest.page_urls[index], next_url) if next_url else None) != expected_next:
            raise ValueError("snapshot page chain is incomplete or inconsistent")
    identity = {"urls": manifest.page_urls, "pages": [manifest.files[name] for name in raw_names], "acquisition": manifest.acquisition}
    if digest(canonical(identity))[:24] != manifest.snapshot_id:
        raise ValueError("snapshot ID does not match raw content")
    return manifest, records


def envelope(record_id, snapshot_id, payload, source_set, fixture=False):
    text = canonical(payload).decode("utf-8")
    return RecordEnvelope(record_id=record_id, snapshot_id=snapshot_id, payload_json=text,
                          payload_sha256=digest(text.encode()), source_set=source_set, integration_test_fixture=fixture)


def build_bundle(catalog_dir: Path, mapping: RouteMap, output_dir: Path, briefs=(), approaches=()):
    manifest, records = validate_snapshot(catalog_dir)
    by_id = {record.catalog_id: record for record in records}
    models = []
    for route in mapping.routes:
        if route.catalog_id not in by_id:
            raise ValueError(f"required catalog ID missing: {route.catalog_id}")
        catalog = by_id[route.catalog_id]
        market = MarketReference(snapshot_date=manifest.retrieved_at[:10], list_price_input_usd_per_m=catalog.input_usd_per_m,
            list_price_output_usd_per_m=catalog.output_usd_per_m,
            status=EvidenceStatus.verified if manifest.acquisition == "https_api" else EvidenceStatus.unverified)
        if route.billing_profile:
            model = route.billing_profile.model_copy(deep=True, update={"tier": route.tier, "required": route.required, "market": market})
        else:
            source = SourceRef(source_set="pricing_snapshots", record_id=route.route_id, version=manifest.snapshot_id,
                               status=EvidenceStatus.unknown)
            model = ModelProfile(model_id=route.route_id, provider_label="unverified route/provider mapping", tier=route.tier,
                required=route.required, source=source, market=market, rates=[
                    Rate(category=category, unit="1M tokens", usd_per_unit=None, status=EvidenceStatus.unknown, source=source)
                    for category in (RateCategory.input_tokens, RateCategory.output_tokens)])
        models.append(model)
    payloads = {"catalog": [(record.catalog_id, record.model_dump(mode="json")) for record in records],
                "models": [(model.model_id, model.model_dump(mode="json")) for model in models]}
    if briefs:
        payloads["briefs"] = [(brief.brief_id, brief.model_dump(mode="json")) for brief in briefs]
    if approaches:
        payloads["approaches"] = [(approach.approach_id, approach.model_dump(mode="json")) for approach in approaches]
    for key, values in payloads.items():
        if len({rid for rid, _ in values}) != len(values):
            raise ValueError(f"duplicate {key} IDs")
    source_manifest_hash = digest((catalog_dir / "manifest.json").read_bytes())
    identity = {"schema_version": "1.1", "catalog_snapshot": manifest.snapshot_id, "catalog_source_manifest_sha256": source_manifest_hash,
                "route_map": mapping.model_dump(mode="json"), "payloads": payloads}
    bundle_id = digest(canonical(identity))[:24]
    files = {}
    for key, values in payloads.items():
        source_set = {"models": "pricing_snapshots", "approaches": "pricing_snapshots", "briefs": "founder_briefs"}.get(key, "catalog")
        files[f"{key}.json"] = canonical([envelope(rid, bundle_id, payload, source_set,
            manifest.acquisition == "file_import").model_dump(mode="json") for rid, payload in values])
    bundle_manifest = {"schema_version": "1.1", "bundle_id": bundle_id, "catalog_snapshot_id": manifest.snapshot_id,
        "retrieved_at": manifest.retrieved_at, "route_map": mapping.model_dump(mode="json"),
        "catalog_source_manifest_sha256": source_manifest_hash, "catalog_acquisition": manifest.acquisition,
        "source_catalog_files": {f"source_catalog/{name}": digest((catalog_dir / name).read_bytes())
                                 for name in ["manifest.json", *manifest.files]},
        "files": {name: digest(raw) for name, raw in files.items()},
        "counts": {key: len(values) for key, values in payloads.items()},
        "ids": {key: [rid for rid, _ in values] for key, values in payloads.items()},
        "execution_tariffs_verified": False,
        "limitations": ["Catalog references do not supply execution billing rates or dispatch policies.",
                        "Route/provider identity and any supplied billing profile require separate verification."]}
    target = output_dir / bundle_id
    if target.exists():
        existing = validate_bundle(target)
        if existing != bundle_manifest:
            raise ValueError("immutable bundle conflict")
        return target, existing
    target.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        (target / name).write_bytes(raw)
    for name in bundle_manifest["source_catalog_files"]:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((catalog_dir / name.removeprefix("source_catalog/")).read_bytes())
    (target / "manifest.json").write_bytes(canonical(bundle_manifest))
    return target, validate_bundle(target)


def validate_bundle(directory):
    manifest = json_load((directory / "manifest.json").read_bytes())
    if manifest.get("schema_version") != "1.1":
        raise ValueError("unsupported source bundle version")
    if not re.fullmatch(r"[a-f0-9]{24}", manifest.get("bundle_id", "")):
        raise ValueError("invalid bundle ID")
    if not {"catalog.json", "models.json"}.issubset(manifest.get("files", {})):
        raise ValueError("catalog/model files are required")
    if not set(manifest["files"]).issubset({"catalog.json", "models.json", "briefs.json", "approaches.json"}):
        raise ValueError("invalid bundle file path")
    catalog_manifest, _ = validate_snapshot(directory / "source_catalog")
    expected_source_files = {f"source_catalog/{name}" for name in ["manifest.json", *catalog_manifest.files]}
    if set(manifest["source_catalog_files"]) != expected_source_files:
        raise ValueError("invalid retained source file set")
    for name, expected in manifest["source_catalog_files"].items():
        if digest((directory / name).read_bytes()) != expected:
            raise ValueError("retained raw source hash mismatch")
    if (digest((directory / "source_catalog/manifest.json").read_bytes()) != manifest["catalog_source_manifest_sha256"]
            or catalog_manifest.snapshot_id != manifest["catalog_snapshot_id"]
            or catalog_manifest.acquisition != manifest["catalog_acquisition"]):
        raise ValueError("catalog source identity mismatch")
    payloads = {}
    contracts = {"catalog": (CatalogModel, "catalog_id"), "models": (ModelProfile, "model_id"), "briefs": (FounderBrief, "brief_id")}
    from app.contracts import ApproachProfile
    contracts["approaches"] = (ApproachProfile, "approach_id")
    for name, expected in manifest["files"].items():
        if digest((directory / name).read_bytes()) != expected:
            raise ValueError(f"bundle content hash mismatch: {name}")
        rows = json_load((directory / name).read_bytes())
        key = name.removesuffix(".json")
        if len(rows) != manifest["counts"][key] or [row["record_id"] for row in rows] != manifest["ids"][key]:
            raise ValueError("bundle ID/count mismatch")
        payloads[key] = []
        for raw in rows:
            row = RecordEnvelope.model_validate(raw)
            if row.snapshot_id != manifest["bundle_id"] or digest(row.payload_json.encode()) != row.payload_sha256:
                raise ValueError("bundle envelope identity/hash mismatch")
            payload = json_load(row.payload_json)
            contract, identity = contracts[key]
            value = contract.model_validate(payload)
            if row.record_id != getattr(value, identity):
                raise ValueError("bundle payload identity mismatch")
            payloads[key].append((row.record_id, payload))
    mapping = RouteMap.model_validate(manifest["route_map"])
    if manifest["ids"]["models"] != [route.route_id for route in mapping.routes]:
        raise ValueError("bundle route mapping mismatch")
    identity = {"schema_version": "1.1", "catalog_snapshot": manifest["catalog_snapshot_id"],
                "catalog_source_manifest_sha256": manifest["catalog_source_manifest_sha256"],
                "route_map": mapping.model_dump(mode="json"), "payloads": payloads}
    if digest(canonical(identity))[:24] != manifest["bundle_id"]:
        raise ValueError("bundle ID does not match its content")
    return manifest
