"""Synthetic billing attestations for offline tests ONLY; no provider/runtime proof."""
from app.contracts import DispatchPolicy, EvidenceStatus, SourceRef


def verified_profile(model):
    def source(ref):
        return ref.model_copy(update={"status": EvidenceStatus.verified, "origin_url": "https://example.test/synthetic-billing",
                                      "verified_at": "2026-10-25T00:00:00Z", "version": "synthetic-fixture-only"})
    policy = DispatchPolicy(max_prompt_bytes=100_000, prompt_tokens_per_byte="1", prompt_overhead_tokens=2048,
                            max_output_tokens=1024, completion_limit_includes_reasoning=True,
                            billing_mode="input_output_only", source=source(model.source))
    return model.model_copy(update={"rates": [rate.model_copy(update={"status": EvidenceStatus.verified,
                                                                    "source": source(rate.source)}) for rate in model.rates],
                                    "dispatch_policy": policy, "source": source(model.source)})
