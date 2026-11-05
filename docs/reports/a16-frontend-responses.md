# A16 — Frontend response handling and safe rendering

Date: 2026-11-05. Status: reviewed and verified locally on `fix/repository-audit` at
`36e67b7` plus the uncommitted audit diff. Original implementation started at `d9ac405`;
no A16 commit or push has been made. Risk: L1.

## Approved decision and change

The user approved option 2: a small response adapter with runtime validation and
separate rendering functions. The existing page and API routes are retained.

The page checks status and the consumed response fields before rendering a prediction.
It distinguishes field-validation errors, other HTTP failures, network failures and
unusable responses. Recognized field messages are rendered as text and associated
with controls. Raw input/context objects and HTTP error bodies are not dumped into
the page. Unrecognized validation details receive a generic correction message.

Driver labels, dropdown values and error messages use DOM text APIs. The previous
response-derived HTML interpolation is removed. Predictions with or without an
asking-price verdict retain their presentation. Unused response fields remain allowed.

All dropdown lists are validated before prediction is enabled. Failed loading gives
a refresh instruction. New submissions clear stale results/errors, block duplicate
requests and restore the button after completion. Backend validation and ML behavior
are unchanged.

Checkout CI now runs the offline frontend tests with Node.js 24.21.0 and a
commit-pinned setup action, with package-manager caching disabled. No npm dependencies,
frontend framework or inference runtime dependencies were added.

## Verification

| Check | Result | Limit |
| --- | --- | --- |
| Frontend regressions | 38 passed, 0 skipped | Actual inline script, synthetic responses and a narrow DOM double; no model/network access |
| Real-browser smoke | Passed | Synthetic loopback responses; successful estimates with/without verdicts, 422 feedback/recovery, literal HTML-like driver labels, malformed replies, 503 errors and options-loading failure |
| Checkout Python suite | 334 passed, 0 skipped | Existing local model available; one existing Starlette/httpx deprecation warning |
| Foundations source archive and wheel | 142 passed each | Packaging checks do not certify production inference |
| Ruff, workflow semantics, architecture, notebooks | Passed | Architecture checks do not certify runtime isolation |
| Final documentation/task/preservation checks | Passed | 8 A16 files, 23 local links/anchors, task records, whitespace and both byte-identical prior evidence files |
| Remote CI | Pending publication approval | No new commit or push is claimed |

Browser checks observed a field-specific floor error and `aria-invalid`/`aria-describedby`
associations, followed by successful correction. The driver string `<b>Synthetic driver</b>`
appeared literally, with zero injected `b`/`img` elements. Empty asking rent produced an
estimate with no verdict. A malformed 200 response produced an unexpected-response message;
a 503 produced a service message. Failed options left submission disabled with recovery
instructions. The final browser recheck confirmed the invalid field's red border and its
restoration after correction. This verifies the tested rendering paths, not a general
security certification.

## Evidence and remaining work

Detailed commands, observations, prior-file digests and recovery steps are in the
[task plan](../tasks/2026-11-05-frontend-responses/plan.md) and
[task record](../tasks/2026-11-05-frontend-responses/task.json).

Review the implementation and proposed commit message. Commit/push publication and its
exact-revision CI run remain separate from these local results. A17/A18, M2 benchmarks,
protected acceptance and deployment are outside this increment.

## Current completion review

The existing page, 38 frontend tests and CI additions were reviewed and retained.
Fresh synthetic Chrome checks passed: floor-specific 422 text, control associations
and red invalid border, successful correction/cleared associations, literal
`<b>Synthetic driver</b>` with zero injected `b`/`img` elements, both driver directions,
estimates with/without verdict, malformed success and 503 messages with enabled retry,
and options failure with disabled submission followed by a valid reload.

The [completion plan](../tasks/2026-11-05-audit-completion/plan.md) records the final
combined checks and screenshots. The table above retains the original A16 verification
counts; final aggregate counts include A18 regressions. The unrelated reporting files
remain byte-identical. Use the [current recovery pointer](README.md#current-checkpoint-and-recovery).
