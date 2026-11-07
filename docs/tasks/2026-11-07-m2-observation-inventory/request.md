# Approved request

The user asked to move to the next M2 increment under intent, implementation
proposals, human approval, implementation, and human review. After reviewing
the alternatives, the user said “approved option A. start implementing”.

Option A adds a standalone observation inventory in Parquet with a bounded JSON
manifest, an incremental v1-compatible logical digest, a fixed typed schema,
and explicit local I/O limits. It verifies synthetic round trips and local DVC
restoration while preserving all existing release and split interfaces.
PyArrow 26.0.1 is the approved optional backend and development lock addition.

Stop at the second review with checks and a proposed commit message. Scope is
source, documentation, pinned public dependency setup, and disposable synthetic
verification. Publication requires a separate user instruction.
