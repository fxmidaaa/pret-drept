"""Local adapter rejection paths; real DVC successes live in checkout integration."""

import sys
from pathlib import Path

import pytest

from rent_contracts import ContractError
from rent_contracts.validation import MAX_DOCUMENT_BYTES
from rent_data.dvc_local import LocalDvcStore, parse_dvc_metadata
from rent_data.releases import ReleaseError, content_digest

METADATA = b"outs:\n- md5: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.dir\n  size: 120\n  nfiles: 4\n  hash: md5\n  path: payload\n"


def test_parse_pinned_local_directory_metadata_preserves_native_hash():
    assert parse_dvc_metadata(METADATA) == {
        "object_id": "a" * 32 + ".dir",
        "size_bytes": 120,
        "file_count": 4,
    }


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"[]",
        b"null",
        b"outs: []",
        b"outs: [1]",
        b"\xff",
        b"\xef\xbb\xbf" + METADATA,
        METADATA + b"outs: []\n",
        METADATA + b"---\nouts: []\n",
        b"outs: &output []\nother: *output\n",
        b"!!python/object:builtins.object {}",
        METADATA + b"deps: []\n",
        METADATA + b"repo: {}\n",
        METADATA.replace(b"  hash: md5", b"  hash: md5\n  remote: cloud"),
        METADATA.replace(b"  hash: md5", b"  hash: md5\n  path: payload"),
        METADATA.replace(b"path: payload", b"path: ../payload"),
        METADATA.replace(b"path: payload", b"path: /tmp/payload"),
        METADATA.replace(b"hash: md5", b"hash: sha256"),
        METADATA.replace(b"size: 120", b"size: true"),
        METADATA.replace(b"size: 120", b"size: 0"),
        METADATA.replace(b"nfiles: 4", b"nfiles: -1"),
        METADATA.replace(b"nfiles: 4", b"nfiles: '4'"),
        METADATA.replace(b".dir", b".file"),
        METADATA.replace(b"aaaaaaaa", b"AAAAAAAA"),
        b" " * (MAX_DOCUMENT_BYTES + 1),
        "outs: []",
    ],
)
def test_unsupported_or_ambiguous_metadata_is_rejected_before_dvc(raw):
    with pytest.raises(ContractError):
        parse_dvc_metadata(raw)


def adapter(**kwargs):
    return LocalDvcStore(
        Path(sys.executable), tool_profile_ref=content_digest(b"fixture"), **kwargs
    )


@pytest.mark.parametrize("timeout", [0, -1, 121, float("nan"), float("inf"), True, "5"])
def test_timeout_must_be_finite_positive_and_bounded(timeout):
    with pytest.raises(ContractError):
        adapter(timeout_seconds=timeout)


@pytest.mark.parametrize("profile", [None, True, "/private/path", "sha256:" + "a" * 64 + "\n"])
def test_tool_identity_must_be_exact(profile):
    with pytest.raises(ContractError):
        LocalDvcStore(Path(sys.executable), tool_profile_ref=profile)


def test_missing_tool_fails_without_installing(tmp_path):
    with pytest.raises(ReleaseError, match="TOOL_UNAVAILABLE"):
        LocalDvcStore(tmp_path / "absent", tool_profile_ref=content_digest(b"fixture"))


