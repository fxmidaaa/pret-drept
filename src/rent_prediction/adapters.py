"""Model-family boundary (§10.3), independent of runner, harness and LLM providers."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RegressionAdapter(Protocol):
    """Model-specific representation is private; prediction must never fit or update state.

    Implementations validate canonical records, preserve fitted preprocessing, export native
    payloads, declare unknown-category behavior, and load only verified compatible bundles.
    This protocol does not imply that a model adapter or certified runtime is implemented.
    """

    family: str
    interface_version: str

    def configuration_schema(self) -> Mapping[str, Any]: ...

    def validate_configuration(self, configuration: Mapping[str, Any]) -> None: ...

    def fit(
        self,
        records: Sequence[Mapping[str, Any]],
        targets_eur: Sequence[float],
        *,
        configuration: Mapping[str, Any],
        random_seed: int,
    ) -> None: ...

    def predict(self, records: Sequence[Mapping[str, Any]]) -> Sequence[float]: ...

    def export_state(self, destination: Path) -> Mapping[str, Any]: ...

    @classmethod
    def load_state(cls, source: Path, manifest: Mapping[str, Any]) -> "RegressionAdapter": ...

    def requirements(self) -> Mapping[str, Any]: ...

    def runtime_capabilities(self) -> Mapping[str, Any]: ...
