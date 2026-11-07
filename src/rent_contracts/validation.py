"""Strict JSON/schema validation, without remote schema lookup or authorization."""

import json
import math
from functools import lru_cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource

from rent_domain.apartment import ApartmentRelationshipError, validate_apartment_relationships

SCHEMA_NAMES = (
    "apartment",
    "experiment-request",
    "train-request",
    "predict-batch-request",
    "prediction-batch",
    "bundle-manifest",
    "task-record",
    "observation-reference",
    "evaluation-policy",
    "development-split",
    "observation-source",
    "observation-quality-report",
    "observation-candidate",
    "dataset-release",
    "restoration-report",
    "observation-inventory",
    "observation-candidate-v2",
    "dataset-release-v2",
)
MAX_DOCUMENT_BYTES = 1_048_576


class ContractError(ValueError):
    """A safe diagnostic, deliberately excluding submitted values and raw validator text."""


class DocumentSizeError(ContractError):
    """A well-formed document exceeded the shared 1 MiB wire bound.

    This refines, and never replaces, ``ContractError`` so a caller can tell a size limit
    from a malformed document. The message and every existing handler stay unchanged.
    """


def _strict_tree(value: Any, depth: int = 0) -> None:
    if depth > 64:
        raise ContractError("JSON nesting limit exceeded")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ContractError("nonfinite JSON number")
        return
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ContractError("JSON object keys must be strings")
            _strict_tree(child, depth + 1)
        return
    if type(value) is list:
        for child in value:
            _strict_tree(child, depth + 1)
        return
    raise ContractError("unsupported JSON value type")


def canonical_json(document: Any) -> str:
    """Local v1 canonicalization; not an assertion of RFC 8785 compliance."""
    _strict_tree(document)
    try:
        encoded = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > MAX_DOCUMENT_BYTES:
            raise DocumentSizeError("document size limit exceeded")
        return encoded
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("invalid JSON encoding") from None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON object key")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise ContractError("nonfinite JSON number")


def load_document(raw: str | bytes) -> dict[str, Any]:
    if not isinstance(raw, (str, bytes)):
        raise ContractError("expected JSON text or UTF-8 bytes")
    try:
        if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > MAX_DOCUMENT_BYTES:
            raise DocumentSizeError("document size limit exceeded")
        if isinstance(raw, bytes):
            # json.loads(bytes) auto-detects UTF-16/32 and strips a UTF-8 BOM.
            # Decode explicitly so every wire document follows the UTF-8 contract.
            raw = raw.decode("utf-8")
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
        canonical_json(value)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("invalid JSON document") from None
    if type(value) is not dict:
        raise ContractError("expected a JSON object")
    return value


def _no_remote_lookup(uri: str) -> Resource:
    raise NoSuchResource(ref=uri)


@lru_cache(maxsize=1)
def _resources() -> tuple[dict[str, dict], Registry]:
    schemas = {}
    registry = Registry(retrieve=_no_remote_lookup)
    for name in SCHEMA_NAMES:
        version = "v2" if name.endswith("-v2") else "v1"
        filename = f"{name.removesuffix('-v2')}.schema.json"
        schema = load_document(
            files("rent_contracts").joinpath("schemas", version, filename).read_bytes()
        )
        Draft202012Validator.check_schema(schema)
        schemas[name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def validate_document(name: str, document: dict[str, Any]) -> None:
    """Validate public syntax and cross-field apartment constraints."""
    if name not in SCHEMA_NAMES:
        raise ContractError("unsupported document contract")
    canonical_json(document)
    schemas, registry = _resources()
    validator = Draft202012Validator(
        schemas[name], registry=registry, format_checker=FormatChecker()
    )
    error = next(validator.iter_errors(document), None)
    if error is not None:
        # Never echo user-supplied property names, values, credentials or raw exceptions.
        raise ContractError(f"{name} contract violation ({error.validator})")
    if name == "apartment":
        try:
            validate_apartment_relationships(document)
        except ApartmentRelationshipError as exc:
            raise ContractError(str(exc)) from None


def validate_configuration(configuration: dict, schema: dict) -> None:
    """The caller supplies an already registered adapter schema, never an import path."""
    canonical_json(configuration)
    canonical_json(schema)
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(
            schema, registry=Registry(retrieve=_no_remote_lookup), format_checker=FormatChecker()
        )
        if next(validator.iter_errors(configuration), None) is not None:
            raise ContractError("adapter configuration contract violation")
    except ContractError:
        raise
    except Exception:
        # Resolver/schema exceptions can contain caller-controlled URI/text.
        raise ContractError("invalid or unresolved adapter configuration schema") from None
