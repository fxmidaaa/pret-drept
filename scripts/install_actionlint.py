"""Explicitly install the pinned development-only workflow validator (macOS/Linux)."""

import argparse
import hashlib
import io
import platform
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

VERSION = "1.7.12"
# https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_checksums.txt
ARCHIVE_SHA256 = {
    "darwin_amd64": "5b44c3bc2255115c9b69e30efc0fecdf498fdb63c5d58e17084fd5f16324c644",
    "darwin_arm64": "aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f",
    "linux_amd64": "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
    "linux_arm64": "325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6",
}


def install_actionlint(directory: Path) -> Path:
    machine = platform.machine().lower()
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(machine, machine)
    target = f"{platform.system().lower()}_{architecture}"
    if target not in ARCHIVE_SHA256:
        raise ValueError(f"unsupported actionlint platform: {target}")
    url = (
        f"https://github.com/rhysd/actionlint/releases/download/v{VERSION}/"
        f"actionlint_{VERSION}_{target}.tar.gz"
    )
    with urlopen(url, timeout=30) as response:
        data = response.read(16 * 1024 * 1024 + 1)
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256[target]:
        raise ValueError("actionlint archive SHA-256 mismatch; installation refused")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        member = archive.getmember("actionlint")
        if not member.isfile():
            raise ValueError("actionlint archive entry must be a regular file")
        with archive.extractfile(member) as stream:
            executable = stream.read()

    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "actionlint"
    with tempfile.TemporaryDirectory(prefix=".actionlint-", dir=directory) as staging:
        temporary = Path(staging) / "actionlint"
        temporary.write_bytes(executable)
        temporary.chmod(0o755)
        temporary.replace(destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        destination = install_actionlint(arguments.directory)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, f"actionlint installation failed: {error}\n")
    print(f"Installed actionlint {VERSION} with verified archive SHA-256: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
