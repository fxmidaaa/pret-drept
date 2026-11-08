"""Measure how far the synthetic M2 data pipeline scales: size limits, time and memory.

Backlog item Q03 asks for the candidate, inventory, release and split stages to be tested
together with realistic identifier lengths and volumes, so the bottleneck is visible across the
whole pipeline. This tool runs the production code for those stages, unchanged, on deterministic
synthetic populations inside a directory it creates, resolves and removes. It reads no real data,
uses no network, DVC, credentials or protected labels, and prints aggregate numbers only. Every
stage is production code, so it either succeeds or fails with its own fixed message. The tool only
skips the pure derivation above the production ceiling.

``stages`` runs the pipeline once. Peak memory is the process peak, so use a fresh process per
configuration. ``capacity`` fits a size model from small production runs. The model is affine in
the observation and envelope counts, with measured offsets inside the repeating cycle of each
mix. It derives the largest population each size gate admits and names the first limit. Those
limits are predictions, and fit runs below the default size are faster but can leave the
candidate and release predictions a few rows off. ``--confirm`` runs the production path around
the predicted boundary of the first limit, about a minute per run near the defaults, and reports
the observed boundary. Only that is a production measurement. Output is JSON, or Markdown with
``--format markdown``.

Sizes and sealed identities are deterministic. Seconds and memory belong to the machine that ran
them. A production gate that fails is a finding and exits 0. Malformed arguments exit 2. A
``--confirm`` run with a boundary that cannot be confirmed exits 1, and so does a tool error such
as a failed fit run, which prints a message.
"""

import argparse
import json
import math
import os
import platform
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from fractions import Fraction
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory

from rent_contracts import ContractError
from rent_contracts.evaluation import derive_development_memberships, evaluation_policy_digest
from rent_contracts.inventory import MAX_INVENTORY_RECORDS, PARQUET_FILE
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json
from rent_data.candidates import MAX_REFERENCE_SOURCE_BYTES, build_observation_candidate
from rent_data.inventory_io import write_observation_inventory
from rent_data.release_io import finalize_restoration, write_payload
from rent_data.releases import (
    DVC_VERSION,
    build_dataset_release,
    build_restoration_report,
    content_digest,
)
from rent_data.split_io import materialize_development_split, read_verified_development_split
from rent_data.splits import MAX_SPLIT_OBSERVATIONS

DEFAULT_PER_SOURCE = 600
# Fit runs of 198 to about 600 observations keep every decimal counter in the digit regime of the
# populations that matter. Smaller runs let counters gain a digit between runs, which tilts the
# fitted slope of the candidate and release and moves their predicted capacity by a row or two.
# The unit is a multiple of the row-size period.
DEFAULT_FIT_UNIT = 198
MAX_FIT_UNIT = 300
MIN_ID_LENGTH = 11  # a four-character prefix and seven index digits
MAX_ID_LENGTH = 128  # the schema's identifier maximum
# Source record identifiers have the same schema maximum. Each lineage entry in the candidate and
# each record in a source envelope carries one, so their length moves those sizes one for one.
MIN_RECORD_ID_LENGTH = 14  # "capture-" and six index digits
DEFAULT_RECORD_ID_LENGTH = MIN_RECORD_ID_LENGTH

# Production stages in order. ``derive`` runs the pure membership rules on their own, so the
# cost of the rules can be told apart from the cost of the surrounding verification.
STAGES = (
    "derive",
    "inventory",
    "candidate",
    "payload",
    "release",
    "restoration",
    "split",
    "readback",
)

TRAINING_CUTOFF = "2026-01-20T00:00:00Z"
VALIDATION_WINDOW = {
    "start_inclusive": "2026-02-01T00:00:00Z",
    "end_exclusive": "2026-03-01T00:00:00Z",
}

# Observation kinds: (collection instant, domain status). The tests write out the membership
# each kind derives under the existing v1 rules. ``seen_*`` kinds reuse the training row that
# leads their cycle, so they only make sense in the ``typical`` mix.
_KINDS = {
    "training": ("2026-01-10T12:00:00Z", "valid"),
    "unseen": ("2026-02-12T12:00:00Z", "valid"),
    "seen_property": ("2026-02-13T12:00:00Z", "valid"),
    "seen_listing": ("2026-02-14T12:00:00Z", "valid"),
    "untimed": (None, "valid"),
    "invalid_domain": ("2026-03-02T12:00:00Z", "invalid"),
}
MIXES = {
    # Smallest split rows: the best case for the split document limit.
    "training": ("training",),
    # The six kinds of the shared reference fixture, repeated in order.
    "typical": ("training", "unseen", "seen_property", "seen_listing", "untimed", "invalid_domain"),
    # One-reason excluded rows, whose split capacity the design states in closed form.
    "excluded": ("untimed",),
    # Alternating training and unseen validation rows: the worst case for the derivation.
    "balanced": ("training", "unseen"),
}
# Row sizes repeat with this period, so a fit population is a multiple of it to stay exact.
MIX_PERIOD = math.lcm(*map(len, MIXES.values()))


