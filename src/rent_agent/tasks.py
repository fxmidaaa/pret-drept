"""Deterministic task lifecycle and atomic repository-native context (§6)."""

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from rent_contracts import ContractError, load_document, validate_document
from rent_contracts.validation import canonical_json


class TaskState(StrEnum):
    PROPOSED = "PROPOSED"
    CLASSIFIED = "CLASSIFIED"
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    VERIFYING = "VERIFYING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_TRANSITIONS = {
    TaskState.PROPOSED: {TaskState.CLASSIFIED, TaskState.CANCELLED},
    TaskState.CLASSIFIED: {
        TaskState.PLANNED,
        TaskState.ACTIVE,
        TaskState.BLOCKED,
        TaskState.CANCELLED,
    },
    TaskState.PLANNED: {TaskState.ACTIVE, TaskState.BLOCKED, TaskState.CANCELLED},
    TaskState.ACTIVE: {
        TaskState.VERIFYING,
        TaskState.BLOCKED,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.VERIFYING: {
        TaskState.ACTIVE,
        TaskState.READY_FOR_REVIEW,
        TaskState.BLOCKED,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.READY_FOR_REVIEW: {
        TaskState.ACTIVE,
        TaskState.COMPLETED,
        TaskState.BLOCKED,
        TaskState.CANCELLED,
    },
    TaskState.BLOCKED: {TaskState.CLASSIFIED, TaskState.CANCELLED},
    TaskState.FAILED: {TaskState.CLASSIFIED, TaskState.CANCELLED},
    TaskState.COMPLETED: set(),
    TaskState.CANCELLED: set(),
}
_PLANNED_STATES = {
    TaskState.PLANNED,
    TaskState.ACTIVE,
    TaskState.VERIFYING,
    TaskState.READY_FOR_REVIEW,
    TaskState.COMPLETED,
}


def _validate_task(document: dict) -> None:
    validate_document("task-record", document)
    state = TaskState(document["state"])
    history = document["history"]
    if history[0]["state"] != TaskState.PROPOSED or history[-1]["state"] != state:
        raise ContractError("task history does not match current state")
    timestamps = [
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")) for event in history
    ]
    if any(a > b for a, b in zip(timestamps, timestamps[1:])):
        raise ContractError("task history is not chronological")
    for previous, current in zip(history, history[1:]):
        if TaskState(current["state"]) not in _TRANSITIONS[TaskState(previous["state"])]:
            raise ContractError("invalid task history transition")
        if (
            document["risk_level"] != "L0"
            and previous["state"] == TaskState.CLASSIFIED
            and current["state"] == TaskState.ACTIVE
        ):
            raise ContractError("engineering/protected task must pass through PLANNED")
    if document["risk_level"] != "L0" and state in _PLANNED_STATES:
        if not all(
            document[key]
            for key in (
                "implementation_plan",
                "affected_modules",
                "acceptance_criteria",
                "verification_requirements",
                "scope_boundaries",
                "protected_invariants",
            )
        ):
            raise ContractError("engineering/protected task lacks required planning context")
        if state != TaskState.PLANNED and not any(
            event["state"] == TaskState.PLANNED for event in history
        ):
            raise ContractError("engineering/protected task must pass through PLANNED")
    if state in (TaskState.READY_FOR_REVIEW, TaskState.COMPLETED):
        evidence = document["verification_evidence"]
        required = [item for item in evidence if item["required"]]
        if not required or any(item["status"] != "passed" for item in required):
            raise ContractError("required verification evidence is incomplete")
        checks = {item["check"] for item in required}
        if not set(document["verification_requirements"]).issubset(checks):
            raise ContractError("required verification checks are missing")
    if state == TaskState.COMPLETED:
        if document["pending_approvals"] or document["known_blockers"]:
            raise ContractError("task has pending approvals or blockers")
        if document["final_outcome"] is None:
            raise ContractError("completed task lacks final outcome")


@dataclass(frozen=True)
class TaskRecord:
    """Validated context, not trusted evidence or authorization. Never feed this to admission
    as proof of permission. On recovery reconcile it with Git and independent execution records.
    """

    canonical_payload: str

    @classmethod
    def from_document(cls, document: dict) -> "TaskRecord":
        _validate_task(document)
        return cls(canonical_json(document))

    @classmethod
    def read(cls, path: Path) -> "TaskRecord":
        with path.open("rb") as stream:
            raw = stream.read(1_048_577)
        return cls.from_document(load_document(raw))

    def to_document(self) -> dict:
        return json.loads(self.canonical_payload)

    def transition(self, state: TaskState, *, timestamp: datetime | None = None) -> "TaskRecord":
        document = self.to_document()
        current = TaskState(document["state"])
        if state not in _TRANSITIONS[current]:
            raise ContractError("invalid task state transition")
        instant = timestamp or datetime.now(timezone.utc)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ContractError("task timestamps must have a timezone")
        document["state"] = str(state)
        document["history"].append({"state": str(state), "timestamp": instant.isoformat()})
        return self.from_document(document)

    def save(self, path: Path) -> None:
        """Replace one context file atomically; a failed write leaves its prior version intact."""
        document = self.to_document()
        _validate_task(document)
        path = Path(path)
        if path.is_symlink():
            raise ContractError("task record destination must not be a symlink")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".task-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(document, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
