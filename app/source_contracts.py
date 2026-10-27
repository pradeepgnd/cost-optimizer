"""Versioned public source contracts; catalog facts never certify an execution tariff."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_serializer, model_validator

from app.contracts import (ApproachProfile, FounderBrief, ModelProfile, NonBlank, NonNegativeDecimal,
                           NonNegativeInt, PositiveInt, PublicInput, SourceRef, require_unique)

SOURCE_URL = "https://openrouter.ai/api/v1/models"


class CatalogModel(PublicInput):
    catalog_id: NonBlank
    name: NonBlank
    context_length: NonNegativeInt | None = None
    supported_parameters: list[str] = Field(default_factory=list)
    input_usd_per_m: NonNegativeDecimal | None = None
    output_usd_per_m: NonNegativeDecimal | None = None
    pricing: dict = Field(default_factory=dict)
    # All conditional/auxiliary terms are retained, without claiming support in the cost engine.
    pricing_overrides: list[dict] = Field(default_factory=list)
    # Catalog reference only. None == the snapshot did not carry the field (unknown, not "text only").
    input_modalities: list[str] | None = None
    output_modalities: list[str] | None = None
    hugging_face_id: str | None = None


class SourceManifest(PublicInput):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    source_url: Literal["https://openrouter.ai/api/v1/models"] = SOURCE_URL
    acquisition: Literal["https_api", "file_import"]
    retrieved_at: str
    scope: Literal["text_model_catalog"] = "text_model_catalog"
    complete: Literal[True] = True
    record_count: PositiveInt
    rejected_record_count: NonNegativeInt = 0
    upstream_record_count: PositiveInt
    files: dict[str, str]
    page_urls: list[str]
    usage_terms_url: str = "https://openrouter.ai/terms"
    usage_terms_status: Literal["requires_review"] = "requires_review"
    purpose: Literal["catalog_reference_only"] = "catalog_reference_only"

    @model_validator(mode="after")
    def _date(self):
        if datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("retrieved_at must include a timezone")
        return self


class RouteMapping(PublicInput):
    catalog_id: NonBlank
    route_id: NonBlank
    tier: Literal["frontier", "mid_tier", "open_source"] | None = None
    required: bool = False
    # A deliberately curated profile, never derived by copying a catalog price into a tariff.
    billing_profile: ModelProfile | None = None
    # Human-readable role note, e.g. why this route fills its tier. Descriptive only; selection never reads it.
    label: NonBlank | None = None

    @model_validator(mode="after")
    def _binding(self):
        if self.required and self.tier != "open_source":
            raise ValueError("only the open_source route can be required")
        if self.billing_profile and self.billing_profile.model_id != self.route_id:
            raise ValueError("billing profile must match the exact mapped Nightshift route")
        return self

    @model_serializer(mode="wrap")
    def _omit_unset_label(self, handler):
        # Bundle IDs hash the dumped route map; an absent label must not change existing bundle identities.
        data = handler(self)
        if self.label is None:
            data.pop("label", None)
        return data


class RouteMap(PublicInput):
    routes: list[RouteMapping] = Field(min_length=2, max_length=200)
    mapping_status: Literal["planned", "discovery_observed"] = "planned"
    discovery_source: SourceRef | None = None

    @model_validator(mode="after")
    def _unique(self):
        require_unique([route.route_id for route in self.routes], "route IDs")
        # A tier is an optional curated hint; the controller derives the rest. No route is pinned or required.
        if self.mapping_status == "discovery_observed" and not self.discovery_source:
            raise ValueError("observed mapping requires a retained discovery source")
        return self


class RecordEnvelope(PublicInput):
    record_id: NonBlank
    snapshot_id: NonBlank
    payload_json: str
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_set: Literal["catalog", "pricing_snapshots", "founder_briefs", "evaluation_evidence"]
    integration_test_fixture: bool = False


class SourceBindings(PublicInput):
    schema_version: Literal["1.1"] = "1.1"
    namespace: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
    snapshot_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    tables: dict[str, str]
    expected_counts: dict[str, NonNegativeInt]
    expected_ids: dict[str, list[str]]
    expected_row_sha256: dict[str, dict[str, str]]
    registered: bool = False
    catalog_source_url: Literal["https://openrouter.ai/api/v1/models"] = SOURCE_URL
    catalog_acquisition: Literal["https_api", "file_import"] = "file_import"
    catalog_retrieved_at: str | None = None

    @model_validator(mode="after")
    def _tables(self):
        import re
        if not set(self.tables).issubset({"catalog", "models", "briefs", "approaches"}):
            raise ValueError("unsupported source table binding")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", table) for table in self.tables.values()):
            raise ValueError("invalid bound table name")
        if (set(self.tables) != set(self.expected_counts) or set(self.tables) != set(self.expected_ids)
                or set(self.tables) != set(self.expected_row_sha256)):
            raise ValueError("each binding needs exact expected counts and IDs")
        for key, ids in self.expected_ids.items():
            require_unique(ids, f"{key} IDs")
            if len(ids) != self.expected_counts[key]:
                raise ValueError("expected ID count mismatch")
            if (set(self.expected_row_sha256[key]) != set(ids)
                    or any(not re.fullmatch(r"[a-f0-9]{64}", value) for value in self.expected_row_sha256[key].values())):
                raise ValueError("each pinned source row needs its expected envelope SHA-256")
        return self


class StorageConfig(PublicInput):
    backend: Literal["localstack", "aws"] = "localstack"
    bucket: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
    prefix: str = Field(default="cost-optimizer/v4", pattern=r"^[A-Za-z0-9][A-Za-z0-9/_-]{0,180}$")
    region: NonBlank = "us-east-1"
    publisher_endpoint: str | None = "http://127.0.0.1:4566"
    zetaris_endpoint: str | None = "http://cost-optimizer-localstack:4566"
    namespace: str = Field(default="cost_optimizer_v4", pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")

    @model_validator(mode="after")
    def _endpoint(self):
        from urllib.parse import urlparse
        if ".." in self.prefix or self.prefix.endswith("/"):
            raise ValueError("invalid storage prefix")
        if self.backend == "aws":
            if self.publisher_endpoint or self.zetaris_endpoint:
                raise ValueError("AWS uses its standard endpoint; set both custom endpoints to null")
        else:
            for endpoint in (self.publisher_endpoint, self.zetaris_endpoint):
                url = urlparse(endpoint or "")
                if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
                    raise ValueError("invalid LocalStack endpoint")
                import re
                if not re.fullmatch(r"https?://[A-Za-z0-9._:\[\]-]+/?", endpoint):
                    raise ValueError("LocalStack endpoints must be plain host/port URLs")
            if urlparse(self.publisher_endpoint).hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("LocalStack publisher endpoint must be loopback; test credentials cannot target a remote host")
        return self