@dataclass(frozen=True)
class Population:
    """Synthetic observations in identifier order, with the envelopes that carry them."""

    rows: list[dict]
    sources: list[bytes]
    recipe: dict
    policy: dict
    parameters: dict


def _digest(label: str) -> str:
    return content_digest(label.encode("utf-8"))


def _identifier(prefix: str, index: int, length: int) -> str:
    # Fixed width, so identifiers have exactly ``length`` characters and sort in index order.
    # Only the length affects any encoded size, never the characters.
    return f"{prefix}{index:0{length - len(prefix)}d}"


def build_population(
    count: int,
    id_length: int,
    mix: str,
    per_source: int = DEFAULT_PER_SOURCE,
    record_id_length: int = DEFAULT_RECORD_ID_LENGTH,
) -> Population:
    """Build a deterministic synthetic population. Raises ValueError for unusable arguments.

    ``ContractError`` from the production canonicalizer is not caught: an envelope above the
    shared document limit is reported by the caller as a population failure.
    """
    if mix not in MIXES:
        raise ValueError(f"unknown mix: {mix}")
    if not MIN_ID_LENGTH <= id_length <= MAX_ID_LENGTH:
        raise ValueError(f"identifier length must be {MIN_ID_LENGTH} to {MAX_ID_LENGTH}")
    if not 1 <= count <= MAX_INVENTORY_RECORDS:
        raise ValueError(f"record count must be 1 to {MAX_INVENTORY_RECORDS}")
    if per_source < 1:
        raise ValueError("records per source must be positive")
    if not MIN_RECORD_ID_LENGTH <= record_id_length <= MAX_ID_LENGTH:
        raise ValueError(
            f"record identifier length must be {MIN_RECORD_ID_LENGTH} to {MAX_ID_LENGTH}"
        )
    domain_ref, matching_ref = (
        _digest("synthetic domain policy"),
        _digest("synthetic matching policy"),
    )
    evidence = _digest("synthetic temporal evidence")
    cycle = MIXES[mix]
    rows = []
    for index in range(count):
        kind = cycle[index % len(cycle)]
        instant, domain_status = _KINDS[kind]
        leading = index - index % len(cycle)
        seen = kind.startswith("seen_")
        rows.append(
            {
                "contract_version": "1.0.0",
                "observation_id": _identifier("obs-", index, id_length),
                "listing_id": _identifier(
                    "lst-", leading if kind == "seen_listing" else index, id_length
                ),
                "property_identity": {
                    "status": "confirmed",
                    "property_id": _identifier("prp-", leading if seen else index, id_length),
                    "confidence": 0.75 if kind in ("unseen", "seen_property") else None,
                    "policy_ref": matching_ref,
                },
                "domain_policy_ref": domain_ref,
                "domain_status": domain_status,
                "published_at": instant,
                "collected_at": instant,
                "features_available_at": instant,
                "prediction_cutoff_at": instant,
                "temporal_evidence_ref": None if instant is None else evidence,
            }
        )
    sources = []
    for start in range(0, count, per_source):
        envelope = {
            "contract_version": "1.0.0",
            "raw_source_ref": _digest(f"synthetic capacity source {start}"),
            "acquisition_provenance_ref": None,
            "acquisition_period": {"start": None, "end": None},
            "records": [
                {
                    "source_record_id": _identifier("capture-", offset, record_id_length),
                    "observation": row,
                }
                for offset, row in enumerate(rows[start : start + per_source])
            ],
        }
        sources.append(canonical_json(envelope).encode("utf-8"))
    policy = {
        "contract_version": "1.0.0",
        "policy_version": "synthetic-split-v1",
        "domain_policy_ref": domain_ref,
        "property_matching_policy_ref": matching_ref,
        "selection_basis": "non_target_metadata_only",
        "property_matching_basis": "non_target_signals_only",
        "eligibility_rule": "non_target_domain_and_observation_time_v1",
        "unseen_property_rule": "confirmed_absence_from_resolved_training_v1",
        "target_unit": "EUR/month",
    }
    policy["policy_digest"] = evaluation_policy_digest(policy)
    return Population(
        rows=rows,
        sources=sources,
        recipe={
            "dataset_family": "synthetic-capacity-probe",
            "transformation_ref": _digest("synthetic transformation"),
            "projection_policy_ref": _digest("synthetic projection"),
            "domain_policy_ref": domain_ref,
            "property_matching_policy_ref": matching_ref,
        },
        policy=policy,
        parameters={
            "training_cutoff": TRAINING_CUTOFF,
            "validation_window": dict(VALIDATION_WINDOW),
            "creation_provenance": {
                "source_snapshot_ref": _digest("synthetic split source snapshot"),
                "created_at": "2026-03-03T12:00:00Z",
            },
        },
    )


