from pathlib import Path

from rent_agent.tasks import TaskRecord


def test_persisted_project_task_context_is_valid():
    root = Path(__file__).resolve().parents[2]
    records = list((root / "docs/tasks").glob("*/task.json"))
    assert records, "project task context must exist"
    for path in records:
        TaskRecord.read(path)
