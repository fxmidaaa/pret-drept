"""Immutable, validated public requests; parsing grants no execution capability."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .validation import ContractError, canonical_json, validate_configuration, validate_document


@dataclass(frozen=True)
class ExperimentRequest:
    """Canonical payload prevents mutation after validation. Principal is never caller supplied."""

    canonical_payload: str

    @classmethod
    def from_document(
        cls, document: dict[str, Any], *, model_schemas: Mapping[str, dict]
    ) -> "ExperimentRequest":
        validate_document("experiment-request", document)
        schema = model_schemas.get(document["model_family"])
        if schema is None:
            raise ContractError("unregistered model family")
        validate_configuration(document["configuration"], schema)
        return cls(canonical_json(document))

    @property
    def request_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_payload.encode("utf-8")).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return json.loads(self.canonical_payload)