def _canonical_size(document: dict) -> int:
    return len(canonical_json(document).encode("utf-8"))


def _binding(artifacts: list[dict]) -> dict:
    # Placeholder Git and DVC identities. No DVC runs here, so object transfer is not measured.
    return {
        "metadata": {
            "commit": "e" * 40,
            "path": "payload.dvc",
            "digest": _digest("synthetic metadata"),
        },
        "dvc": {
            "version": DVC_VERSION,
            "hash_algorithm": "md5",
            "object_id": "b" * 32 + ".dir",
            "size_bytes": sum(row["size_bytes"] for row in artifacts),
            "file_count": len(artifacts),
            "tool_profile_ref": _digest("synthetic tool profile"),
        },
    }


def _derive(ctx: dict) -> None:
    population = ctx["population"]
    derive_development_memberships(
        population.rows,
        policy=population.policy,
        training_cutoff=population.parameters["training_cutoff"],
        validation_window=population.parameters["validation_window"],
        max_inventory_records=len(population.rows),
    )


def _inventory(ctx: dict) -> None:
    directory = ctx["root"] / "inventory"
    write_observation_inventory(directory, ctx["population"].rows)
    ctx["sizes"]["parquet_bytes"] = (directory / PARQUET_FILE).stat().st_size


def _candidate(ctx: dict) -> None:
    population = ctx["population"]
    ctx["candidate"] = build_observation_candidate(
        population.sources, **population.recipe, inventory_directory=ctx["root"] / "inventory"
    )
    ctx["sizes"]["candidate_bytes"] = _canonical_size(ctx["candidate"])


def _payload(ctx: dict) -> None:
    candidate = ctx["candidate"]
    (ctx["root"] / "restored").mkdir()
    ctx["artifacts"] = write_payload(
        ctx["root"] / "restored" / "payload",
        candidate,
        source_documents=ctx["population"].sources,
        expected_candidate_ref=candidate["candidate_digest"],
        inventory_directory=ctx["root"] / "inventory",
    )


def _release(ctx: dict) -> None:
    ctx["release"] = build_dataset_release(
        ctx["candidate"],
        source_documents=ctx["population"].sources,
        inventory_directory=ctx["root"] / "restored" / "payload" / "inventory",
        binding=_binding(ctx["artifacts"]),
        artifacts=ctx["artifacts"],
    )
    ctx["sizes"]["release_bytes"] = _canonical_size(ctx["release"])
    ctx["identities"]["release_digest"] = ctx["release"]["release_digest"]


def _restoration(ctx: dict) -> None:
    release = ctx["release"]
    finalize_restoration(
        ctx["root"] / "restored",
        build_restoration_report(release),
        manifest=release,
        expected_release_ref=release["release_digest"],
    )


def _split(ctx: dict) -> None:
    population, release = ctx["population"], ctx["release"]
    ctx["split"] = materialize_development_split(
        ctx["root"] / "restored",
        ctx["root"] / "split",
        release=release,
        policy=population.policy,
        expected_release_ref=release["release_digest"],
        expected_policy_ref=population.policy["policy_digest"],
        **population.parameters,
    )
    ctx["sizes"]["split_bytes"] = _canonical_size(ctx["split"])
    ctx["identities"]["split_digest"] = ctx["split"]["split_digest"]


def _readback(ctx: dict) -> None:
    population, release = ctx["population"], ctx["release"]
    read_verified_development_split(
        ctx["root"] / "split",
        restored_directory=ctx["root"] / "restored",
        release=release,
        policy=population.policy,
        expected_release_ref=release["release_digest"],
        expected_policy_ref=population.policy["policy_digest"],
        expected_split_ref=ctx["split"]["split_digest"],
    )


