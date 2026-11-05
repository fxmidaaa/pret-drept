import io

import pytest

from scripts import install_actionlint as installer


def test_corrupt_download_preserves_existing_executable(tmp_path, monkeypatch):
    destination = tmp_path / "actionlint"
    destination.write_bytes(b"previous executable")
    monkeypatch.setattr(installer.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(installer.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(installer, "urlopen", lambda *args, **kwargs: io.BytesIO(b"corrupt"))

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        installer.install_actionlint(tmp_path)

    assert destination.read_bytes() == b"previous executable"
    assert list(tmp_path.iterdir()) == [destination]


def test_unsupported_platform_fails_before_download(tmp_path, monkeypatch):
    monkeypatch.setattr(installer.platform, "system", lambda: "Unsupported")

    def reject_download(*args, **kwargs):
        pytest.fail("unsupported platforms must not download or execute a tool")

    monkeypatch.setattr(installer, "urlopen", reject_download)
    destination = tmp_path / "tools"
    with pytest.raises(ValueError, match="unsupported actionlint platform"):
        installer.install_actionlint(destination)
    assert not destination.exists()
