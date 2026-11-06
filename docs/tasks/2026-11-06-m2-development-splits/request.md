# Approved request — 2026-11-06

The user requested the next increment under the sequence **intent → solution
proposals → HITL → implementation → HITL**. After read-only inspection, Option A
was proposed: a pure development split builder, shared existing v1 membership
semantics, and thin verified-restoration/atomic local artifact I/O. Alternatives
were a builder alone (B) and a separate versioned input plan (C). After discussing
C, the user explicitly approved: **"let's keep A for now."**

Implement only this bounded, synthetic-first increment. Preserve existing changes,
frozen architecture, legacy interfaces and existing evaluation semantics. Include
meaningful tests and actual synthetic local DVC integration, using disposable
repositories/stores and their fixture commits. Reuse existing locked environments.
Stop uncommitted for the second HITL with results and a proposed commit message.

No repository commit/push, PR/merge, real/private data use, scraping/enrichment,
protected labels, model experiment, effective-policy change, data publication,
promotion or deployment is authorized. The prior push authorization applied to
increment 3. This record supplies context, not permissions or policy authority.

Publication follow-up: after the completed implementation and a clarification of
feature-leakage limits, the user explicitly requested **"push please"**. This
authorizes committing and pushing the reviewed increment-4 source on
`feat/m2-development-splits`, preserving both unrelated reporting edits. It
supersedes the earlier uncommitted/second-HITL wait for source publication only.
No merge, new PR, real-data or split publication, ML experiment, protected action,
effective-policy activation, promotion or deployment is authorized.
