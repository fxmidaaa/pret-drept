# M2 increment 8 — pipeline capacity evidence

2026-11-07, L1 engineering on `feat/m2-reference-splits` at `3716c12`, uncommitted. The
[task plan](../tasks/2026-11-07-m2-pipeline-capacity/plan.md) and
[record](../tasks/2026-11-07-m2-pipeline-capacity/task.json) hold the scope, verification and
recovery. This increment changes no production source, schema, dependency or contract. It adds
a synthetic measurement tool, `scripts/measure_pipeline_capacity.py`, its tests and this
report. It answers backlog item
[Q03](architecture-quality-improvements.md#q03--prove-release-and-split-capacity-using-realistic-inputs):
where the candidate, inventory, release and split stages fail together, and what they cost.

## What the tool does

It runs the production code for those stages, unchanged, on deterministic synthetic
populations in a directory it creates and removes, so a stage that fails reports the production's
own message. The limits it predicts come from a size model. Only a confirmation is a production
measurement of a boundary.

- `stages` runs the pipeline once and reports each stage's outcome, wall time and peak memory,
  the artifact sizes and the sealed identities. Use a fresh process per configuration.
- `capacity` fits a size model for each artifact from small production runs, derives the
  largest population each size gate admits and names the first limit. The model is exact for
  the source bytes and the split, and within a few bytes for the candidate and release.
  `--confirm` runs the production path within four records of the predicted boundary of the
  first limit, prints its progress to standard error and reports where the pipeline really fails.
  Fit runs below the default 198 observations are faster and can leave the candidate and release
  predictions several rows off, so the output says so.

Identifier length dominates every size, so it is a parameter. Sixteen characters is the
legacy `listing_key`. The others are a 128-bit and a 256-bit hexadecimal digest and the schema
maximum. Four mixes are named: `training` (the smallest split rows, the best case for the split
limit), `typical` (the six observation kinds of the reference fixture, one third of them
excluded), `excluded` (the one-reason rows whose capacity the design states in closed form) and
`balanced` (alternating training and unseen validation rows, the worst case for derivation).

## Capacity

For each identifier length (L) and mix, the table gives the largest population that passes each
limit that can bind, the first limit, and how far the pipeline could grow if only that limit were
lifted. A slash joins limits within one row of each other. Limits are predicted by the size model.
The last column shows that the real pipeline was run around the predicted boundary of the first
limit. It passed at the capacity and failed one record beyond it, in the stage and with the message
of that limit. The source record identifiers here are 14 characters.

| Mix | ID chars | Record ID chars | Source bytes | Candidate | Split | First limit | Headroom if lifted | Production boundary |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| training | 16 | 14 | 5,863 | 6,479 | 6,468 | source bytes (5,863) | +10.3% (split document) | confirmed at 5,863 |
| training | 32 | 14 | 5,494 | 5,895 | 5,886 | source bytes (5,494) | +7.1% (split document) | confirmed at 5,494 |
| training | 64 | 14 | 4,880 | 4,994 | 4,989 | source bytes (4,880) | +2.2% (split document) | confirmed at 4,880 |
| training | 128 | 14 | 3,989 | 3,825 | 3,824 | split document / candidate document (3,824) | +0.0% (candidate document) | confirmed at 3,824 |
| typical | 16 | 14 | 6,059 | 6,479 | 5,429 | split document (5,429) | +11.6% (source bytes) | confirmed at 5,429 |
| typical | 32 | 14 | 5,666 | 5,895 | 5,013 | split document (5,013) | +13.0% (source bytes) | confirmed at 5,013 |
| typical | 64 | 14 | 5,015 | 4,994 | 4,347 | split document (4,347) | +14.9% (candidate document) | confirmed at 4,347 |
| typical | 128 | 14 | 4,079 | 3,825 | 3,435 | split document (3,435) | +11.4% (candidate document) | confirmed at 3,435 |
| excluded | 16 | 14 | 7,302 | 6,480 | 5,544 | split document (5,544) | +16.9% (candidate document) | confirmed at 5,544 |
| excluded | 32 | 14 | 6,739 | 5,895 | 5,111 | split document (5,111) | +15.3% (candidate document) | confirmed at 5,111 |
| excluded | 64 | 14 | 5,838 | 4,994 | 4,421 | split document (4,421) | +13.0% (candidate document) | confirmed at 4,421 |
| excluded | 128 | 14 | 4,607 | 3,825 | 3,481 | split document (3,481) | +9.9% (candidate document) | confirmed at 3,481 |

Source record identifiers are a free parameter that the architecture does not fix, and the
schema allows 128 characters. Every lineage entry in the candidate and every record in a source
envelope carries one, so a long identifier makes the candidate the first limit by a wide margin.
The same confirmation with 128-character record identifiers:

| Mix | ID chars | Record ID chars | Source bytes | Candidate | Split | First limit | Headroom if lifted | Production boundary |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| typical | 16 | 128 | 5,202 | 3,798 | 5,429 | candidate document (3,798) | +37.0% (source bytes) | confirmed at 3,798 |
| typical | 64 | 128 | 4,413 | 3,234 | 4,347 | candidate document (3,234) | +34.4% (split document) | confirmed at 3,234 |

What each limit costs per observation, from the fitted model. It is exact for the source bytes and
the split, and within 5 bytes (candidate) and 9 bytes (release) on the held-out run:

| Artifact | Limit | Bytes per observation | Also grows with |
| --- | ---: | --- | --- |
| Source envelopes | 4 MiB in total | 3 × L + R + 653 (training), 3 × L + R + 630 (typical), 3 × L + R + 512 (excluded) | 212 bytes per envelope |
| Candidate document | 1 MiB | L + R + 131, one lineage entry | 300 bytes per envelope, about 2 KB fixed |
| Split document | 1 MiB | L + 146 (training), L + 177 (typical), L + 173 (excluded) | 733 bytes fixed |
| Release document | 1 MiB | none | 492 bytes per envelope, about 2.5 KB fixed |

L is the identifier length and R the source record identifier length. The release document does
not grow with the observation count, and the inventory record limit of 100,000 is not reached
before the others. The `excluded` mix gives split capacities of 5,544, 5,111, 4,421 and 3,481
observations at 16, 32, 64 and 128 characters. They equal the closed-form figures in the design to
the observation, and production confirmed all four.

Reading the tables:

- **The limits sit close together.** At 14-character record identifiers the candidate document
  admits 6,479, 5,895, 4,994 and 3,825 observations at 16, 32, 64 and 128 characters, give or
  take one row whatever the mix. In the `typical` mix the split is the first limit at every
  length, and lifting it alone raises the pipeline's capacity by only 11% to 15%. For
  training-heavy populations the source bytes bind first up to 64 characters and the candidate
  and split tie at 128, so lifting the split alone gains nothing.
- **A long source record identifier moves the first limit to the candidate.** With 128-character
  record identifiers the candidate document admits 3,798 and 3,234 observations at 16 and 64
  characters, below the split limits of 5,429 and 4,347. Lifting the split alone then gains
  nothing. Only the `typical` mix was run with these identifiers, but the other mixes' split limits
  at these lengths (6,468 and 5,544 at 16 characters, 4,989 and 4,421 at 64) are higher still, so
  the candidate is first there too. That is an inference.
- **The M0 volume sits on the edge.** M0 documents 4,528 raw rows. That volume passes every limit
  for 16- and 32-character identifiers, passes at 64 characters only for a training-heavy
  population and by less than 8%, and fails at 128 characters. With 128-character record
  identifiers it fails even at 16 characters. A second complete collection of that listing set,
  about 9,056 observations, exceeds the candidate document alone at every length and shape tried.

## Time and memory

These runs used one macOS ARM64 machine with 10 CPUs, each in a fresh process, with no other probe,
test or agent run active. The one-minute load average was 2.7 at the start, left over from a job
that had just ended. Three repeats of the first configuration agree within 1.3% per stage and 4% for the
derivation, so the other configurations are single runs. Here is that first configuration:

4,528 observations, 16-character identifiers, 14-character source record identifiers, mix `typical`, 600 per source document (8 documents).

| Stage | Outcome | Seconds | Peak RSS (MiB) |
| --- | --- | ---: | ---: |
| derive | ok | 2.33 | 44.4 |
| inventory | ok | 2.44 | 123.7 |
| candidate | ok | 4.45 | 133.0 |
| payload | ok | 4.72 | 135.3 |
| release | ok | 5.15 | 135.4 |
| restoration | ok | 4.95 | 142.5 |
| split | ok | 15.19 | 142.7 |
| readback | ok | 10.72 | 144.8 |

Bytes: source 3,134,410 · largest source document 415,312 · Parquet 1,764,738 · candidate 733,399 · release 6,426 · split 874,615.
Generating the population took 0.03 s. Resident memory was 42.0 MiB before the first stage.

- **What a pass costs.** The seven production stages after the tool's own derivation stage take
  about 48 s at the M0 volume, and the whole run about 50 s. It peaks at 144 MiB, of which 42 MiB is
  the interpreter, its imports and the generated population. That is about 11 ms and 23 KiB per
  observation. Extrapolating that linear cost, which is an estimate and not a measurement, one
  pass over the 100,000-record inventory limit would take about 18 minutes and 2.2 GiB, before the
  pairwise comparison below adds more.
- **Where it stops.** At 4,528 observations and 64-character identifiers the `typical` mix fails in
  the split stage after 9.6 s with the production message. At 128 characters the source bound fails
  right after the inventory is written, before anything is parsed. The training-heavy 64-character
  population passes with the source bytes at 93% of their bound (3,891,248 of 4,194,304), the
  candidate at 91% (950,736 of 1,048,576) and the split at 91% (951,613 of 1,048,576). At the
  predicted source limit of 5,863 observations the whole pipeline passes with the source bytes 139
  bytes under the bound (62 s, 154 MiB).
- **Where the time goes.** A one-off profile of the same run, not retained, put 95% of the time in
  JSON-Schema validation: 163,121 `validate_document` calls, or 36 for every observation. The
  candidate is built once and rebuilt five more times by verification, which is 54% of the run.
  `validate_document` builds a new validator and canonicalizes the document again on every call,
  and the observation schema resolves many `$ref` pointers. One derivation of the memberships,
  including the validation it performs, is 5% of a pass.
  Reproduce the shares with `python -m cProfile -o profile.out scripts/measure_pipeline_capacity.py
  stages --records 4528 --id-length 16 --mix typical`. The profiler slowed the run 3.4 times (172 s
  against 50 s). The profile came from an earlier revision of the tool with the same production
  stages, so its shares apply.

**Derivation scaling.** This is the `balanced` mix, the worst case for the pairwise comparison, with
the derivation stage run alone:

| Observations | Seconds | Peak RSS (MiB) |
| ---: | ---: | ---: |
| 1,782 | 0.98 | 39.2 |
| 3,564 | 2.17 | 43.0 |
| 7,128 | 5.06 and 5.13 | 50.3 and 50.0 |

Time grows roughly 2.2 and then 2.3 to 2.4 times per doubling, not four times, because the validation a
derivation performs is linear and the comparison of training with validation rows is quadratic. A
fit through the first and last points gives about 0.49 ms per observation plus 31 ns per squared
observation, or about 125 ns per training-validation pair, and predicts the middle point to within
1%. The pairwise term overtakes the linear one near 15,700 observations. Extrapolated, a
derivation at 100,000 balanced observations takes about six minutes, mostly pairwise. A verified
pass derives three times, twice when it creates the split and once when it reads it back, so at
100,000 observations the pairwise term adds about 5 minutes to a pass in the `typical` mix, where
training rows are a sixth of the population, and about 16 in the `balanced` mix. A pass would then
take roughly 23 to 33 minutes.

## What this means for the next increment

The recorded next increment is a versioned typed split-membership artifact, which is an L2 change.
The evidence says it is necessary but not enough, and it adds two requirements that the recorded
plan does not state.

1. **Do not plan the split transport alone.** At the default shapes, lifting only the split limit
   raises the pipeline's capacity by 11% to 15% in the `typical` mix and by nothing for
   training-heavy populations. With long source record identifiers the candidate lineage is the
   first limit and a split transport gains nothing. The M0 volume sits on these limits, and a
   second collection of the same listings exceeds the candidate document by almost 40% at best. The plan
   should cover the split membership, the candidate lineage and the 4 MiB source bound together.
2. **Verification, not size, is the practical limit.** A verified pass is expensive, at about
   11 ms and 23 KiB per observation, and about 95% of it is repeated schema validation.
   Extrapolated, one pass over the 100,000-record inventory limit takes about 18 minutes of that
   cost plus 5 to 16 minutes of pairwise comparison, and 2.2 GiB.
   A transport that only lifts size limits would leave verification impractical. The plan should
   require that each observation is validated once per verified population, or that the validator
   is reused, and that memory stays bounded. Those are behavior-preserving changes that differential
   tests can check against the current code.
3. **The membership rules are quadratic.** One derivation costs 5% of a pass at the M0 volume, most
   of it validation. The pairwise term overtakes the linear one near 15,700 observations, and
   extrapolation puts a derivation at about six minutes at 100,000, three times in each verified
   pass. A linear-time derivation has to
   come before the 7,133-observation ceiling can be lifted.

What the plan cannot size without the owner, and this report does not decide: the population a
release must carry, the shapes of the observation, listing, property and source record
identifiers, and the verification time that is acceptable. No format, version or threshold is
proposed here. Any change to the split or lineage wire format is L2 and needs a formal plan, a
threat assessment, explicit approval and independent verification.

**Recommended next increment.** Write the L2 plan and threat assessment for one coordinated
transport covering split membership, candidate lineage and the source bound, with once-per-population
validation, bounded-memory verification and a linear-time derivation. It needs the owner's decision on
the three inputs above and approval to start the L2 process.

## Limits of this evidence

- **Synthetic metadata only.** No real listing, identifier or date was read or measured. The
  identifier lengths and mixes are assumptions. The candidate figures do not depend on the mix,
  but the source and split figures do, which is why several mixes are shown. Timestamps are
  second-resolution UTC (20 characters). The schema allows 32, which adds up to 48 bytes to every
  observation that has timestamps and would lower the source limit by up to 6%, and not at all in
  the `excluded` mix, whose instants are null. The candidate and split documents do not carry
  timestamps.
- **A model, confirmed where it matters.** Capacities come from a size model fitted to small
  production runs. It is exact for the source bytes and the split, and a row or so uncertain for
  the candidate and release, whose documents carry decimal counters. Only the first limit of each
  configuration was re-checked against production at its boundary. The other limits are
  predictions.
- **One machine.** Seconds and memory come from single runs on one macOS ARM64 machine with 10
  CPUs, and one configuration was repeated three times to show the spread. They say nothing
  about Linux CI or a serving host. Peak memory is the process peak and includes the generated
  population.
- **No transfer cost.** The Git and DVC binding is a placeholder, so no DVC command, remote
  storage or network time is included. A real restore adds the object transfer.
- **Extrapolation is labelled.** Anything beyond a measured size is arithmetic, not a
  measurement.
- **Not a quality result.** Nothing here establishes data correctness, feature lineage, leakage
  freedom, isolation or a defensible evaluation. A14 and the M2 exit gate stay open. Exact-revision
  CI for this uncommitted work is unavailable.

## Reproduce

From the checkout, in the locked development environment, one fresh process per command. All
output goes to standard output, apart from progress lines on standard error, and the tool keeps no
state. The first command takes fifteen to twenty minutes because `--confirm` runs the real
pipeline near each boundary.

```bash
.venv/bin/python scripts/measure_pipeline_capacity.py capacity --mixes training,typical --confirm --format markdown
.venv/bin/python scripts/measure_pipeline_capacity.py stages --records 4528 --id-length 16 --mix typical --format markdown
.venv/bin/python scripts/measure_pipeline_capacity.py stages --records 7128 --id-length 16 --mix balanced --through derive --format markdown
.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_pipeline_capacity.py
```

Use `--format json` for every number the tables omit, such as the fitted bytes per observation
and the held-out residuals. Sizes and sealed identities are identical across runs and hash
seeds. Seconds and memory are not.