_ACTIONS = dict(
    zip(
        STAGES,
        (_derive, _inventory, _candidate, _payload, _release, _restoration, _split, _readback),
        strict=True,
    )
)


def _peak_rss_mib() -> float | None:
    try:
        import resource
    except ImportError:  # not available on Windows
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is bytes on macOS and kibibytes on Linux.
    return round(peak / (1024 * 1024 if sys.platform == "darwin" else 1024), 1)


def run_stages(
    count: int,
    id_length: int,
    mix: str,
    *,
    per_source: int = DEFAULT_PER_SOURCE,
    record_id_length: int = DEFAULT_RECORD_ID_LENGTH,
    through: str = "readback",
) -> dict:
    """Run the production path up to ``through`` and report what each stage did.

    The run stops at the first production failure and records its fixed message. Sizes and
    identities are deterministic; seconds and peak memory are not.
    """
    if through not in STAGES:
        raise ValueError(f"unknown stage: {through}")
    result = {
        "parameters": {
            "records": count,
            "id_length": id_length,
            "mix": mix,
            "per_source": per_source,
            "record_id_length": record_id_length,
            "through": through,
        },
        "outcome": "ok",
        "failed_stage": None,
        "message": None,
        "sizes": {},
        "identities": {},
        "stages": [],
    }

    def log(stage: str, outcome: str, started: float, message: str | None = None) -> None:
        entry = {
            "stage": stage,
            "outcome": outcome,
            "seconds": round(time.perf_counter() - started, 3),
            "peak_rss_mib": _peak_rss_mib(),
        }
        if message is not None:
            entry["message"] = message
        result["stages"].append(entry)

    def fail(stage: str, started: float, error: ContractError) -> dict:
        log(stage, "failed", started, str(error))
        result.update(outcome="failed", failed_stage=stage, message=str(error))
        return result

    started = time.perf_counter()
    try:
        population = build_population(count, id_length, mix, per_source, record_id_length)
    except ContractError as error:
        return fail("population", started, error)
    result["population_seconds"] = round(time.perf_counter() - started, 3)
    result["baseline_rss_mib"] = _peak_rss_mib()
    result["sizes"] = {
        "source_bytes": sum(len(raw) for raw in population.sources),
        "source_documents": len(population.sources),
        "largest_source_bytes": max(len(raw) for raw in population.sources),
    }
    with TemporaryDirectory(prefix="rent-capacity-") as scratch:
        ctx = {
            "population": population,
            "root": Path(scratch).resolve(),
            "sizes": result["sizes"],
            "identities": result["identities"],
        }
        for stage in STAGES:
            started = time.perf_counter()
            if stage == "derive" and count > MAX_SPLIT_OBSERVATIONS:
                # Production rejects such a population before deriving, and the rules are
                # quadratic in the training and validation rows, so measuring them is pointless.
                log(stage, "skipped", started, "above the production split population ceiling")
            else:
                try:
                    _ACTIONS[stage](ctx)
                except ContractError as error:
                    return fail(stage, started, error)
                log(stage, "ok", started)
            if stage == through:
                break
    return result


@dataclass(frozen=True)
class Fit:
    """A size model, exact in rationals.

    size = per_record * (records in whole cycles) + phases[records left over] + per_source *
    sources + fixed. The rows of some mixes differ in size, so the size repeats every
    ``len(phases)`` observations. ``phases[j]`` is the measured size of the first ``j``
    observations of a cycle, which makes the prediction exact at every count and not only at
    whole cycles.
    """

    per_record: Fraction
    per_source: Fraction
    fixed: Fraction
    residual: Fraction  # predicted minus measured on the held-out run
    phases: tuple[Fraction, ...] = (Fraction(0),)

    def predict(self, records: int, sources: int) -> Fraction:
        cycle = len(self.phases)
        return (
            self.per_record * (records - records % cycle)
            + self.phases[records % cycle]
            + self.per_source * sources
            + self.fixed
        )


