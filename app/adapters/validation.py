"""Fail-closed validation shared by adapter diagnostics and platform preflight."""
from __future__ import annotations


def sql_rows(body) -> list:
    """Recognize explicit row containers, never treat unknown objects as a successful query."""
    if isinstance(body, list):
        return body
    if not isinstance(body, dict):
        raise ValueError("SQL response is not a row container")
    if (any(body.get(key) for key in ("error", "errors", "errorMessage"))
            or body.get("success") is False
            or str(body.get("status", "")).lower() in {"error", "failed", "failure"}):
        raise ValueError("SQL response reports an error")
    for key in ("rows", "data", "result", "results", "records"):
        value = body.get(key)
        if isinstance(value, (list, dict)):
            return sql_rows(value)
    raise ValueError("SQL response has no recognized rows; installed response mapping is required")


def validate_select_one(body) -> None:
    rows = sql_rows(body)
    if len(rows) != 1:
        raise ValueError("SELECT 1 must return exactly one row")
    row = rows[0]
    cells = list(row.values()) if isinstance(row, dict) else row
    if not isinstance(cells, list) or len(cells) != 1:
        raise ValueError("SELECT 1 must return exactly one cell")
    value = cells[0]
    if not ((type(value) in (int, float) and value == 1) or (type(value) is str and value.strip() == "1")):
        raise ValueError("SELECT 1 cell must be 1")


def validate_model_ids(ids) -> list[str]:
    if not isinstance(ids, list) or not ids:
        raise ValueError("Model discovery must contain a nonempty data list")
    if any(not isinstance(model, str) or not model.strip() or model != model.strip() for model in ids):
        raise ValueError("Model discovery contains an invalid route ID")
    if len(ids) != len(set(ids)):
        raise ValueError("Model discovery contains duplicate route IDs")
    return ids


def parse_model_discovery(body) -> list[str]:
    if not isinstance(body, dict) or body.get("error") or body.get("errors"):
        raise ValueError("Model discovery must be a data object without errors")
    entries = body.get("data")
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError("Model discovery must contain a list of model objects")
    return validate_model_ids([entry.get("id") for entry in entries])
