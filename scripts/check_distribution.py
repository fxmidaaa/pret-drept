"""Build the foundations release and exercise its shipped tests in both forms."""

import os
import subprocess
import sys
import sysconfig
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def _test_distribution(source: Path, *, wheel: Path | None = None) -> None:
    # Skip site initialization so the checkout's editable-install .pth file cannot run.
    pythonpath = sorted({sysconfig.get_path(name) for name in ("purelib", "platlib")})
    if wheel is not None:
        pythonpath.insert(0, str(wheel))
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        environment.pop(name, None)
    environment.update(
        PYTHONPATH=os.pathsep.join(pythonpath),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    source_path = "src" if wheel is None else ""
    pytest_args = ["-q", "-ra", "-p", "no:cacheprovider", "-o", f"pythonpath={source_path}"]
    print(f"Testing {wheel.name if wheel else 'the extracted source distribution'}", flush=True)
    subprocess.run(
        [sys.executable, "-S", "-P", "-m", "pytest", *pytest_args],
        cwd=source,
        env=environment,
        check=True,
    )


def main() -> None:
    with TemporaryDirectory(prefix="rent-distribution-") as directory:
        work = Path(directory).resolve()
        dist = work / "dist"
        subprocess.run(
            [sys.executable, "-I", "-m", "build", "--no-isolation", "--outdir", str(dist)],
            cwd=ROOT,
            check=True,
        )
        (sdist,) = dist.glob("*.tar.gz")
        (wheel,) = dist.glob("*.whl")
        unpacked = work / "unpacked"
        with tarfile.open(sdist) as archive:
            archive.extractall(unpacked, filter="data")
        (source,) = unpacked.iterdir()
        _test_distribution(source)
        _test_distribution(source, wheel=wheel)


if __name__ == "__main__":
    main()