def fit_series(
    first: tuple[int, int, int],
    second: tuple[int, int, int],
    third: tuple[int, int, int],
    held_out: tuple[int, int, int],
    phases: tuple[int, ...] = (0,),
) -> Fit:
    """Solve the model from three (records, sources, size) runs and check a fourth.

    ``first`` and ``second`` share a source count and ``second`` and ``third`` a record count,
    so the record and source terms are separately identified. Both ``first`` and ``second`` are
    whole cycles of ``len(phases)`` observations, and ``phases[0]`` is zero.
    """
    (n1, e1, s1), (n2, e2, s2), (n3, e3, s3) = first, second, third
    cycle = len(phases)
    if e1 != e2 or n2 != n3 or n1 == n2 or e2 == e3 or not cycle or phases[0] != 0:
        raise ValueError("the runs do not identify the size model")
    if n1 % cycle or n2 % cycle:
        raise ValueError("the first two runs must be whole cycles")
    per_record = Fraction(s2 - s1, n2 - n1)
    per_source = Fraction(s3 - s2, e3 - e2)
    fixed = s1 - per_record * n1 - per_source * e1
    fit = Fit(per_record, per_source, fixed, Fraction(0), tuple(map(Fraction, phases)))
    n4, e4, s4 = held_out
    return replace(fit, residual=fit.predict(n4, e4) - s4)


def largest_population(fit: Fit, rows_per_source: int, limit: int) -> int | None:
    """Largest record count whose predicted size is at most ``limit``.

    Returns None when the size never grows. Raises ValueError for a model that shrinks, which
    would mean the measured runs do not describe a size that increases with the population.
    """
    if fit.per_record < 0 or fit.per_source < 0:
        raise ValueError("size model does not grow with the population")
    if fit.per_record == 0 and fit.per_source == 0:
        return None

    def size(records: int) -> Fraction:
        return fit.predict(records, math.ceil(records / rows_per_source))

    if size(1) > limit:
        return 0
    low, high = 1, 2
    while size(high) <= limit:
        low, high = high, high * 2
    while high - low > 1:
        middle = (low + high) // 2
        low, high = (middle, high) if size(middle) <= limit else (low, middle)
    return low


@dataclass(frozen=True)
class Gate:
    """A production size gate: the artifact it bounds and how production reports a breach."""

    name: str
    series: str
    limit: int
    stage: str
    message: str
    # False when decimal counters make the fitted size a few bytes uncertain.
    exact: bool


GATES = (
    Gate(
        "source bytes",
        "source_bytes",
        MAX_REFERENCE_SOURCE_BYTES,
        "candidate",
        "source inventory size limit exceeded",
        True,
    ),
    Gate(
        "candidate document",
        "candidate_bytes",
        MAX_DOCUMENT_BYTES,
        "candidate",
        "document size limit exceeded",
        False,
    ),
    Gate(
        "release document",
        "release_bytes",
        MAX_DOCUMENT_BYTES,
        "release",
        "document size limit exceeded",
        False,
    ),
    Gate(
        "split document",
        "split_bytes",
        MAX_DOCUMENT_BYTES,
        "split",
        "development split output size limit exceeded",
        True,
    ),
)
INVENTORY_RECORDS = "inventory records"
# The candidate and release sizes carry decimal counters, so their predicted capacity can be a
# row off. Limits that close together are reported as tied, and either may be the one that fails.
TIE_ROWS = 1
# A confirmation searches this far either side of the prediction, so its cost is bounded.
SEARCH_WINDOW = TIE_ROWS + 3
CAPACITY_BASIS = (
    "limits are predicted by a size model fitted to small production runs; "
    "only a confirmation is a production measurement"
)


def _series_points(runs: list[dict]) -> dict[str, list[tuple[int, int, int]]]:
    points = {gate.series: [] for gate in GATES}
    for run in runs:
        sizes = run["sizes"]
        for series in points:
            points[series].append(
                (run["parameters"]["records"], sizes["source_documents"], sizes[series])
            )
    return points


def fit_runs(
    id_length: int, mix: str, unit: int, record_id_length: int = DEFAULT_RECORD_ID_LENGTH
) -> dict[str, Fit]:
    """Fit every gate's artifact from small production runs.

    Four runs identify the model, and the last, which ends part-way through a cycle, is held out.
    A mix whose rows differ in size adds one run per further observation of its cycle, each in
    a single envelope, to measure how the size grows within a cycle.
    """
    if unit < 1 or unit % MIX_PERIOD:
        raise ValueError(f"fit unit must be a positive multiple of {MIX_PERIOD}")
    cycle = len(MIXES[mix])
    layout = [(unit, unit), (2 * unit, 2 * unit), (2 * unit, unit), (3 * unit + cycle - 1, unit)]
    layout += [(unit + extra, unit + cycle) for extra in range(1, cycle)]
    runs = [
        run_stages(
            records,
            id_length,
            mix,
            per_source=rows,
            record_id_length=record_id_length,
            through="split",
        )
        for records, rows in layout
    ]
    for run in runs:
        if run["outcome"] != "ok":
            raise RuntimeError(f"a small fit run failed at {run['failed_stage']}: {run['message']}")
    fits = {}
    for series, points in _series_points(runs).items():
        base = points[0]
        steps = [points[3 + extra] for extra in range(1, cycle)]
        if any(sources != base[1] for _, sources, _ in steps):
            raise RuntimeError("the phase runs must use the same number of source envelopes")
        phases = (0, *(size - base[2] for _, _, size in steps))
        fits[series] = fit_series(*points[:3], points[3], phases)
    return fits


