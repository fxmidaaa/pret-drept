import re
from pathlib import Path

import yaml


def test_unprivileged_workflow_source_has_no_privileged_trigger_or_credentials():
    path = Path(__file__).resolve().parents[2] / ".github/workflows/validate.yml"
    raw = path.read_text()
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
