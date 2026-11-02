from pathlib import Path

import pytest

from rent_checks.architecture import check_architecture

ROOT = Path(__file__).resolve().parents[2]


def test_actual_repository_respects_dependency_boundaries():
    assert check_architecture(ROOT) == []


@pytest.mark.parametrize(
    "path,source",
    [
        ("src/rent_prediction/model.py", "import rent_platform.promotion"),
        ("src/rent_prediction/model.py", "from rent_agent import tasks"),
        ("src/rent_agent/tool.py", "from rent_platform.execution import run"),
        ("src/rent_agent/tool.py", "import train"),
        ("src/rent_platform/runner.py", "import rent_prediction.adapters"),
        ("src/rent_platform/runner.py", "import features as safe_name"),
        ("src/rent_contracts/bad.py", "from rent_platform import admission"),
        ("train.py", "import rent_platform"),
        (
            "src/rent_prediction/model.py",
            "import importlib as loader\nloader.import_module('rent_platform')",
        ),
        (
            "src/rent_prediction/model.py",
            "from importlib import import_module as load\nload('rent_platform')",
        ),
        ("src/rent_prediction/model.py", "__import__('rent_platform')"),
        ("src/rent_prediction/model.py", "__import__(user_input)"),
        ("src/rent_prediction/model.py", "from ..rent_agent import tasks"),
    ],
)
def test_forbidden_imports_are_detected_without_execution(tmp_path, path, source):
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source + "\nraise RuntimeError('must never execute')\n")
    assert check_architecture(tmp_path), f"did not detect {path}"


def test_stdlib_platform_and_public_contracts_remain_available(tmp_path):
    source = tmp_path / "src/rent_prediction/model.py"
    source.parent.mkdir(parents=True)
    source.write_text("import platform\nfrom rent_contracts import validate_document\n")
    assert check_architecture(tmp_path) == []


def test_package_symlink_does_not_hide_uninspected_sources(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "model.py").write_text("raise RuntimeError('must not execute')\n")
    source = tmp_path / "src"
    source.mkdir()
    (source / "rent_prediction").symlink_to(outside, target_is_directory=True)
    violations = check_architecture(tmp_path)
    assert len(violations) == 1
    assert "symlink" in violations[0].rule
