"""Pinned public CLI for owned local development workspaces, not trusted admission."""

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rent_contracts import ContractError, load_document
from rent_contracts.validation import MAX_DOCUMENT_BYTES

from ._artifact_io import resolved_local_path
from .candidates import INLINE_VERSION, REFERENCE_VERSION
from .release_io import (
    _write_exclusive,
    finalize_restoration,
    payload_inventory,
    read_artifact,
    verify_payload,
)
from .releases import (
    DVC_VERSION,
    INVENTORY_MANIFEST_PATH,
    INVENTORY_PARQUET_PATH,
    ReleaseError,
    build_restoration_report,
    content_digest,
    validate_dataset_release,
)

_CONTROLLED_CONFIG = "[core]\nanalytics = false\ncheck_update = false\n[studio]\noffline = true\n"
_SAFE_ENV = ("PATH", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL", "SYSTEMROOT")


def parse_dvc_metadata(raw: bytes) -> dict:
    """Strict subset emitted by the pinned version for one local payload directory."""
    try:
        import yaml
    except ImportError:
        raise ReleaseError("DATA_EXTRA_UNAVAILABLE") from None
    if type(raw) is not bytes or len(raw) > MAX_DOCUMENT_BYTES or raw.startswith(b"\xef\xbb\xbf"):
        raise ContractError("invalid DVC metadata encoding or size")
    try:
        text = raw.decode("utf-8")
        if any(
            isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken))
            for token in yaml.scan(text)
        ):
            raise ContractError("DVC metadata aliases are unsupported")

        class UniqueLoader(yaml.SafeLoader):
            pass

        def mapping(loader, node, deep=False):
            result = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if type(key) is not str or key in result:
                    raise ContractError("ambiguous DVC metadata mapping")
                result[key] = loader.construct_object(value_node, deep=deep)
            return result

        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        document = yaml.load(text, Loader=UniqueLoader)
    except (UnicodeError, yaml.YAMLError, RecursionError):
        raise ContractError("invalid DVC metadata document") from None
    if type(document) is not dict or set(document) != {"outs"}:
        raise ContractError("unsupported DVC metadata fields")
    outs = document["outs"]
    if type(outs) is not list or len(outs) != 1 or type(outs[0]) is not dict:
        raise ContractError("unsupported DVC output population")
    out = outs[0]
    if set(out) != {"md5", "size", "nfiles", "hash", "path"}:
        raise ContractError("unsupported DVC output fields")
    if out["hash"] != "md5" or out["path"] != "payload":
        raise ContractError("unsupported DVC output hash or path")
    if type(out["md5"]) is not str or re.fullmatch(r"[a-f0-9]{32}\.dir", out["md5"]) is None:
        raise ContractError("invalid DVC directory identity")
    if any(type(out[key]) is not int or out[key] < 1 for key in ("size", "nfiles")):
        raise ContractError("invalid DVC output totals")
    return {"object_id": out["md5"], "size_bytes": out["size"], "file_count": out["nfiles"]}


