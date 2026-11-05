"""Fitted feature state for the legacy XGBoost pipeline and its future adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction import DictVectorizer


@dataclass(frozen=True)
class XGBoostPreprocessing:
    features: tuple[str, ...]
    vectorizer: DictVectorizer
    imputation_medians: Mapping[str, float]
    serving_defaults: Mapping[str, float]

    @classmethod
    def fit_transform(
        cls,
        training_features: pd.DataFrame,
        *,
        imputation_medians: Mapping[str, float],
        numeric_fields: Sequence[str],
    ) -> tuple[Self, np.ndarray]:
        from sklearn.feature_extraction import DictVectorizer

        vectorizer = DictVectorizer(sparse=False)
        encoded = vectorizer.fit_transform(training_features.to_dict(orient="records"))
        state = cls(
            features=tuple(training_features.columns),
            vectorizer=vectorizer,
            imputation_medians=dict(imputation_medians),
            serving_defaults={
                field: float(training_features[field].median())
                for field in numeric_fields
                if field not in imputation_medians
            },
        )
        return state, encoded

    def transform(self, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
        return self.vectorizer.transform(rows)

    @property
    def numeric_defaults(self) -> dict[str, float]:
        return {**self.serving_defaults, **self.imputation_medians}

    def legacy_bundle_fields(self) -> dict[str, Any]:
        """Store the fitted state using ordinary legacy bundle values."""
        return {
            "features": list(self.features),
            "dv": self.vectorizer,
            "numeric_defaults": self.numeric_defaults,
            "imputation_medians": dict(self.imputation_medians),
        }

    @classmethod
    def from_legacy_bundle(cls, bundle: Mapping[str, Any]) -> Self:
        fitted = bundle.get("imputation_medians", {})
        return cls(
            features=tuple(bundle["features"]),
            vectorizer=bundle["dv"],
            imputation_medians=fitted,
            serving_defaults={
                field: value
                for field, value in bundle["numeric_defaults"].items()
                if field not in fitted
            },
        )
