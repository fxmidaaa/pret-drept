from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    n_estimators: int = Field(ge=1, le=1000)
    max_depth: int = Field(ge=1, le=12)
    learning_rate: float = Field(gt=0, le=1)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    seed: int = Field(ge=0, le=2**31 - 1)
    evaluation_fraction: float = Field(ge=0.1, le=0.5)
    model: ModelConfig


def load_config(path: Path) -> Config:
    return Config.model_validate_json(path.read_text(encoding="utf-8"))
