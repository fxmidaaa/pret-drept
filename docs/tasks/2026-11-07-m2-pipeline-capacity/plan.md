# M2 increment 8 — pipeline capacity evidence

## Scope and starting state

L1 engineering under [§6.2](../../architecture/specification-v1.md#62-risk-classification).
The [request](request.md) leaves the choice of increment to this session. This increment adds
measurement tooling, tests and documentation. It changes no production source, schema, wire
contract, policy or dependency, reads no real data and activates nothing.

**Classification.** No split rule, partition, cohort, exclusion, boundary, schema or wire format
changes, and no protected data, security boundary, CI privilege or promotion path is involved.
The tool calls the existing production code unchanged. L1 is chosen over L0 because it adds a
tool, tests and a report across several areas. A change to any limit, format or rule that the
report recommends is a separate decision and, for the split transport, L2.

**Starting state, verified rather than read from the records.**

| Item | Observed |
| --- | --- |
| Branch and HEAD | `feat/m2-reference-splits` at `3716c1252b40bb095904221891357de987ce4f81`. It equals `origin/feat/m2-reference-splits` and is one commit ahead of `main` (`7f69b17`). The index is empty |
| Content of HEAD | Increments 6 and 7 in one commit. Their committed records still say "uncommitted on `main`" and "Linux CI unavailable", which is stale, and still list their review as pending. This task did not change them |
| Exact-revision CI | [Run 42411611205](https://github.com/fxmidaaa/pret-drept/actions/runs/42411611205) passed: 969 checkout passes and 12 private-model skips, and 768 passes for each of the source archive and the wheel. No pull request exists for the branch |
| Working tree | Five edits this task does not own. They must stay byte-identical (table below) |

| Edit not owned by this task | SHA-256 at the start of work |
| --- | --- |
| `AGENTS.md` | `0854ec994b0bc9a46f5ee68efcd726ab9a9a270a37bfbcd6803f07d45c449bdf` |
| `docs/development.md` | `3c90180bac5e596e4e6b61555cb3e231a06fbc5520ebaed2978af6ba7ea639d4` |
| `docs/reports/architecture-quality-improvements.md` (untracked) | `32035930ada0244fd0389d0beebcee74e0a472d5dbfb12403851a2af9bc64b75` |
| `docs/tasks/2026-11-05-audit-report-consistency/plan.md` | `1ba54d3d91900a393317ab043f0a90c8c46e11bbc0347ce23518461f3a4d16a2` |
| `docs/tasks/2026-11-05-audit-report-consistency/task.json` | `b38332bc330b29cb66eccc5176ee9d085b0ff570c8c23218ef996e73d7295da6` |

`AGENTS.md` and `docs/development.md` were edited at 22:47 local time while this session was
reading. Another session or tool made that edit, adding the verification cadence this plan follows.
The hashes above describe the files after it. `docs/development.md` was reworded again at 23:48,
and its hash at the end of work is in the final verification. This task edits none of the five
files.

**Why work continues despite the review gate.** The earlier gate protected an uncommitted,
unreviewed increment whose files a second increment would have edited. Increments 6 and 7 are now
committed and published, and this increment edits none of the files they added. A review finding
against them cannot conflict with this tool. Whether that review is complete is recorded only in
those records, which still list it pending, so this plan treats it as open and does not alter it.

## Increment selection

The M2 exit gate (a reproducible training run and a defensible development evaluation) is open.
It needs authorized real data, defensible chronology, reviewed property evidence and policies,
and isolated execution. None of these exists, so none can be worked on here.

The recorded next increment is a versioned typed split-membership artifact. It changes the split
wire contract and is L2 under §6.2. That level requires a formal plan, a threat assessment,
explicit approval and independent verification, and none has been given. It also lacks its
sizing input. Backlog item Q03 asks to size any change against measured workload, memory and
processing time, and to make the bottleneck visible across the whole pipeline. The only capacity
figures are a one-off probe that the design says is not retained in the repository.

A preliminary exploration with the production builders (not retained, so not evidence) found two
facts that bear on the L2 decision. At the 4,528 rows documented by M0 and 64-character
identifiers, the candidate document and the source bytes were near their caps (about 89% and 90%).
The complete split already exceeded its cap. If so, a split-only transport would add little
capacity. A verified restore also took tens of seconds. This increment retains the measurement
and confirms or refutes these facts with a reviewable tool, so the L2 proposal can be scoped on
evidence. It needs no approval, because it changes nothing the L2 gate protects. The
[report](../../reports/m2-pipeline-capacity.md) records what the retained tool found.

## Quality-backlog review

[Backlog](../../reports/architecture-quality-improvements.md#use-in-implementation) reviewed
against the affected modules (the candidate, inventory, release and split stages), their size
limits and their failure modes.

| Q-ID | Decision | Record |
| --- | --- | --- |
| Q03 | Address in this task | Whole-pipeline capacity with realistic identifier lengths, exclusion mixes and the M0-documented volume, including the candidate source and lineage limits, with time and memory. Evidence: the probe, its tests and the [report](../../reports/m2-pipeline-capacity.md). Already covered by increment 7 and cited, not repeated: parity with the existing path, rejection of damaged, missing, extra or swapped records, and restoration of an earlier release and split into a fresh cache |
| Q07 | Address in part | The probe is a documented synthetic entry point whose sizes and sealed identities are deterministic. Tests compare them across hash seeds, which turns the ad hoc increment 7 check into a retained one. Timings and memory carry their platform. The second-person clean-checkout path is a follow-up that needs a reviewer |
| Q12 | Address in part | Records build and verification time and peak memory per stage for the synthetic path, without a new service, store or dependency |
| Q08 | Already covered | The limits exercised are the existing pre-decode bounds from increments 5 to 7. This task changes none and runs only in a directory it creates and removes. It demonstrates no isolation |
| Q01 | Follow up separately | Collection cadence, scope and volume need approved acquisition and data-handling decisions (U-09). The report states volumes only as arithmetic on the documented 4,528 rows |
| Q10 | Not applicable | No monitoring, retention or recovery drill. Synthetic timings are not recovery-time evidence |
| Q02, Q04, Q05, Q06, Q09, Q11 | Not applicable | No identity matching, feature, model, renter-facing, release-fault, serving or harness behavior is touched |

## Design and requirements

One tool, `scripts/measure_pipeline_capacity.py`, outside the shipped packages, with two commands:

- `stages` runs the production candidate, inventory, payload, release, restoration, split and
  read-back path once for a stated population. It reports each stage's outcome, wall time and
  peak resident memory, the artifact sizes and the sealed release and split identities. It stops
  at the first production failure and reports the production's own fixed message. A
  derivation stage runs the membership rules alone, with the validation they perform. Each run is
  a fresh process, so peak memory is meaningful.
- `capacity` fits a size model for each artifact from small production runs of a few hundred
  observations. The model is affine in the observation and envelope counts, with measured offsets
  inside the repeating cycle of each mix, so it is exact at every count and not only at whole
  cycles. It predicts, for every size gate, the largest population that passes, then names the
  first limit, any limit within one row of it, and the headroom left if the first limit alone were
  lifted.
  `--confirm` searches within four records of the predicted boundary with the real production
  path and prints a progress line to standard error before each run. It reports the largest passing
  population and the failure one record beyond it. It confirms only when the boundary equals the
  prediction, or is within a row when the first or a tied limit is the candidate or release
  document, whose decimal counters leave their model a few bytes uncertain, and when the failure is
  that of the first or a tied limit.

Populations are deterministic and synthetic. Identifier length is a parameter, because it
dominates every size. Four mixes are named. `training` gives the smallest split rows and so the
best case for the split limit. `typical` repeats the six observation kinds of the shared
reference fixture. `excluded` gives the one-reason rows whose capacity the design already states in
closed form. `balanced` alternates training and unseen validation rows, the worst case for the
quadratic derivation. Expected memberships under the existing rules are written by hand in the
tests.

Boundaries and invariants:

- The tool imports public production APIs and constants only. It does not patch, wrap or copy
  production code, so a stage that fails reports the production's own message. The only thing it
  skips is the pure derivation above the production ceiling. A predicted limit comes from a size
  model, and only a confirmation is a production measurement of a boundary.
- It writes only inside a temporary directory it creates, resolves and removes. It accepts no
  output path, reads no input data, and uses no network, DVC, credential or protected label. It
  prints aggregate numbers only.
- Sizes and identities are deterministic. Timings and memory are not, and they are reported
  with the platform that produced them. Predicted limits are labelled as predictions in every
  output, and extrapolations beyond measured sizes are labelled in the report.
- Malformed arguments exit with status 2. A failing production gate is a finding, not a tool
  error, so a complete report exits 0. A `--confirm` run exits 1 when a boundary cannot be
  confirmed, and a tool error such as a failed fit run exits 1 with a message.

## Alternatives considered

- Implement the L2 typed split artifact now. It needs approval and a threat assessment, and the
  preliminary figures suggest re-scoping it first. Rejected for this increment.
- Compute capacity from closed-form byte formulas. This would measure the formulas, not the
  production code. The fitted model uses production artifacts and checks a held-out run.
- A slow pytest marker for capacity. It would lengthen the default suite or change its default
  selection. A script with fast guard tests keeps the suite quick.
- Instrument production code with counters or timers. No source change is needed. The
  probe stays outside the product.
- Optimize validation or the quadratic derivation now. Neither is a demonstrated blocker at the
  current ceiling. A linear-time derivation is a prerequisite for lifting the ceiling, so it
  belongs to the L2 design, informed by this evidence.

## Acceptance criteria and implementation plan

1. The population generator is deterministic. Every row passes the production validators and has
   the requested identifier length. Each mix derives the hand-written memberships under the
   production rules.
2. The stage runner exercises the production path in a directory it owns and removes. It reports
   stage outcome, time, peak memory, sizes and identities. It stops at the first production
   failure with the production message and creates no persistent state.
3. The fitted model predicts production sizes exactly for the source bytes and the split at every
   count, including counts that end part-way through a cycle of the mix, and within a few bytes
   for the candidate and release. The split capacity it derives for the `excluded` mix equals the
   existing closed-form figures (5,544, 5,111, 4,421 and 3,481 observations at 16, 32, 64 and
   128 characters).
4. `--confirm` shows, for each reported first limit, that the production path passes at the
   predicted capacity and fails at one record more, or reports the observed boundary. A bounded
   search keeps its cost predictable. The runs are recorded in the report.
5. Release and split identities and every size are identical across fresh interpreters with
   three different hash seeds, and so is a capacity report across two.
6. The report gives measured sizes at the M0-documented volume, capacity per gate and identifier
   length, the first limit and headroom, the time and memory budget, the derivation scaling, and
   the consequences for the next increment. It labels extrapolation and states synthetic,
   platform and single-machine limits.
7. The earlier ad hoc figures in the design are reproduced or corrected. No production source,
   schema, dependency, packaging or protected file changes. This task does not edit any of the five
   files above. Nothing is committed or pushed.
8. Checks run after the last edit under the
   [verification cadence](../../development.md#verification-for-each-increment) and each result is
   recorded as passed, failed, skipped or unavailable.

Plan: persist this record; write the generator and stage runner; add the model, gates and
confirmation; add the CLI; add the tests; run the probe grid; write the report and update the
design and index; run the checks; review the diff independently; record the evidence.

## Verification and recovery

Run, with `-p no:cacheprovider` and an owned `--basetemp` for every pytest run:

```bash
.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_pipeline_capacity.py
.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_repository_tasks.py tests/foundations/test_tasks.py tests/foundations/test_architecture.py
.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/integration tests/test_scrape.py tests/conftest.py
.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/integration tests/test_scrape.py tests/conftest.py
.venv/bin/rent-check-architecture --root .
.venv/bin/python -m pytest -p no:cacheprovider -q -ra -m 'not legacy_artifact'
```

The last command is the aggregate regression, including the actual local Git and DVC
integration with the pinned DVC. It stays inside the synthetic scope. The source and wheel suites
are skipped by plan under the cadence: no packaged file, public contract or dependency changes,
which `git diff --stat -- src pyproject.toml MANIFEST.in requirements-dev.lock` shows. Exact-revision
CI is unavailable for uncommitted work.

On recovery, reconcile before continuing:

```bash
git rev-parse HEAD                      # 3716c1252b40bb095904221891357de987ce4f81
git branch --show-current               # feat/m2-reference-splits
git diff --cached --name-only           # empty
git status --short                      # the five edits above, plus this task's files
git diff --check
shasum -a 256 AGENTS.md docs/development.md docs/reports/architecture-quality-improvements.md docs/tasks/2026-11-05-audit-report-consistency/plan.md docs/tasks/2026-11-05-audit-report-consistency/task.json
```

Compare the hashes with the table above. `docs/development.md` was reworded by someone else at
23:48, so compare it with the hash in the final verification. A later change to a file this task
does not own comes from someone else and is theirs to keep. The tool leaves no state, so an
interrupted run needs only a rerun.

## Maintainer review

Reading the diff and running it, then an independent review by a fresh reviewer that saw only the
code and the tool's own claims, found the issues below. Each was verified before it was changed.

My own findings while building:

- The first production confirmation of the training-heavy 128-character population disagreed with
  the prediction. The candidate and split limits tie at 3,824 and production failed in the split
  stage, while my check accepted only the first-named gate. Limits within one row are now reported
  as tied, and a confirmation accepts the failure of any of them.
- The synthetic source record identifier length was a hidden assumption, and it moves the candidate
  limit by one row per character. It is now `--record-id-length`, and the report shows the
  128-character case, where the candidate becomes the first limit.
- Production put the candidate boundary two rows above the prediction at 64 characters and one at
  128. Decimal counters gain a digit between tiny fit runs and the target size, which tilts the
  fitted slope. A fit unit of 198 keeps the counters in the target's digit regime and predicted
  both boundaries exactly, so it is the default.
- A new test caught an off-by-one in the boundary search: a boundary exactly at the edge of the
  window was never found.
- Three claims in my draft report were wrong and are corrected: lifting the split alone was said to
  help training-heavy populations, the source figures were said not to depend on the mix, and one
  derivation stage was presented as the membership rules alone.

Independent review, first round, seven findings:

1. **High.** The model was exact only at counts that are whole cycles of the mix. Reproduced against
   production: for 13-character identifiers it predicted 5,514 and production's boundary is 5,515.
   The model now measures the offsets inside a cycle with extra fit runs, and the held-out run ends
   part-way through a cycle. Tests compare it with production at counts that are not whole cycles.
2. **Medium.** The per-envelope document limit was not modelled, so a large `--per-source` gave a
   wrong report. It is now rejected with a clear error.
3. **Medium.** A confirmation could cost many silent runs. The search is bounded to four records
   either side, a progress line goes to standard error before each run, and the help states the cost.
4. **Low.** A size gate tied with the inventory record limit crashed `--confirm`. A capacity whose
   search would pass the record limit is now reported as not confirmable, with a note. The second
   round showed that the first fix was off by one at the edge of the search window. It is
   corrected and tested at the edge.
5. **Low.** `--fit-unit` accepted values whose fit runs cannot pass. It is bounded to 300. The second
   round also showed that units below the default 198 leave the candidate prediction several rows
   off, because decimal counters tilt the slope. They stay allowed for quick checks, and the help
   and every Markdown table now say so.
6. **Low.** Wording overstated the code. The docstring, the plan and every capacity output now say
   that limits are predictions and only a confirmation is a production measurement.
7. **Low.** Some tests mirrored the implementation or could not fail. The report test now uses
   hand-computed fits, an assertion that could not fail is gone, and tests cover the Markdown
   branches, an unfound boundary, a period-six confirmation, the record limit, progress output and
   cross-process determinism of `capacity`.

Independent review, second round, of the finished tool, report and plan. It confirmed that the
fixes for findings 1, 2, 3, 5, 6 and 7 hold against production, including the 13-character case.
It found nine more issues, all verified and fixed:

1. **Medium.** The report called a verified pass linear and gave 19 minutes at 100,000 observations,
   which ignored the quadratic derivation term that the same report quantifies, and the arithmetic
   was a minute high. The estimate is now about 18 minutes of linear cost plus 5 to 16 minutes of
   pairwise comparison.
2. **Medium.** The design bullet and the index entry said the three limits bind within about 15% of
   each other. Only the next limit is within 15%. Both now say that lifting only the split limit
   adds at most 17% of capacity at the default shapes.
3. **Low to medium.** The timestamp sensitivity was given as 5% to 7%. It is up to 6%, and none in
   the `excluded` mix.
4. **Low to medium.** Small fit units are flagged in the output, as item 5 above records.
5. **Low.** The record-limit guard was off by one at the window edge. Fixed with tests at the edge.
6. **Low.** The report claimed "nothing else running" for the timing runs. It now states what was
   true, including the load average at the start.
7. **Low.** Smaller report inaccuracies are corrected: the baseline memory includes the generated
   population, the profiler slowed the run 3.4 times and came from an earlier tool revision with the
   same production stages, the second doubling was 2.3 to 2.4 times, and "gains nothing in any mix"
   is now labelled an inference.
8. **Low.** A test mirrored a constant and some boundaries were untested. The constant is replaced by
   the invariant that the window exceeds the tolerance, and new tests cover the record-limit edge,
   the envelope guard's exact boundary against production and the fit-unit note.
9. **Low.** This section said the record-limit tie was reported as not confirmable, which was true
   only at the exact limit. It now says what the code does.

A mutation pass on a scratch copy broke the tool on purpose: population kinds and identifier widths,
the cleanup and stop-at-failure behavior, recorded sizes and identities, the model's solve, phases,
tolerance and ties, the boundary search and its window, the confirmation rules, the command-line
bounds and the output notes. The first test set let two mutants survive: an equality boundary in the
model search and acceptance of a wrong failing stage. Tests were added for both. All 46 mutants
in the final set are caught.

Not changed, with the follow-up:

- `validate_document` builds a validator and canonicalizes the document on every call, which the
  profile shows is 95% of a verified pass. Changing production validation is outside this task. The
  [report](../../reports/m2-pipeline-capacity.md#what-this-means-for-the-next-increment) makes
  validating once per verified population a requirement of the next transport plan.
- A gate behind an earlier gate cannot be observed in production, so its limit stays a prediction.
  Only each configuration's first limit is confirmed.
- The tool is about 1,000 lines. A maintainer who finds that too much can drop the `balanced` mix
  and the Markdown renderer without changing any finding.

## Final verification

The checks ran on CPython 3.13.16, Darwin ARM64, PyArrow 26.0.1, DVC 3.67.1 and Git 2.54.0, with
only synthetic populations, disposable directories and local stores. The project index and branch
tip stayed unchanged.

| Status | Check | Evidence |
| --- | --- | --- |
| Passed | Focused | **145 passed** in `tests/foundations/test_pipeline_capacity.py` after the last code and test edit |
| Passed | Task records, lifecycle and architecture tests | **57 passed**, which validate this record |
| Passed | Static and dependency boundaries | Ruff check and format check over **59** files, and `rent-check-architecture` |
| Passed | Checkout regression | **1,108 passed**, **12 private-model checks deselected**, 1 existing deprecation warning, in 302 s. It includes the actual local Git and DVC integration and ran once. The second review round then changed only the probe, its tests and documentation, which nothing else in the suite imports, so the probe's tests were rerun after those edits |
| Passed | No production change | `git diff --stat` over `src`, packaging, dependency, workflow and legacy files is empty, and no untracked file lies outside `docs`, `scripts` and `tests` |
| Passed | Preservation | HEAD `3716c12`, the branch and the empty index are unchanged. `AGENTS.md`, the quality backlog and the two report-consistency files are byte-identical to their starting hashes. `docs/development.md` was reworded by someone else at 23:48, and its SHA-256 at the end is `bd299f1a0ed925d092de89d852e52ed8dd52a9d4dc439241d08bede698c87b82` |
| Passed, not required | Production confirmation | Fourteen first-limit boundaries confirmed against the real pipeline: the training, typical and excluded mixes at 16, 32, 64 and 128 characters, and the typical mix at 16 and 64 characters with 128-character record identifiers. Each passed at the predicted capacity and failed one record beyond it with the production message |
| Passed, not required | Mutation sanity | All **49** deliberate regressions of the tool were caught, across populations, cleanup and stopping, recorded sizes, the model's solve, phases, tolerance and ties, the boundary search and window, the record-limit and envelope guards, the confirmation rules, the command-line bounds and the output notes |
| Passed, not required | Determinism across hash seeds | Retained tests compare sizes and sealed identities across three seeds and a capacity report across two |
| Failed, recovered | Interim: first confirmation of the 128-character training population | The candidate and split limits tie and production failed in the split stage, which the first check did not accept. Limits within a row are now tied and either failure is accepted |
| Failed, recovered | Interim: size model at counts that are not whole cycles | Independent review reproduced a one-record error (predicted 5,514, production 5,515). Fixed with a phase-aware model and tests against production |
| Failed, recovered | Interim: boundary search window | A new test found that a boundary at the edge of the window was never found. Fixed |
| Failed, recovered | Interim: first mutation set | Two mutants survived: an equality boundary in the model search and acceptance of a wrong failing stage. A later pass found a third, the envelope guard's equality case. Tests were added for each |
| Failed, recovered | Interim: scratch mutation harness | Its first run stopped because pytest needs the parent of `--basetemp` to exist. It is scratch tooling and not a product check |
| Skipped | Source and wheel suites | Skipped by plan under the verification cadence: no packaged file, public contract or dependency changed |
| Unavailable | Exact-revision CI, protected verification and the M2 exit gate | The work is uncommitted, so no CI run exists for it. Real-data evidence, authorized chronology, reviewed property evidence and policy, isolated reproducible execution and independent verification are separate gates |

### Backlog results

- **Q03, addressed.** The probe measures the candidate, inventory, release and split stages together
  with identifier lengths from 16 to 128, three exclusion mixes, two record identifier lengths and
  the M0 volume. Fourteen first limits are confirmed against production, and the time and memory
  budget is recorded. Increment 7 already covered parity, damaged records and restoration into a
  fresh cache. Result: lifting only the split limit adds at most 17% of capacity, so the next
  transport must also cover candidate lineage and the source bound.
- **Q07, addressed in part.** The probe is a documented synthetic entry point. Sizes and sealed
  identities are identical across hash seeds, and the timing and memory carry their platform. The
  second-person clean-checkout path still needs a reviewer.
- **Q12, addressed in part.** A verified pass at the M0 volume takes about 50 s and 144 MiB, and 95%
  of it is repeated schema validation. No service, store or dependency was added.
- **Q08, already covered.** The size bounds are the existing pre-decode limits. No isolation is
  demonstrated.
- **Q01, follow up separately.** Collection cadence and volume need the acquisition decisions in U-09.
  The report states volumes only as arithmetic on the documented 4,528 rows.

## Review handoff

The bounded increment is `READY_FOR_REVIEW` on `feat/m2-reference-splits` at `3716c12`, uncommitted
with an empty index. It sits on the published increments 6 and 7, whose own review this task did
not change. See the [increment report](../../reports/m2-pipeline-capacity.md). It adds the probe,
its tests, the report and this record, and edits three documents: the split design, the report
index and the increment 7 report's next-increment paragraph.

The single next increment is the L2 plan and threat assessment for one coordinated transport that
covers split membership, candidate lineage and the source bound, with once-per-population
validation, bounded-memory verification and a linear-time derivation. It needs the owner's
decision on the population a release must carry, the identifier shapes and the acceptable
verification time, and approval to start the L2 process. `docs/development.md` would also gain a
pointer to the probe, which this task left out because someone else was editing that file.
