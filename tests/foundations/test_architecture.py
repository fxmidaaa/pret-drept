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
        ("src/rent_contracts/bad.py", "import rent_data.candidates"),
        ("src/rent_data/bad.py", "from rent_agent import tasks"),
        ("src/rent_data/bad.py", "from rent_platform import datasets"),
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


def test_data_preparation_can_use_public_contracts_independently_of_harness(tmp_path):
    source = tmp_path / "src/rent_data/candidates.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from rent_contracts.evaluation import observation_inventory_digest\n"
        "from rent_contracts import ContractError\n"
    )
    assert check_architecture(tmp_path) == []


def _write_sources(root, sources):
    for path, code in sources.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code + "\nraise RuntimeError('must never execute')\n", encoding="utf-8")


def test_unclassified_bridge_reports_ownership_and_import_chain(tmp_path):
    _write_sources(
        tmp_path,
        {
            "src/rent_prediction/model.py": "# first line\nimport bridge",
            "bridge.py": "import rent_platform.promotion",
        },
    )
    violations = check_architecture(tmp_path)
    assert any(v.path == "bridge.py" and "unclassified" in v.rule for v in violations)
    assert any(
        v.path == "src/rent_prediction/model.py"
        and v.line == 2
        and "rent_prediction.model -> bridge -> rent_platform" in v.rule
        for v in violations
    )


@pytest.mark.parametrize(
    "link_path",
    ["src", "src/rent_prediction", "src/rent_prediction/nested", "src/rent_prediction/hidden.py"],
)
def test_source_symlinks_are_rejected_without_traversing_targets(tmp_path, link_path):
    root = tmp_path / "checkout"
    outside = tmp_path / "outside"
    _write_sources(outside, {"bridge.py": "import rent_platform.promotion"})
    link = root / link_path
    link.parent.mkdir(parents=True)
    is_directory = link.suffix != ".py"
    link.symlink_to(
        outside if is_directory else outside / "bridge.py", target_is_directory=is_directory
    )
    violations = check_architecture(root)
    assert [(v.path, v.rule) for v in violations] == [
        (link_path, "source symlink is not inspectable")
    ]


def test_forbidden_chain_through_classified_modules_with_cycle(tmp_path):
    _write_sources(
        tmp_path,
        {
            "src/rent_agent/tool.py": "from rent_data import bridge",
            "src/rent_data/bridge.py": "from . import helper",
            "src/rent_data/helper.py": "from . import bridge\nimport train",
            "train.py": "import features",
            "features.py": "",
        },
    )
    violations = check_architecture(tmp_path)
    assert len(violations) == 1
    assert violations[0].path == "src/rent_agent/tool.py"
    assert "rent_agent.tool -> rent_data.bridge -> rent_data.helper -> train" in violations[0].rule


def test_import_of_submodule_also_checks_package_initializer(tmp_path):
    _write_sources(
        tmp_path,
        {
            "src/rent_agent/tool.py": "import rent_data.clean",
            "src/rent_data/__init__.py": "import train",
            "src/rent_data/clean.py": "",
            "train.py": "",
        },
    )
    violations = check_architecture(tmp_path)
    assert len(violations) == 1
    assert "rent_agent.tool -> rent_data -> train" in violations[0].rule


@pytest.mark.parametrize(
    "statement",
    [
        "from src import rent_platform",
        "import src.rent_platform.promotion",
        "from builtins import __import__ as load\nload('rent_platform')",
        "import importlib.util\nimportlib.import_module('rent_platform')",
        "import importlib\nload = importlib.import_module",
        "__import__('promotion', level=1)",
    ],
)
def test_import_spellings_cannot_hide_loader_or_forbidden_dependency(tmp_path, statement):
    _write_sources(tmp_path, {"src/rent_prediction/model.py": statement})
    violations = check_architecture(tmp_path)
    assert len(violations) == 1
    assert any(term in violations[0].rule for term in ("forbidden", "not inspectable"))


def test_runtime_import_of_tooling_fails(tmp_path):
    _write_sources(
        tmp_path,
        {"src/rent_prediction/model.py": "import scripts.helper", "scripts/helper.py": ""},
    )
    assert any("forbidden" in v.rule for v in check_architecture(tmp_path))


def test_valid_relative_contract_and_legacy_imports(tmp_path):
    _write_sources(
        tmp_path,
        {
            "src/rent_agent/tool.py": "from rent_contracts import validation",
            "src/rent_contracts/__init__.py": "from .validation import validate_document",
            "src/rent_contracts/validation.py": "import json",
            "src/rent_prediction/nested/model.py": "from .. import adapter",
            "src/rent_prediction/adapter.py": "import platform",
            "api.py": "import predict",
            "predict.py": "import features",
            "features.py": "",
        },
    )
    assert check_architecture(tmp_path) == []
