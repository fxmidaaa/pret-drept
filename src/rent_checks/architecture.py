"""Inspect Python imports without importing or executing application code (§4.3/16.5)."""

import argparse
import ast
import os
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

_LEGACY = {"features", "train", "predict", "api"}
_DOMAINS = {
    "rent_prediction": "ml",
    "rent_agent": "agent",
    "rent_platform": "platform",
    "rent_contracts": "contracts",
    "rent_domain": "contracts",
    "rent_data": "data",
    "rent_checks": "tooling",
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


_TOOLING = {"scripts", "tests", "rent_checks"}
_ARTIFACT_DIRS = {"build", "data", "dist", "venv"}


@dataclass(frozen=True)
class _Source:
    path: Path
    domain: str | None
    package: str


def _inventory(root: Path, violations: list[Violation]) -> dict[str, _Source]:
    sources: dict[str, _Source] = {}

    def walk_error(error: OSError) -> None:
        path = Path(error.filename) if error.filename else root
        violations.append(Violation(path.relative_to(root).as_posix(), 1, "unreadable source tree"))

    for directory, dirs, files in os.walk(root, onerror=walk_error, followlinks=False):
        parent = Path(directory)
        subdirectories = []
        for name in sorted(dirs):
            if (
                name.startswith(".")
                or name == "__pycache__"
                or name.endswith(".egg-info")
                or (parent == root and name in _ARTIFACT_DIRS)
            ):
                continue
            if (parent / name).is_symlink():
                path = (parent / name).relative_to(root).as_posix()
                violations.append(Violation(path, 1, "source symlink is not inspectable"))
            else:
                subdirectories.append(name)
        dirs[:] = subdirectories

        for name in sorted(files):
            path = (parent / name).relative_to(root)
            if (root / path).is_symlink():
                if not name.startswith(".") and not (parent == root and name in _ARTIFACT_DIRS):
                    violations.append(
                        Violation(path.as_posix(), 1, "source symlink is not inspectable")
                    )
                continue
            if path.suffix != ".py":
                continue
            parts = path.with_suffix("").parts
            if parts[0] == "src":
                parts = parts[1:]
                domain = _DOMAINS.get(parts[0]) if len(parts) > 1 else None
            elif parts[0] in {"scripts", "tests"} and len(parts) > 1:
                domain = "tooling"
            elif len(parts) == 1 and parts[0] in _LEGACY:
                domain = "ml"
            else:
                domain = "data" if parts == ("scrape",) else None

            is_package = parts[-1] == "__init__"
            module_parts = parts[:-1] if is_package else parts
            if not module_parts or not all(part.isidentifier() for part in module_parts):
                violations.append(Violation(path.as_posix(), 1, "invalid project module identity"))
                continue
            if domain is None:
                violations.append(Violation(path.as_posix(), 1, "unclassified project source"))
            module = ".".join(module_parts)
            if module in sources:
                violations.append(
                    Violation(path.as_posix(), 1, "ambiguous project module identity")
                )
                continue
            package = module if is_package else module.rpartition(".")[0]
            sources[module] = _Source(path, domain, package)
    return sources


def _prefixes(module: str):
    parts = module.split(".")
    for end in range(1, len(parts) + 1):
        yield ".".join(parts[:end])


def _is_loader(node: ast.AST, attributes: set[tuple[str, str]], loaders: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in loaders
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return (node.value.id, node.attr) in attributes
    return False


def _import_edges(
    tree: ast.AST, source: _Source, local: set[str], violations: list[Violation]
) -> dict[str, int]:
    attributes: set[tuple[str, str]] = set()
    loader_modules = {"importlib": "import_module", "builtins": "__import__"}
    loaders = {"__import__"}
    nodes = list(ast.walk(tree))
    for node in nodes:
        if isinstance(node, ast.Import):
            for item in node.names:
                top = item.name.split(".")[0]
                imported = item.name if item.asname else top
                if imported in loader_modules:
                    attributes.add((item.asname or top, loader_modules[imported]))
        elif isinstance(node, ast.ImportFrom) and not node.level:
            for item in node.names:
                if item.name == loader_modules.get(node.module):
                    loaders.add(item.asname or item.name)

    direct_loaders = {
        node.func
        for node in nodes
        if isinstance(node, ast.Call) and _is_loader(node.func, attributes, loaders)
    }
    edges: dict[str, int] = {}

    def reject(line: int, reason: str) -> None:
        violations.append(Violation(source.path.as_posix(), line, reason))

    def add(module: str, line: int) -> None:
        for dependency in _prefixes(module.removeprefix("src.")):
            edges.setdefault(dependency, line)

    for node in nodes:
        if isinstance(node, ast.Import):
            for item in node.names:
                add(item.name, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = source.package.split(".") if source.package else []
                if node.level > len(parts):
                    reject(node.lineno, "relative import escapes package")
                    continue
                package = ".".join(parts[: len(parts) - node.level + 1])
                base = f"{package}.{base}" if base else package
            add(base, node.lineno)
            for item in node.names:
                child = f"{base}.{item.name}"
                if item.name == "*" and (
                    base == "src" or base in loader_modules or base.removeprefix("src.") in local
                ):
                    reject(node.lineno, "wildcard import is not inspectable")
                elif base == "src" or child.removeprefix("src.") in local:
                    add(child, node.lineno)
        elif isinstance(node, ast.Call) and node.func in direct_loaders:
            if (
                len(node.args) != 1
                or node.keywords
                or not isinstance(node.args[0], ast.Constant)
                or not isinstance(node.args[0].value, str)
                or not all(part.isidentifier() for part in node.args[0].value.split("."))
            ):
                reject(node.lineno, "dynamic import target is not inspectable")
            else:
                add(node.args[0].value, node.lineno)
        elif _is_loader(node, attributes, loaders) and node not in direct_loaders:
            reject(node.lineno, "indirect dynamic loader is not inspectable")
    return edges


def _forbidden_chains(
    sources: dict[str, _Source], graph: dict[str, dict[str, int]]
) -> list[Violation]:
    incoming: dict[str, list[str]] = defaultdict(list)
    for module, dependencies in graph.items():
        for dependency in dependencies:
            incoming[dependency].append(module)

    violations = []
    for domain, forbidden in _FORBIDDEN.items():
        # A reverse search finds one shortest chain per source for this policy.
        targets = forbidden | _TOOLING | _ARTIFACT_DIRS
        next_hop: dict[str, str | None] = {
            module: None for module in incoming if module.partition(".")[0] in targets
        }
        queue = deque(next_hop)
        while queue:
            dependency = queue.popleft()
            for importer in incoming[dependency]:
                if importer not in next_hop:
                    next_hop[importer] = dependency
                    queue.append(importer)
        for module, source in sources.items():
            if source.domain != domain or (dependency := next_hop.get(module)) is None:
                continue
            chain = [module, dependency]
            while (dependency := next_hop[dependency]) is not None:
                chain.append(dependency)
            violations.append(
                Violation(
                    source.path.as_posix(),
                    graph[module][chain[1]],
                    "forbidden cross-domain import: " + " -> ".join(chain),
                )
            )
    return violations


def check_architecture(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    sources = _inventory(root, violations)
    local = {prefix for module in sources for prefix in _prefixes(module)}
    graph = {}
    for module, source in sources.items():
        path = root / source.path
        try:
            if not path.is_file():
                raise OSError
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=source.path.as_posix())
        except (OSError, SyntaxError, UnicodeError):
            violations.append(Violation(source.path.as_posix(), 1, "source cannot be parsed"))
            continue
        graph[module] = _import_edges(tree, source, local, violations)
    violations.extend(_forbidden_chains(sources, graph))
    return sorted(
        violations, key=lambda violation: (violation.path, violation.line, violation.rule)
    )


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
