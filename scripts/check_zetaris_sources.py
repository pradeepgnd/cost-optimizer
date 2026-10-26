"""Independent source proof: typed reads, explicit catalog scenario and optional fixture write/readback.

No Nightshift completions or H-MEM setup is required. Output is component evidence,
never a claim of a measured model run or verified execution billing.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.adapters.base import SetupIncomplete
from app.adapters.live_zetaris import ZetarisDataLayer, record_id
from app.adapters.validation import validate_select_one
from app.contracts import EvidenceStatus, FeatureProfile, ModelProfile, Rate, RateCategory, Stage, TokenUsage
from app.economics import stage_cost_row
from app.source_contracts import SourceBindings, StorageConfig
from app.source_registry import EvidencePublisher
from app.source_snapshots import canonical, digest
from app.trace import Trace, _mask


def reference_projection(catalog, source):
    """Explicit token-only catalog scenario; never inserted into application execution profiles."""
    if catalog.input_usd_per_m is None or catalog.output_usd_per_m is None:
        raise ValueError("catalog reference price unknown; an arithmetic PASS requires both token prices")
    source = source.model_copy(update={"source_set": "catalog_reference_scenario", "status": EvidenceStatus.unverified})
    model = ModelProfile(model_id=catalog.catalog_id, provider_label="OpenRouter reference scenario", source=source,
        rates=[Rate(category=category, unit="1M tokens", usd_per_unit=price, status=EvidenceStatus.unverified, source=source)
               for category, price in ((RateCategory.input_tokens, catalog.input_usd_per_m), (RateCategory.output_tokens, catalog.output_usd_per_m))])
    feature = FeatureProfile(feature_id="integration-reference", description="Synthetic token-price arithmetic check",
        example_input="Fixture only", mode="interactive", uses_per_user_month="10", calls_per_use=1)
    stage = Stage(name="Component fixture", active_users=100)
    usage = TokenUsage(input_tokens="1000", output_tokens="100", basis="estimated", method="explicit integration fixture, no inference")
    row = stage_cost_row(feature, model, stage, usage, retry_rate=Decimal("0"))
    if catalog.input_usd_per_m is not None and catalog.output_usd_per_m is not None:
        expected = (Decimal(1000) * catalog.input_usd_per_m + Decimal(100) * catalog.output_usd_per_m) / 1_000_000 * 1000
        if row._exact_gross != expected:
            raise ValueError("queried catalog price did not reproduce calculator arithmetic")
    return {"kind": "catalog_reference_scenario", "execution_tariff": False, "model_execution_performed": False,
        "complete_billing_estimate": False,
        "source": source.model_dump(mode="json"), "row": row.model_dump(mode="json"),
        "limitations": ["Token-only reference prices with synthetic volume/usage; not a serving-provider or Nightshift bill.",
                        "Conditional/auxiliary fees are retained in the catalog and are not verified by this scenario."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--catalog-id", help="Exact retained catalog ID for the reference arithmetic check.")
    parser.add_argument("--output-dir", type=Path, required=True, help="A new directory; existing evidence is preserved.")
    parser.add_argument("--round-trip", action="store_true", help="Publish a labeled integration-test record and read it through Zetaris.")
    parser.add_argument("--storage", type=Path, help="Publisher-side config, required for --round-trip.")
    parser.add_argument("--run-id", default=None, help="Reuse for the idempotency test; evidence content is stable.")
    parser.add_argument("--no-dotenv", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("--output-dir must be new; existing artifacts are never overwritten")
    if args.round_trip and not args.storage:
        parser.error("--round-trip requires --storage")
    args.output_dir.mkdir(parents=True)
    if not args.no_dotenv:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    run_id = record_id(args.run_id or "source-check-" + uuid.uuid4().hex[:12])
    layer = None
    report = {"status": "incomplete", "scope": "Zetaris source component only", "run_id": run_id,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model_completions": 0,
        "execution_billing_verified": False, "checks": []}
    try:
        bindings = SourceBindings.model_validate_json(args.bindings.read_text())
        layer = ZetarisDataLayer(Trace(run_id, "live", str(args.output_dir), echo=False), bindings=bindings)
        body = layer.select_one()
        validate_select_one(body)
        (args.output_dir / "select-one.json").write_bytes(canonical(body))
        report["checks"].append({"check": "SELECT 1", "status": "pass"})
        models = layer.read_models()
        report["checks"].append({"check": "typed pinned model read", "status": "pass", "model_ids": [model.model_id for model in models]})
        (args.output_dir / "models.json").write_bytes(canonical([model.model_dump(mode="json") for model in models]))
        if "briefs" in bindings.tables:
            brief, source = layer.read_brief(bindings.expected_ids["briefs"][0])
            report["checks"].append({"check": "typed founder brief read", "status": "pass", "brief_id": brief.brief_id,
                                      "source": source.model_dump(mode="json")})
        cid = args.catalog_id or bindings.expected_ids["catalog"][0]
        catalog, source = layer.read_catalog(cid)
        scenario = reference_projection(catalog, source)
        (args.output_dir / "reference-scenario.json").write_bytes(canonical(scenario))
        report["checks"].append({"check": "queried catalog reference arithmetic", "status": "pass", "catalog_id": cid,
            "input_usd_per_m": str(catalog.input_usd_per_m), "output_usd_per_m": str(catalog.output_usd_per_m),
            "execution_tariff": False, "source": source.model_dump(mode="json")})
        if args.round_trip:
            config = StorageConfig.model_validate_json(args.storage.read_text())
            publisher = EvidencePublisher(layer, config, bindings)
            record = {"id": run_id + "/integration-test", "run_id": run_id, "kind": "integration_test_fixture",
                      "payload": {"message": "source round-trip fixture; no inference", "fixture": True}}
            first = publisher.write(record)
            second = publisher.write(record)
            appended = {**record, "id": run_id + "/integration-test-2", "payload": {"message": "second fixture; no inference", "fixture": True}}
            publisher.write(appended)
            # Recreate publisher state to prove the first ID remains idempotent after an append/restart.
            EvidencePublisher(layer, config, bindings).write(record)
            payload, read = layer.read_evidence(record["id"])
            if canonical(payload) != canonical(record) or first.version != second.version or first.version != read.version:
                raise ValueError("evidence continuity/idempotency assertion failed")
            report["checks"].append({"check": "fixture write/readback, append, restart and duplicate write", "status": "pass",
                "appended_record_id": appended["id"],
                "source": read.model_dump(mode="json"), "payload_sha256": digest(canonical(record)), "real_measured_sample": False})
        report["status"] = "pass"
    except Exception as error:
        report.update(status="fail", error_type=type(error).__name__,
                      message="Source check failed; retained artifacts contain successful prior checks. No model was called.")
        if isinstance(error, SetupIncomplete):
            # Setup messages name missing settings, never their values; masking is a second guard.
            report["setup_issue"] = str(_mask(str(error)))[:300]
    finally:
        if layer:
            layer.client.close()
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