def find_boundary(
    passes: Callable[[int], dict], predicted: int, window: int = SEARCH_WINDOW
) -> tuple[int, dict] | None:
    """Largest count near ``predicted`` that passes, with the failure one record beyond it.

    ``passes(count)`` runs the production path and returns its result. The search assumes that
    passing is monotone in the count, as every size gate is, and gives up after ``window`` steps.
    """
    count = predicted
    result = passes(count)
    if result["outcome"] == "ok":
        while count <= predicted + window:
            beyond = passes(count + 1)
            if beyond["outcome"] != "ok":
                return count, beyond
            count += 1
        return None
    failure = result
    while count > max(1, predicted - window):
        count -= 1
        result = passes(count)
        if result["outcome"] == "ok":
            return count, failure
        failure = result
    return None


def capacity_report(
    id_length: int,
    mix: str,
    *,
    per_source: int = DEFAULT_PER_SOURCE,
    record_id_length: int = DEFAULT_RECORD_ID_LENGTH,
    fit_unit: int = DEFAULT_FIT_UNIT,
    confirm: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Predict the largest population each size gate admits, and optionally confirm the first."""
    if per_source < 1:
        raise ValueError("records per source must be positive")
    fits = fit_runs(id_length, mix, fit_unit, record_id_length)
    source = fits["source_bytes"]
    if source.per_record * per_source + source.per_source > MAX_DOCUMENT_BYTES:
        raise ValueError("records per source exceed the document limit at this identifier length")
    gates = {
        gate.name: largest_population(fits[gate.series], per_source, gate.limit) for gate in GATES
    }
    gates[INVENTORY_RECORDS] = MAX_INVENTORY_RECORDS
    limits = sorted((count, name) for name, count in gates.items() if count is not None)
    (capacity, first), others = limits[0], limits[1:]
    report = {
        "mix": mix,
        "id_length": id_length,
        "record_id_length": record_id_length,
        "per_source": per_source,
        "fit_unit": fit_unit,
        "fit": {
            series: {
                "bytes_per_record": float(fit.per_record),
                "bytes_per_source": float(fit.per_source),
                "fixed_bytes": float(fit.fixed),
                "held_out_residual_bytes": float(fit.residual),
            }
            for series, fit in fits.items()
        },
        "gates": gates,
        "first_limit": first,
        "tied_limits": [name for count, name in others if count <= capacity + TIE_ROWS],
        "capacity": capacity,
        "next_limit": others[0][1] if others else None,
        "next_capacity": others[0][0] if others else None,
        "headroom_percent": (
            round(100 * (others[0][0] / capacity - 1), 1) if others and capacity else None
        ),
        "confirmation": None,
    }
    if confirm:
        report["confirmation"] = confirm_boundary(report, id_length, mix, per_source, progress)
    return report


def confirm_boundary(
    report: dict,
    id_length: int,
    mix: str,
    per_source: int,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Check the predicted capacity against production, and which gate then fails.

    Confirmed means the largest passing population equals the prediction, to within a row when
    the first limit or one tied with it has an uncertain model, and the failure one record
    beyond it is the stage and message of the first limit or of a limit tied with it.
    """
    gate = next((gate for gate in GATES if gate.name == report["first_limit"]), None)
    if gate is None:
        return {"gate": report["first_limit"], "confirmed": None, "note": "not a size gate"}
    if report["capacity"] < 1:
        return {"gate": gate.name, "confirmed": None, "note": "no population fits"}
    if report["capacity"] + SEARCH_WINDOW + 1 > MAX_INVENTORY_RECORDS:
        return {"gate": gate.name, "confirmed": None, "note": "at the inventory record limit"}

    def passes(count: int) -> dict:
        if progress is not None:
            progress(f"confirming {mix}, {id_length}-character identifiers: {count:,} observations")
        return run_stages(
            count,
            id_length,
            mix,
            per_source=per_source,
            record_id_length=report["record_id_length"],
        )

    boundary = find_boundary(passes, report["capacity"])
    if boundary is None:
        return {"gate": gate.name, "predicted": report["capacity"], "confirmed": False}
    observed, failure = boundary
    near = [
        candidate
        for candidate in GATES
        if candidate.name in (report["first_limit"], *report["tied_limits"])
    ]
    tolerance = TIE_ROWS if any(not candidate.exact for candidate in near) else 0
    explained = {(candidate.stage, candidate.message) for candidate in near}
    return {
        "gate": gate.name,
        "predicted": report["capacity"],
        "observed": observed,
        "tolerance_rows": tolerance,
        "failed_stage": failure["failed_stage"],
        "message": failure["message"],
        "confirmed": (
            abs(observed - report["capacity"]) <= tolerance
            and (failure["failed_stage"], failure["message"]) in explained
        ),
    }


def environment() -> dict:
    try:
        pyarrow = metadata.version("pyarrow")
    except metadata.PackageNotFoundError:
        pyarrow = "not installed"
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "pyarrow": pyarrow,
        "cpu_count": os.cpu_count(),
    }


