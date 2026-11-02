from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def require_legacy_artifact(request):
    if request.node.get_closest_marker("legacy_artifact"):
        artifact = Path(__file__).resolve().parents[1] / "model.joblib"
        if not artifact.is_file():
            pytest.skip("private legacy model.joblib absent; no artifact result is claimed")
