"""Immutable, validated public requests; parsing grants no execution capability."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import InitVar, dataclass, field
from typing import Any

from .validation import (
    ContractError,
    canonical_json,
    load_document,
    validate_configuration,
    validate_document,
)


@dataclass(frozen=True)
class ExperimentRequest:
    """Every construction validates against registered schemas, then stores canonical JSON.

    Principal is never caller supplied; validation grants no execution authority.
    """

    canonical_payload: str
    model_schemas: InitVar[Mapping[str, dict]] = field(kw_only=True)

    def __post_init__(self, model_schemas: Mapping[str, dict]) -> None:
        document = load_document(self.canonical_payload)
        validate_document("experiment-request", document)
        schema = model_schemas.get(document["model_family"])
        if schema is None:
            raise ContractError("unregistered model family")
        validate_configuration(document["configuration"], schema)
        object.__setattr__(self, "canonical_payload", canonical_json(document))

    @classmethod
    def from_document(
        cls, document: dict[str, Any], *, model_schemas: Mapping[str, dict]
    ) -> "ExperimentRequest":
        return cls(canonical_json(document), model_schemas=model_schemas)

    @property
    def request_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_payload.encode("utf-8")).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return json.loads(self.canonical_payload)