def _count(value: int | None) -> str:
    return "none" if value is None else f"{value:,}"


def format_stages(result: dict) -> str:
    parameters, sizes = result["parameters"], result["sizes"]
    lines = [
        f"{parameters['records']:,} observations, {parameters['id_length']}-character "
        f"identifiers, {parameters['record_id_length']}-character source record identifiers, "
        f"mix `{parameters['mix']}`, {parameters['per_source']} per source document "
        f"({sizes.get('source_documents', 'n/a')} documents).",
        "",
        "| Stage | Outcome | Seconds | Peak RSS (MiB) |",
        "| --- | --- | ---: | ---: |",
    ]
    for stage in result["stages"]:
        outcome = stage["outcome"]
        if outcome != "ok":
            outcome += f": {stage['message']}"
        peak = "n/a" if stage["peak_rss_mib"] is None else f"{stage['peak_rss_mib']:.1f}"
        lines.append(f"| {stage['stage']} | {outcome} | {stage['seconds']:.2f} | {peak} |")
    names = {
        "source_bytes": "source",
        "largest_source_bytes": "largest source document",
        "parquet_bytes": "Parquet",
        "candidate_bytes": "candidate",
        "release_bytes": "release",
        "split_bytes": "split",
    }
    shown = [f"{label} {sizes[key]:,}" for key, label in names.items() if key in sizes]
    lines += ["", "Bytes: " + " · ".join(shown) + "."]
    if "baseline_rss_mib" in result:
        lines.append(
            f"Generating the population took {result['population_seconds']:.2f} s. "
            f"Resident memory was {result['baseline_rss_mib']} MiB before the first stage."
        )
    return "\n".join(lines)


