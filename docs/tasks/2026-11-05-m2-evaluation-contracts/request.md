# Authorized request

2026-11-05: Start M2 — Data versioning and baseline ML, implementing only its first
coherent increment: versioned public contracts for evaluation eligibility and
exclusions, observation/property references, temporal cutoffs and development
split/cohort membership. Preserve pre-existing changes and legacy interfaces; do
not commit or push. Read the frozen specification and M0/M1/audit/A14 handoffs.

Distinguish listing, observation, property, dataset-release and split identities and
publication, collection, feature-availability and prediction-cutoff times. Keep
membership fixed across candidate comparisons, unresolved identity explicit, and
future-market/unseen-property views separate from restricted final-holdout details.
Avoid target-dependent evaluation selection; verify meaningful synthetic invalid
cases and population/leakage invariants without claiming contracts prove features
or evaluations leakage-free. Review proposed policy before real-data application.

Persist risk, acceptance criteria, plan, verification and recovery; outline later
increments in dependency order. Run relevant development checks after final edits
and record passed/failed/skipped/unavailable outcomes. Stop after the first increment
and report design, tests, limits and one recommended next increment with real-data
prerequisites. Do not claim M2's reproducible-run/development-evaluation gate passed.

No fabricated historical timestamps, matching thresholds, identities or benchmark
results; no scraping, protected-label access, unisolated experiments, data publishing,
trusted-policy changes, promotion, deployment or private row-level reporting.
