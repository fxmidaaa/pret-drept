import json
from datetime import datetime, timezone

import pytest

from rent_agent.tasks import TaskRecord, TaskState
from rent_contracts import ContractError
from rent_contracts.validation import MAX_DOCUMENT_BYTES


def advance(record, *states):
    for state in states:
        record = record.transition(state)
    return record


def ready_record(document):
    document["verification_evidence"] = [
        {"check": "unit", "status": "passed", "required": True, "reference": "report.md"}
    ]
    return advance(
        TaskRecord.from_document(document),
        TaskState.CLASSIFIED,
        TaskState.PLANNED,
        TaskState.ACTIVE,
        TaskState.VERIFYING,
        TaskState.READY_FOR_REVIEW,
    )


def test_task_context_survives_a_fresh_read(task_document, tmp_path):
    record = ready_record(task_document)
    path = tmp_path / "task.json"
    record.save(path)
    reloaded = TaskRecord.read(path)
    assert reloaded.to_document() == record.to_document()
    assert reloaded.to_document()["state"] == "READY_FOR_REVIEW"
    assert list(tmp_path.glob(".task-*.tmp")) == []


@pytest.mark.parametrize("extra_bytes", [0, 1], ids=["at-limit", "one-byte-over"])
def test_task_record_storage_byte_limit(task_document, tmp_path, extra_bytes):
    path = tmp_path / "task.json"
    original = TaskRecord.from_document(task_document)
    original.save(path)
    previous_bytes = path.read_bytes()

    def storage_size():
        return len((json.dumps(task_document, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    target = MAX_DOCUMENT_BYTES + extra_bytes
    chunk = "é" * 1024
    task_document["current_progress"] = [""]
    base_size = storage_size()
    task_document["current_progress"] = [chunk, ""]
    count, tail = divmod(target - base_size, storage_size() - base_size)
    task_document["current_progress"] = [chunk] * count + ["x" * tail]
    assert storage_size() == target
    record = TaskRecord.from_document(task_document)

    if extra_bytes:
        with pytest.raises(ContractError, match="size limit"):
            record.save(path)
        assert path.read_bytes() == previous_bytes
        assert TaskRecord.read(path) == original
    else:
        record.save(path)
        assert path.stat().st_size == MAX_DOCUMENT_BYTES
        assert TaskRecord.read(path) == record
        with path.open("ab") as stream:
            stream.write(b"\n")
        with pytest.raises(ContractError, match="size limit"):
            TaskRecord.read(path)
    assert list(tmp_path.glob(".task-*.tmp")) == []


def test_failed_atomic_replace_preserves_previous_context(task_document, tmp_path, monkeypatch):
    path = tmp_path / "task.json"
    original = TaskRecord.from_document(task_document)
    original.save(path)

    def fail_replace(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr("rent_agent.tasks.os.replace", fail_replace)
    with pytest.raises(OSError):
        original.transition(TaskState.CLASSIFIED).save(path)
    assert TaskRecord.read(path).to_document() == original.to_document()
    assert list(tmp_path.glob(".task-*.tmp")) == []


@pytest.mark.parametrize("risk", ["L1", "L2"])
def test_nonroutine_task_cannot_skip_plan(task_document, risk):
    task_document["risk_level"] = risk
    record = TaskRecord.from_document(task_document).transition(TaskState.CLASSIFIED)
    with pytest.raises(ContractError, match="PLANNED"):
        record.transition(TaskState.ACTIVE)


def test_routine_task_can_start_without_formal_plan(task_document):
    task_document["risk_level"] = "L0"
    task_document["implementation_plan"] = []
    record = advance(
        TaskRecord.from_document(task_document), TaskState.CLASSIFIED, TaskState.ACTIVE
    )
    assert record.to_document()["state"] == "ACTIVE"


@pytest.mark.parametrize(
    "field",
    ["implementation_plan", "affected_modules", "acceptance_criteria", "verification_requirements"],
)
def test_required_planning_fields_cannot_be_empty(task_document, field):
    task_document[field] = []
    record = TaskRecord.from_document(task_document).transition(TaskState.CLASSIFIED)
    with pytest.raises(ContractError):
        record.transition(TaskState.PLANNED)


@pytest.mark.parametrize("status", ["failed", "skipped", "unavailable"])
def test_required_checks_cannot_be_reported_as_success_when_unverified(task_document, status):
    task_document["verification_evidence"] = [
        {"check": "unit", "status": status, "required": True, "reference": "report.md"}
    ]
    record = advance(
        TaskRecord.from_document(task_document),
        TaskState.CLASSIFIED,
        TaskState.PLANNED,
        TaskState.ACTIVE,
        TaskState.VERIFYING,
    )
    with pytest.raises(ContractError, match="evidence"):
        record.transition(TaskState.READY_FOR_REVIEW)


def test_missing_mandatory_check_cannot_pass_with_unrelated_evidence(task_document):
    record = ready_record(task_document).to_document()
    record["verification_requirements"].append("security")
    with pytest.raises(ContractError, match="missing"):
        TaskRecord.from_document(record)


@pytest.mark.parametrize("field", ["known_blockers", "pending_approvals"])
def test_completion_cannot_hide_pending_work(task_document, field):
    document = ready_record(task_document).to_document()
    document["final_outcome"] = "source tested"
    document[field] = ["external prerequisite"]
    with pytest.raises(ContractError):
        TaskRecord.from_document(document).transition(TaskState.COMPLETED)


def test_completed_task_is_terminal_and_not_model_acceptance(task_document):
    document = ready_record(task_document).to_document()
    document["final_outcome"] = "contract helper tested; no model accepted"
    completed = TaskRecord.from_document(document).transition(TaskState.COMPLETED)
    with pytest.raises(ContractError):
        completed.transition(TaskState.ACTIVE)


def test_backdated_or_naive_history_is_rejected(task_document):
    record = TaskRecord.from_document(task_document)
    with pytest.raises(ContractError, match="timezone"):
        record.transition(TaskState.CLASSIFIED, timestamp=datetime(2026, 11, 2))
    with pytest.raises(ContractError, match="chronological"):
        record.transition(TaskState.CLASSIFIED, timestamp=datetime(2000, 1, 1, tzinfo=timezone.utc))


def test_forged_or_unknown_history_state_is_rejected(task_document):
    task_document["history"].append({"state": "COMPLETED", "timestamp": "2026-11-02T10:01:00Z"})
    task_document["state"] = "COMPLETED"
    with pytest.raises(ContractError, match="transition"):
        TaskRecord.from_document(task_document)


def test_blocked_task_reenters_classification_before_resuming(task_document):
    record = advance(
        TaskRecord.from_document(task_document),
        TaskState.CLASSIFIED,
        TaskState.PLANNED,
        TaskState.ACTIVE,
        TaskState.BLOCKED,
    )
    with pytest.raises(ContractError):
        record.transition(TaskState.ACTIVE)
    resumed = advance(record, TaskState.CLASSIFIED, TaskState.PLANNED, TaskState.ACTIVE)
    assert resumed.to_document()["state"] == "ACTIVE"


def test_blocked_record_cannot_conceal_skipped_historical_planning(task_document):
    task_document["state"] = "BLOCKED"
    task_document["history"].extend(
        [
            {"state": "CLASSIFIED", "timestamp": "2026-11-02T10:01:00Z"},
            {"state": "ACTIVE", "timestamp": "2026-11-02T10:02:00Z"},
            {"state": "BLOCKED", "timestamp": "2026-11-02T10:03:00Z"},
        ]
    )
    with pytest.raises(ContractError, match="PLANNED"):
        TaskRecord.from_document(task_document)
