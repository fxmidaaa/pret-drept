"""Inspect Python imports without importing or executing application code (§4.3/16.5)."""

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

_LEGACY = {"features", "train", "predict", "api"}
_DOMAINS = {
    "rent_prediction": "ml",
    "rent_agent": "agent",
    "rent_platform": "platform",
    "rent_contracts": "contracts",
    "rent_data": "data",
}
_FORBIDDEN = {
    "ml": {"rent_agent", "rent_platform", "agent"},
    "agent": {"rent_platform", "rent_prediction", *_LEGACY},
    "platform": {"rent_prediction", "rent_agent", "scrape", *_LEGACY},
    "contracts": {"rent_prediction", "rent_agent", "rent_platform", "rent_data", *_LEGACY},
    "data": {"rent_agent", "rent_platform"},
}


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    rule: str


def _source_files(root: Path):
    for name in sorted(_LEGACY | {"scrape"}):
        path = root / f"{name}.py"
        if path.is_file():
            yield path, "data" if name == "scrape" else "ml"
    for package, domain in _DOMAINS.items():
        directory = root / "src" / package
        if directory.is_symlink():
            yield directory, domain
            continue
        if directory.is_dir():
            for path in sorted(directory.rglob("*.py")):
                yield path, domain


def check_architecture(root: Path) -> list[Violation]:
    violations = []
    for path, domain in _source_files(root):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            violations.append(Violation(relative, 1, "source symlink is not inspectable"))
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (SyntaxError, UnicodeError):
            violations.append(Violation(relative, 1, "source cannot be parsed"))
            continue
        aliases = {}
        dynamic_loaders = {"__import__"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    aliases[item.asname or item.name.split(".")[0]] = item.name
            elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
                for item in node.names:
                    if item.name == "import_module":
                        dynamic_loaders.add(item.asname or item.name)
        for node in ast.walk(tree):
            dependencies = []
            if isinstance(node, ast.Import):
                dependencies = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    # Relative imports stay within this package unless they escape it.
                    depth = (
                        len(path.relative_to(root / "src").parts) - 1 if "src" in path.parts else 0
                    )
                    if node.level > depth:
                        violations.append(
                            Violation(relative, node.lineno, "relative import escapes package")
                        )
                elif node.module:
                    dependencies = [node.module]
            elif isinstance(node, ast.Call):
                target = node.func
                is_loader = isinstance(target, ast.Name) and target.id in dynamic_loaders
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                    is_loader |= (
                        aliases.get(target.value.id) == "importlib"
                        and target.attr == "import_module"
                    )
                if is_loader:
                    if (
                        not node.args
                        or not isinstance(node.args[0], ast.Constant)
                        or not isinstance(node.args[0].value, str)
                    ):
                        violations.append(
                            Violation(
                                relative, node.lineno, "dynamic import target is not inspectable"
                            )
                        )
                    else:
                        dependencies = [node.args[0].value]
            for dependency in dependencies:
                if dependency.split(".")[0] in _FORBIDDEN[domain]:
                    violations.append(
                        Violation(relative, node.lineno, "forbidden cross-domain import")
                    )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    if not (arguments.root / "pyproject.toml").is_file():
        parser.error("root must identify this project's source checkout")
    violations = check_architecture(arguments.root.resolve())
    for violation in violations:
        print(f"{violation.path}:{violation.line}: {violation.rule}")
    if not violations:
        print("Architecture dependency checks passed (runtime isolation is not assessed).")
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
