"""Conservative reservations followed by usage-based settlement, separate from founder ledgers."""
from __future__ import annotations

from decimal import Decimal

from app.adapters.base import SetupIncomplete
from app.contracts import EvidenceStatus, RateCategory

MAX_OUTPUT_TOKENS = 1024
MAX_PROMPT_BYTES = 48000


def model_rates(profile):
    rates = []
    for category in (RateCategory.input_tokens, RateCategory.output_tokens):
        matches = [r for r in profile.rates if r.category == category]
        if len(matches) != 1:
            raise SetupIncomplete(f"Exactly one input/output rate is required for {profile.model_id}.")
        rate = matches[0]
        if (rate.usd_per_unit is None or not rate.usd_per_unit.is_finite() or rate.usd_per_unit < 0
                or rate.status != EvidenceStatus.verified or rate.source.status != EvidenceStatus.verified
                or not rate.source.verified_at or not (rate.source.origin_url or "").startswith("https://")
                or rate.unit not in {"1M tokens", "1000000 tokens"}):
            raise SetupIncomplete(f"Dated, cited, verified per-million-token rates required for {profile.model_id}.")
        rates.append(rate.usd_per_unit)
    return tuple(rates)


def token_usage(usage):
    if not isinstance(usage, dict):
        raise ValueError("Missing token usage")
    counts = (usage.get("prompt_tokens", usage.get("input_tokens")),
              usage.get("completion_tokens", usage.get("output_tokens")))
    if any(type(n) is not int or n < 0 for n in counts) or sum(counts) == 0:
        raise ValueError("Missing or invalid token usage")
    return counts


def cost(counts, rates):
    return sum((Decimal(n) * r for n, r in zip(counts, rates)), Decimal("0")) / Decimal("1000000")


def reservation(system, user, schema, rates):
    import json
    # UTF-8 bytes are a deliberately conservative input-token bound, with envelope headroom.
    size = len((system + user + json.dumps(schema or {})).encode("utf-8"))
    if size > MAX_PROMPT_BYTES:
        raise SetupIncomplete("Prompt exceeds the bounded evaluation input size.")
    return cost((size + 2048, MAX_OUTPUT_TOKENS), rates)