def test_wrong_version_stops_before_git_or_dvc_initialization(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    root = tmp_path / "workspace"
    # Python --version is intentionally not the pinned DVC version.
    with pytest.raises(ReleaseError, match="TOOL_VERSION_MISMATCH"):
        adapter().create_workspace(root, store=store)
    assert not (root / ".git").exists()
    assert not (root / ".dvc").exists()
    assert not (root / "restoration-report.json").exists()


def test_process_failure_exit_code_and_private_output_are_handled_safely(tmp_path):
    with pytest.raises(ReleaseError, match="PROCESS_FAILED") as failure:
        adapter()._execute(
            Path(sys.executable),
            ["-c", "import sys; print('private-output'); sys.exit(7)"],
            tmp_path,
        )
    assert failure.value.exit_code == 7
    assert "private-output" not in str(failure.value)


def test_process_timeout_and_disappearing_executable_have_safe_failures(tmp_path):
    with pytest.raises(ReleaseError, match="PROCESS_TIMEOUT"):
        adapter(timeout_seconds=0.1)._execute(
            Path(sys.executable), ["-c", "import time; time.sleep(10)"], tmp_path
        )
    with pytest.raises(ReleaseError, match="TOOL_UNAVAILABLE"):
        adapter()._execute(tmp_path / "missing", [], tmp_path)


def test_cli_output_limit_does_not_disclose_output(tmp_path):
    with pytest.raises(ReleaseError, match="TOOL_OUTPUT_LIMIT"):
        adapter()._execute(
            Path(sys.executable), ["-c", f"print('x' * {MAX_DOCUMENT_BYTES + 1})"], tmp_path
        )


def test_environment_drops_caller_dvc_git_and_credential_overrides(tmp_path, monkeypatch):
    for name in (
        "DVC_REMOTE",
        "DVC_GLOBAL_CONFIG_DIR",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_COUNT",
        "AWS_SECRET_ACCESS_KEY",
        "PYTHONPATH",
        "HTTP_PROXY",
    ):
        monkeypatch.setenv(name, "synthetic-untrusted-value")
    environment = adapter()._environment(tmp_path)
    assert environment["DVC_GLOBAL_CONFIG_DIR"] == str(tmp_path / ".control/global")
    assert environment["GIT_CONFIG_GLOBAL"] == str(tmp_path / ".control/git-config")
    assert environment["DVC_STUDIO_OFFLINE"] == "1"
    assert (
        not {"DVC_REMOTE", "GIT_CONFIG_COUNT", "AWS_SECRET_ACCESS_KEY", "PYTHONPATH", "HTTP_PROXY"}
        & environment.keys()
    )


@pytest.mark.parametrize("kind", ["relative", "symlink", "overlap", "existing"])
def test_workspace_and_store_paths_are_explicit_and_nonoverlapping(tmp_path, kind):
    store = tmp_path / "store"
    store.mkdir()
    root = tmp_path / "workspace"
    if kind == "relative":
        store = Path("relative-store")
    elif kind == "symlink":
        link = tmp_path / "store-link"
        link.symlink_to(store, target_is_directory=True)
        store = link
    elif kind == "overlap":
        root = store / "workspace"
    else:
        root.mkdir()
        (root / "preserve").write_bytes(b"existing")
    with pytest.raises(ReleaseError):
        adapter().create_workspace(root, store=store)
    if kind == "existing":
        assert (root / "preserve").read_bytes() == b"existing"


def test_unsafe_committed_metadata_never_reaches_dvc(tmp_path, monkeypatch):
    store = adapter()
    raw = METADATA.replace(
        b"  path: payload", b"  path: payload\n  remote: https://invalid.example"
    )
    calls = []
    monkeypatch.setattr(store, "_guard", lambda workspace: None)

    def execute(executable, arguments, root):
        calls.append(arguments)
        if arguments[0] == "rev-parse":
            return ("a" * 40).encode()
        assert arguments[0] == "--no-pager"
        return raw

    monkeypatch.setattr(store, "_execute", execute)
    from rent_data.dvc_local import LocalWorkspace

    workspace = LocalWorkspace(tmp_path, tmp_path / "store", ())
    with pytest.raises(ContractError):
        store.metadata_binding(workspace, "a" * 40)
    assert len(calls) == 2  # Only Git metadata reads, no DVC operation.


def test_existing_unsupported_metadata_is_rejected_before_retracking(release_case, monkeypatch):
    from rent_data.dvc_local import LocalWorkspace

    store = adapter()
    root = release_case["root"].parent
    (root / "payload.dvc").write_bytes(METADATA + b"deps: []\n")
    monkeypatch.setattr(store, "_guard", lambda workspace: None)

    def unexpected(*args):
        pytest.fail("unsupported existing metadata must not reach a subprocess")

    monkeypatch.setattr(store, "_execute", unexpected)
    with pytest.raises(ContractError):
        store.track_payload(LocalWorkspace(root, root / "store", ()))
