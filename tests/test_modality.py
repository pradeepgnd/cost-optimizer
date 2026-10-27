"""R2: catalog modality fields, image modalities and the not-executable/unknown-cost rules."""
from decimal import Decimal
import json

import pytest
from pydantic import ValidationError

from app.contracts import FeatureProfile, MarketReference, Stage, TokenUsage, covers_modalities
from app.controller import AUDIO_NOT_EXECUTABLE, IMAGE_NOT_EXECUTABLE, Controller
from app.economics import stage_cost_row
from app.source_snapshots import normalize_pages
from tests.test_stage_economics import _feature, _model


def _page(*entries):
    return json.dumps({"data": list(entries)}).encode()


def _entry(cid, *, inp=("text",), out=("text",), hf=None, architecture=True):
    entry = {"id": cid, "name": cid, "pricing": {"prompt": "0.000001", "completion": "0.000002"}}
    if architecture:
        entry["architecture"] = {"input_modalities": list(inp), "output_modalities": list(out)}
    if hf:
        entry["hugging_face_id"] = hf
    return entry


def _market(inp, out):
    return MarketReference(snapshot_date="2026-10-25", input_modalities=inp, output_modalities=out)


def test_normalizer_keeps_modalities_and_open_weights_signal():
    records = normalize_pages([_page(_entry("lab/vision", inp=("image", "text", "image"), hf="lab/vision-hf"),
                                     _entry("lab/plain"))])
    plain, vision = records      # normalized records are sorted by catalog ID
    assert (plain.catalog_id, vision.catalog_id) == ("lab/plain", "lab/vision")
    assert vision.input_modalities == ["image", "text"] and vision.output_modalities == ["text"]
    assert vision.hugging_face_id == "lab/vision-hf" and plain.hugging_face_id is None


def test_missing_architecture_stays_unknown_not_text_only():
    (record,) = normalize_pages([_page(_entry("lab/bare", architecture=False))])
    assert record.input_modalities is None and record.output_modalities is None


def test_malformed_modalities_are_rejected():
    page = _page({**_entry("lab/bad"), "architecture": {"input_modalities": "text", "output_modalities": ["text"]}})
    with pytest.raises(ValueError, match="invalid architecture modalities"):
        normalize_pages([page])


@pytest.mark.parametrize("modalities,inp,out,expected", [
    (["text"], ["text"], ["text"], True),
    (["image_in", "text"], ["text"], ["text"], False),
    (["image_in", "text"], ["image", "text"], ["text"], True),
    (["audio_in", "text"], ["image", "text"], ["text"], False),
    (["audio_in", "text"], ["audio", "text"], ["text"], True),
    (["text", "image_out"], ["text"], ["image", "text"], True),
    (["text", "audio_out"], ["text"], ["text"], False),
    (["text"], ["text"], ["image"], False),     # a text feature still needs text output
])
def test_covers_modalities(modalities, inp, out, expected):
    assert covers_modalities(_market(inp, out), modalities) is expected


def test_unknown_catalog_modalities_give_unknown_coverage():
    assert covers_modalities(None, ["text"]) is None
    assert covers_modalities(MarketReference(snapshot_date="2026-10-25"), ["text"]) is None


def test_market_reference_omits_unset_modality_fields():
    dumped = MarketReference(snapshot_date="2026-10-25").model_dump(mode="json")
    assert not {"input_modalities", "output_modalities", "open_weights_signal"} & set(dumped)


def test_feature_accepts_image_modalities_and_rejects_unknown_ones():
    base = dict(feature_id="f", description="d", example_input="x", mode="interactive")
    assert FeatureProfile(**base, modality=["image_in", "text"]).modality == ["image_in", "text"]
    with pytest.raises(ValidationError):
        FeatureProfile(**base, modality=["video_in"])


@pytest.mark.parametrize("modality,reason", [(["image_in", "text"], IMAGE_NOT_EXECUTABLE),
                                             (["text", "image_out"], IMAGE_NOT_EXECUTABLE),
                                             (["audio_in", "text"], AUDIO_NOT_EXECUTABLE),
                                             (["audio_in", "image_in"], AUDIO_NOT_EXECUTABLE),
                                             (["text"], None)])
def test_not_executable_reason_follows_modality(modality, reason):
    feature = _feature().model_copy(update={"modality": modality})
    assert Controller._not_executable(feature) == reason


def test_image_feature_cost_is_unknown_not_zero():
    feature = _feature().model_copy(update={"modality": ["image_in", "text"]})
    tokens = TokenUsage(input_tokens=100, output_tokens=50, basis="measured", method="api usage")
    row = stage_cost_row(feature, _model(), Stage(name="Launch", active_users=100), tokens)
    assert row.gross_monthly_usd is None and row.cost_per_call_usd is None
    assert any("image_in pricing is not modeled" in warning for warning in row.warnings)
    text_row = stage_cost_row(_feature(), _model(), Stage(name="Launch", active_users=100), tokens)
    assert text_row.gross_monthly_usd is not None
