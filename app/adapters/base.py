"""Adapter interfaces. Live implementations fail visibly when setup is incomplete;
sample implementations read bundled data and make zero network calls."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.contracts import ApproachProfile, DevTaskCase, FounderBrief, ModelProfile, SourceRef


class DataLayer(ABC):
    """Zetaris boundary. Every read returns records plus the SourceRefs that prove where they came from."""

    @abstractmethod
    def read_brief(self, brief_id: str) -> tuple[FounderBrief, SourceRef]: ...

    @abstractmethod
    def read_approaches(self) -> list[ApproachProfile]: ...

    @abstractmethod
    def read_models(self) -> list[ModelProfile]: ...

    @abstractmethod
    def read_task_cases(self, split: str) -> list[DevTaskCase]: ...

    @abstractmethod
    def read_sealed_actuals(self, project_id: str) -> dict: ...

    @abstractmethod
    def write_evidence(self, record: dict) -> SourceRef: ...


class InferenceResult(dict):
    """Keys: text, requested_model, resolved_model, route_id, usage, elapsed_s, execution_kind."""


class Inference(ABC):
    """Nightshift boundary. The only path to any model. No direct-provider fallback exists."""

    @abstractmethod
    def complete(self, *, role: str, model: str, system: str, user: str,
                 json_schema: Optional[dict] = None, timeout_s: int = 60,
                 max_tokens: Optional[int] = None) -> InferenceResult: ...

    @abstractmethod
    def list_models(self) -> list[str]: ...


class Memory(ABC):
    """Meterless H-MEM boundary via the Node bridge. A dict is not an engine."""

    @abstractmethod
    def remember_confirmed(self, project_scope: str, payload: dict) -> dict: ...

    @abstractmethod
    def recall(self, project_scope: str, query: dict) -> dict: ...

    @abstractmethod
    def audit(self, project_scope: str) -> dict: ...


class SetupIncomplete(RuntimeError):
    """Raised by live adapters when configuration or runtime is missing. Never swallowed."""


def require_env(name: str) -> str:
    """A live setting that is absent or still a .env.example placeholder fails visibly."""
    import os
    v = os.getenv(name)
    if not v or v.startswith("your-"):
        raise SetupIncomplete(f"{name} is not configured. Copy .env.example to .env and fill real values.")
    return v
