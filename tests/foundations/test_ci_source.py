import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.install_actionlint import VERSION

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/validate.yml"


@pytest.fixture(scope="module")
def actionlint():
    executable = Path(
        os.environ.get("ACTIONLINT", str(Path(sys.executable).with_name("actionlint")))
    )
    if not executable.is_file():
        pytest.fail(
            "Pinned actionlint is required: run python scripts/install_actionlint.py "
            "--directory .venv/bin, or set ACTIONLINT to its installed path"
        )
    result = subprocess.run(
        [str(executable), "-version"], capture_output=True, text=True, timeout=10, check=True
    )
    assert result.stdout.splitlines()[0] == VERSION, "Install the pinned actionlint version"
    return str(executable)


def test_all_workflows_pass_pinned_semantic_validation(actionlint):
    workflows = sorted(
        path for path in (ROOT / ".github/workflows").iterdir() if path.suffix in {".yml", ".yaml"}
    )
    assert workflows, "at least one workflow must be validated"
    result = subprocess.run(
        [actionlint, "-oneline", "-shellcheck=", "-pyflakes=", *map(str, workflows)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("name", ["MPLCONFIGDIR", "NUMBA_CACHE_DIR", "RENT_DATA_DVC"])
def test_runner_directory_in_job_environment_is_rejected(actionlint, name):
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["foundations"]
    step = next(step for step in job["steps"] if name in step.get("env", {}))
    job["env"][name] = step["env"].pop(name)
    result = subprocess.run(
        [actionlint, "-oneline", "-shellcheck=", "-pyflakes=", "-"],
        input=yaml.safe_dump(workflow, sort_keys=False),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'context "runner" is not allowed here' in result.stdout
    assert result.stdout.count("[expression]") == 1


def test_unprivileged_workflow_source_has_no_privileged_trigger_or_credentials():
    raw = WORKFLOW.read_text()
    workflow = yaml.load(raw, Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"pull_request", "push"}
    assert workflow["permissions"] == {"contents": "read"}
    assert "secrets." not in raw
    assert "id-token" not in raw
    assert "pull_request_target" not in raw
    job = workflow["jobs"]["foundations"]
    assert int(job["timeout-minutes"]) <= 15
    for step in job["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"actions/[a-z-]+@[a-f0-9]{40}", step["uses"])
    checkout = job["steps"][0]
    assert checkout["with"]["persist-credentials"] == "false"
    assert "--require-hashes" in raw