def _local_directory(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ReleaseError("INVALID_LOCAL_STORE")
    if any(character in str(path) for character in ("\x00", "\n", "\r")):
        raise ReleaseError("INVALID_LOCAL_STORE")
    return path.resolve()


@dataclass(frozen=True)
class LocalWorkspace:
    root: Path
    store: Path
    config_digests: tuple[tuple[str, str], ...]


class LocalDvcStore:
    """Local-only adapter. Workspace objects are context, never authorization.

    It creates fresh owned workspaces, uses public CLI calls and reads committed
    metadata. It never commits a caller's Git repository or runs DVC pipelines.
    """

    def __init__(self, executable: Path, *, tool_profile_ref: str, timeout_seconds: float = 45):
        executable = Path(executable)
        if not executable.is_absolute() or not executable.is_file():
            raise ReleaseError("TOOL_UNAVAILABLE")
        if (
            type(tool_profile_ref) is not str
            or re.fullmatch(r"sha256:[a-f0-9]{64}", tool_profile_ref) is None
        ):
            raise ContractError("invalid data tool profile identity")
        if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 120:
            raise ContractError("invalid local tool timeout")
        git = shutil.which("git")
        if git is None:
            raise ReleaseError("GIT_UNAVAILABLE")
        self.executable = executable
        self.git = Path(git)
        self.tool_profile_ref = tool_profile_ref
        self.timeout_seconds = timeout_seconds

    def _environment(self, root: Path) -> dict[str, str]:
        control = root / ".control"
        environment = {name: os.environ[name] for name in _SAFE_ENV if name in os.environ}
        environment.update(
            DVC_GLOBAL_CONFIG_DIR=str(control / "global"),
            DVC_SYSTEM_CONFIG_DIR=str(control / "system"),
            DVC_SITE_CACHE_DIR=str(control / "site"),
            DVC_NO_ANALYTICS="1",
            DVC_STUDIO_OFFLINE="1",
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=str(control / "git-config"),
            PYTHONDONTWRITEBYTECODE="1",
        )
        return environment

    def _execute(self, executable: Path, arguments: list[str], root: Path) -> bytes:
        try:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                result = subprocess.run(
                    [str(executable), *arguments],
                    cwd=root,
                    env=self._environment(root),
                    stdout=output,
                    stderr=errors,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                if result.returncode:
                    raise ReleaseError("PROCESS_FAILED", exit_code=result.returncode)
                output.seek(0)
                raw = output.read(MAX_DOCUMENT_BYTES + 1)
                if len(raw) > MAX_DOCUMENT_BYTES:
                    raise ReleaseError("TOOL_OUTPUT_LIMIT")
                return raw
        except subprocess.TimeoutExpired:
            raise ReleaseError("PROCESS_TIMEOUT") from None
        except OSError:
            raise ReleaseError("TOOL_UNAVAILABLE") from None

    def create_workspace(self, root: Path, *, store: Path) -> LocalWorkspace:
        root = Path(root)
        store = _local_directory(store)
        if not root.is_absolute() or root.parent.is_symlink() or not root.parent.is_dir():
            raise ReleaseError("INVALID_DIRECTORY")
        resolved = root.resolve()
        if resolved == store or resolved in store.parents or store in resolved.parents:
            raise ReleaseError("OVERLAPPING_STORE_WORKSPACE")
        try:
            root.mkdir(mode=0o700)
        except FileExistsError:
            raise ReleaseError("OUTPUT_EXISTS") from None
        except OSError:
            raise ReleaseError("WORKSPACE_WRITE_FAILED") from None
        root = root.resolve()
        try:
            for name in ("global", "system", "site"):
                (root / ".control" / name).mkdir(parents=True, mode=0o700)
        except OSError:
            raise ReleaseError("WORKSPACE_WRITE_FAILED") from None
        _write_exclusive(root / ".control/global/config", _CONTROLLED_CONFIG.encode())
        _write_exclusive(root / ".control/git-config", b"")
        if self._execute(self.executable, ["--version"], root).strip() != DVC_VERSION.encode():
            raise ReleaseError("TOOL_VERSION_MISMATCH")
        self._execute(self.git, ["init", "--quiet"], root)
        for arguments in (
            ["init", "--quiet"],
            ["config", "--local", "cache.type", "copy"],
            ["config", "--local", "cache.dir", str(root / ".dvc/cache")],
            ["remote", "add", "--local", "local-store", str(store)],
        ):
            self._execute(self.executable, arguments, root)
        configs = (
            ".dvc/config",
            ".dvc/config.local",
            ".dvcignore",
            ".git/config",
            ".control/global/config",
            ".control/git-config",
        )
        fingerprints = tuple((path, content_digest(read_artifact(root / path))) for path in configs)
        return LocalWorkspace(root, store, fingerprints)

    def _guard(self, workspace: LocalWorkspace) -> None:
        if (
            _local_directory(workspace.root) != workspace.root
            or _local_directory(workspace.store) != workspace.store
        ):
            raise ReleaseError("WORKSPACE_CONFIGURATION_CHANGED")
        if (workspace.root / ".git").is_symlink() or not (workspace.root / ".git").is_dir():
            raise ReleaseError("WORKSPACE_CONFIGURATION_CHANGED")
        for path, expected in workspace.config_digests:
            if content_digest(read_artifact(workspace.root / path)) != expected:
                raise ReleaseError("WORKSPACE_CONFIGURATION_CHANGED")

    def track_payload(
        self, workspace: LocalWorkspace, *, contract_version: str = INLINE_VERSION
    ) -> dict:
        self._guard(workspace)
        artifacts = payload_inventory(workspace.root / "payload", contract_version=contract_version)
        if contract_version == REFERENCE_VERSION:
            paths = {artifact["path"] for artifact in artifacts}
            required = {
                "candidate.json",
                "quality-report.json",
                INVENTORY_MANIFEST_PATH,
                INVENTORY_PARQUET_PATH,
            }
            if not required < paths:
                raise ReleaseError("INCOMPLETE_PAYLOAD")
        existing = workspace.root / "payload.dvc"
        if existing.exists() or existing.is_symlink():
            parse_dvc_metadata(read_artifact(existing))
        self._execute(self.executable, ["add", "payload"], workspace.root)
        metadata = parse_dvc_metadata(read_artifact(workspace.root / "payload.dvc"))
        if metadata["file_count"] != len(artifacts) or metadata["size_bytes"] != sum(
            row["size_bytes"] for row in artifacts
        ):
            raise ReleaseError("DVC_PAYLOAD_TOTALS_MISMATCH")
        return metadata

    def _committed_binding(self, workspace: LocalWorkspace, commit: str) -> tuple[dict, bytes]:
        self._guard(workspace)
        if (
            type(commit) is not str
            or re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", commit) is None
        ):
            raise ContractError("invalid exact Git metadata revision")
        resolved = self._execute(
            self.git, ["rev-parse", "--verify", f"{commit}^{{commit}}"], workspace.root
        ).strip()
        if resolved != commit.encode():
            raise ReleaseError("GIT_METADATA_REVISION_MISMATCH")
        raw = self._execute(
            self.git, ["--no-pager", "show", f"{commit}:payload.dvc"], workspace.root
        )
        metadata = parse_dvc_metadata(raw)
        return {
            "metadata": {"commit": commit, "path": "payload.dvc", "digest": content_digest(raw)},
            "dvc": {
                "version": DVC_VERSION,
                "hash_algorithm": "md5",
                **metadata,
                "tool_profile_ref": self.tool_profile_ref,
            },
        }, raw

    def metadata_binding(self, workspace: LocalWorkspace, commit: str) -> dict:
        return self._committed_binding(workspace, commit)[0]

    def push(self, workspace: LocalWorkspace, manifest: dict, *, expected_release_ref: str) -> None:
        validate_dataset_release(manifest, expected_release_ref=expected_release_ref)
        binding, raw = self._committed_binding(workspace, manifest["metadata"]["commit"])
        if binding != {"metadata": manifest["metadata"], "dvc": manifest["dvc"]}:
            raise ReleaseError("DVC_BINDING_MISMATCH")
        if read_artifact(workspace.root / "payload.dvc") != raw:
            raise ReleaseError("DVC_BINDING_MISMATCH")
        verify_payload(
            manifest, workspace.root / "payload", expected_release_ref=expected_release_ref
        )
        if manifest["contract_version"] == REFERENCE_VERSION:
            status = self._execute(
                self.executable, ["status", "--json", "payload.dvc"], workspace.root
            )
            if load_document(status):
                raise ReleaseError("DVC_PAYLOAD_CHANGED")
        self._execute(
            self.executable, ["push", "-j", "1", "-r", "local-store", "payload.dvc"], workspace.root
        )

    def restore(
        self,
        manifest: dict,
        *,
        metadata_workspace: LocalWorkspace,
        destination: Path,
        expected_release_ref: str,
    ) -> dict:
        validate_dataset_release(manifest, expected_release_ref=expected_release_ref)
        if manifest["contract_version"] == REFERENCE_VERSION:
            destination = resolved_local_path(destination)
        else:
            destination = Path(destination)
        if destination.exists() or destination.is_symlink():
            raise ReleaseError("OUTPUT_EXISTS")
        binding, raw = self._committed_binding(metadata_workspace, manifest["metadata"]["commit"])
        if binding != {"metadata": manifest["metadata"], "dvc": manifest["dvc"]}:
            raise ReleaseError("DVC_BINDING_MISMATCH")
        consumer = self.create_workspace(destination, store=metadata_workspace.store)
        self._guard(consumer)
        cache = consumer.root / ".dvc/cache"
        if cache.exists() and any(cache.iterdir()):
            raise ReleaseError("RESTORE_CACHE_NOT_EMPTY")
        _write_exclusive(consumer.root / "payload.dvc", raw)
        self._execute(
            self.executable, ["pull", "-j", "1", "-r", "local-store", "payload.dvc"], consumer.root
        )
        report = build_restoration_report(manifest)
        finalize_restoration(
            consumer.root, report, manifest=manifest, expected_release_ref=expected_release_ref
        )
        return report