def format_capacity(reports: list[dict]) -> str:
    lines = [
        "| Mix | ID chars | Record ID chars | Source bytes | Candidate | Split | First limit | "
        "Headroom if lifted | Production boundary |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for report in reports:
        gates, check = report["gates"], report["confirmation"]
        if check is None:
            boundary = "not run"
        elif check.get("confirmed") is None:
            boundary = "not applicable"
        elif check["confirmed"]:
            boundary = f"confirmed at {check['observed']:,}"
        else:
            boundary = f"observed {_count(check.get('observed'))}"
        if report["headroom_percent"] is None:
            headroom = "none"
        else:
            headroom = f"+{report['headroom_percent']}% ({report['next_limit']})"
        lines.append(
            f"| {report['mix']} | {report['id_length']} | {report['record_id_length']} "
            f"| {_count(gates['source bytes'])} "
            f"| {_count(gates['candidate document'])} | {_count(gates['split document'])} "
            f"| {' / '.join([report['first_limit'], *report['tied_limits']])} "
            f"({report['capacity']:,}) | {headroom} | {boundary} |"
        )
    lines += [
        "",
        f"A slash joins limits within {TIE_ROWS} row of each other. {CAPACITY_BASIS.capitalize()}.",
    ]
    if min(report["fit_unit"] for report in reports) < DEFAULT_FIT_UNIT:
        lines.append(
            f"Fit units below {DEFAULT_FIT_UNIT} run faster but can leave the candidate and "
            "release predictions several rows off."
        )
    return "\n".join(lines)


def _environment_line(details: dict) -> str:
    return (
        f"Environment: CPython {details['python']}, {details['system']} {details['machine']}, "
        f"PyArrow {details['pyarrow']}, {details['cpu_count']} CPUs.\n"
    )


def _bounded(minimum: int, maximum: int):
    def parse(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError("must be an integer") from None
        if not minimum <= value <= maximum:
            raise argparse.ArgumentTypeError(f"must be {minimum} to {maximum}")
        return value

    return parse


def _list_of(parse):
    def parse_list(text: str) -> tuple:
        return tuple(parse(item) for item in text.split(","))

    return parse_list


def _mix(text: str) -> str:
    if text not in MIXES:
        raise argparse.ArgumentTypeError(f"must be one of {', '.join(MIXES)}")
    return text


def _fit_unit(text: str) -> int:
    # Two units share one envelope. At the longest identifiers that must stay under the document
    # limit, and every fit run must pass the production gates.
    value = _bounded(1, MAX_FIT_UNIT)(text)
    if value % MIX_PERIOD:
        raise argparse.ArgumentTypeError(f"must be a multiple of {MIX_PERIOD}")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--format", choices=("json", "markdown"), default="json")
    shared.add_argument(
        "--per-source",
        type=_bounded(1, MAX_INVENTORY_RECORDS),
        default=DEFAULT_PER_SOURCE,
        help="observations per source envelope (default %(default)s)",
    )
    shared.add_argument(
        "--record-id-length",
        type=_bounded(MIN_RECORD_ID_LENGTH, MAX_ID_LENGTH),
        default=DEFAULT_RECORD_ID_LENGTH,
        help="characters in every source record identifier (default %(default)s)",
    )
    stages = commands.add_parser("stages", parents=[shared], help="run the pipeline once")
    stages.add_argument(
        "--records",
        type=_bounded(1, MAX_INVENTORY_RECORDS),
        required=True,
        help="number of synthetic observations",
    )
    stages.add_argument(
        "--id-length",
        type=_bounded(MIN_ID_LENGTH, MAX_ID_LENGTH),
        default=16,
        help="characters in every identifier (default %(default)s)",
    )
    stages.add_argument(
        "--mix",
        type=_mix,
        default="typical",
        help=f"one of {', '.join(MIXES)} (default %(default)s)",
    )
    stages.add_argument(
        "--through",
        choices=STAGES,
        default="readback",
        help="last stage to run (default %(default)s)",
    )
    capacity = commands.add_parser(
        "capacity", parents=[shared], help="derive the largest population each gate admits"
    )
    capacity.add_argument(
        "--id-lengths",
        type=_list_of(_bounded(MIN_ID_LENGTH, MAX_ID_LENGTH)),
        default=(16, 32, 64, 128),
        help="comma-separated identifier lengths (default 16,32,64,128)",
    )
    capacity.add_argument(
        "--mixes",
        type=_list_of(_mix),
        default=("training", "typical"),
        help=f"comma-separated mixes from {', '.join(MIXES)} (default training,typical)",
    )
    capacity.add_argument(
        "--fit-unit",
        type=_fit_unit,
        default=DEFAULT_FIT_UNIT,
        help=(
            f"size of the smallest fit run, a multiple of {MIX_PERIOD} (default %(default)s). "
            "Smaller runs are faster but can leave the candidate and release predictions several "
            "rows off"
        ),
    )
    capacity.add_argument(
        "--confirm",
        action="store_true",
        help="run the pipeline around each first limit (about a minute per run near the defaults)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    details = environment()
    try:
        if arguments.command == "stages":
            result = run_stages(
                arguments.records,
                arguments.id_length,
                arguments.mix,
                per_source=arguments.per_source,
                record_id_length=arguments.record_id_length,
                through=arguments.through,
            )
            document, text, status = {"environment": details, **result}, None, 0
            if arguments.format == "markdown":
                text = _environment_line(details) + "\n" + format_stages(result)
        else:
            progress = None
            if arguments.confirm:
                progress = lambda text: print(text, file=sys.stderr, flush=True)  # noqa: E731
            reports = [
                capacity_report(
                    length,
                    mix,
                    per_source=arguments.per_source,
                    record_id_length=arguments.record_id_length,
                    fit_unit=arguments.fit_unit,
                    confirm=arguments.confirm,
                    progress=progress,
                )
                for mix in arguments.mixes
                for length in arguments.id_lengths
            ]
            document = {"environment": details, "basis": CAPACITY_BASIS, "reports": reports}
            text = None
            status = int(
                any((report["confirmation"] or {}).get("confirmed") is False for report in reports)
            )
            if arguments.format == "markdown":
                text = _environment_line(details) + "\n" + format_capacity(reports)
    except (RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(text if text is not None else json.dumps(document, indent=2, sort_keys=True))
    return status


if __name__ == "__main__":
    sys.exit(main())
