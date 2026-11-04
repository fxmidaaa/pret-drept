import json
import subprocess

import pytest

from scripts.check_notebooks import _notebook_issue, check_notebooks


@pytest.fixture
def notebook():
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
        "cells": [
            {
                "cell_type": "code",
                "id": "example",
                "metadata": {},
                "source": ["print('local preview')"],
                "outputs": [],
                "execution_count": None,
            }
        ],
    }


@pytest.mark.parametrize(
    "state, issue",
    [
        (
            {"outputs": [{"output_type": "stream", "text": "synthetic-private-row"}]},
            "cell 1 has saved output",
        ),
        (
            {"outputs": [{"output_type": "display_data", "data": {"image/png": "test"}}]},
            "cell 1 has saved output",
        ),
        ({"execution_count": 1}, "cell 1 has a saved execution count"),
        ({"attachments": {"example": {"text/plain": "test"}}}, "cell 1 has embedded attachments"),
    ],
)
def test_saved_cell_state_is_rejected(tmp_path, notebook, state, issue):
    notebook["cells"][0].update(state)
    path = tmp_path / "example.ipynb"
    path.write_text(json.dumps(notebook), encoding="utf-8")
    assert _notebook_issue(path) == issue


def test_saved_widget_state_is_rejected(tmp_path, notebook):
    notebook["metadata"]["widgets"] = {"application/vnd.jupyter.widget-state+json": {"state": {}}}
    path = tmp_path / "example.ipynb"
    path.write_text(json.dumps(notebook), encoding="utf-8")
    assert _notebook_issue(path) == "saved widget state"


@pytest.mark.parametrize(
    "source, issue",
    [
        ("{", "unreadable or invalid notebook JSON"),
        ('{"metadata":{"widgets":{}},"metadata":{}}', "unreadable or invalid notebook JSON"),
        ('{"nbformat":3,"worksheets":[]}', "expected a v4 notebook with cells and metadata"),
        ('{"nbformat":4,"metadata":{},"cells":[null]}', "cell 1 has an invalid structure"),
    ],
)
def test_invalid_notebooks_fail_safely(tmp_path, source, issue):
    path = tmp_path / "example.ipynb"
    path.write_text(source, encoding="utf-8")
    assert _notebook_issue(path) == issue


def test_checks_tracked_notebooks_and_omits_output_content(tmp_path, notebook, capsys):
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=tmp_path, check=True)
    tracked = tmp_path / "examples" / "example.ipynb"
    tracked.parent.mkdir()
    tracked.write_text(json.dumps(notebook), encoding="utf-8")
    subprocess.run(["git", "add", "--", str(tracked)], cwd=tmp_path, check=True)

    notebook["cells"][0]["outputs"] = [{"output_type": "stream", "text": "synthetic-private-row"}]
    (tmp_path / "local.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    assert check_notebooks(tmp_path) == 0
    assert "(1 tracked notebooks)" in capsys.readouterr().out

    tracked.write_text(json.dumps(notebook), encoding="utf-8")
    assert check_notebooks(tmp_path) == 1
    assert capsys.readouterr().err == "'examples/example.ipynb': cell 1 has saved output\n"
