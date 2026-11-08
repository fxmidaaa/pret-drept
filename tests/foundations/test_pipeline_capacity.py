"""The capacity probe: populations, stage runner, size model, boundaries and determinism.

Synthetic metadata only. The probe calls the production pipeline, so these tests use tiny
populations and check its reports against hand-written expectations and against the
closed-form split capacity that the design already states. Reported seconds and memory depend
on the machine and are only checked for shape. The probe is tooling outside the shipped
packages, so this module runs in the checkout and is not part of the source distribution.
"""

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import pytest

from rent_contracts import ContractError
from rent_contracts.evaluation import derive_development_memberships, validate_observation_reference
from rent_contracts.inventory import MAX_INVENTORY_RECORDS, PARQUET_FILE
from rent_contracts.validation import (
    MAX_DOCUMENT_BYTES,
    canonical_json,
    load_document,
    validate_document,
)
from rent_data.inventory_io import write_observation_inventory
from scripts import measure_pipeline_capacity as probe

SCRIPT = Path(probe.__file__)
ROOT = SCRIPT.parents[1]

# The membership each observation kind must derive under the existing v1 rules, written out by
# hand and never generated: partition, eligibility reasons, cohorts, unseen-property reasons.
EXPECTED = {
    "training": ("training", [], [], ["not_development_validation"]),
    "unseen": ("development_validation", [], ["future_market", "unseen_property"], []),
    "seen_property": (
        "development_validation",
        [],
        ["future_market"],
        ["property_overlap_training"],
    ),
    "seen_listing": (
        "development_validation",
        [],
        ["future_market"],
        ["listing_seen_in_training", "property_overlap_training"],
    ),
    "untimed": ("excluded", ["temporal_evidence_missing"], [], ["not_development_validation"]),
    "invalid_domain": (
        "excluded",
        ["invalid_non_target_domain", "outside_development_windows"],
        [],
        ["not_development_validation"],
    ),
}
# The documented cycle of each mix, so a silent change to a mix fails here.
CYCLES = {
    "training": ["training"],
    "typical": ["training", "unseen", "seen_property", "seen_listing", "untimed", "invalid_domain"],
    "excluded": ["untimed"],
    "balanced": ["training", "unseen"],
}
SMALL = {"per_source": 12}


@pytest.fixture(scope="module")
def typical_fit():
    """One fit of the uneven mix, shared because it does not depend on any limit patched later."""
    return probe.fit_runs(16, "typical", 12)


def run_small(count=24, length=16, mix="typical", **overrides):
    return probe.run_stages(count, length, mix, **{**SMALL, **overrides})


# --- Populations ---------------------------------------------------------------------------


def test_the_named_mixes_are_exactly_the_documented_cycles():
    assert {name: list(cycle) for name, cycle in probe.MIXES.items()} == CYCLES


@pytest.mark.parametrize("mix", CYCLES)
def test_each_mix_derives_the_hand_written_memberships(mix):
    population = probe.build_population(36, 16, mix, per_source=12)
    memberships = derive_development_memberships(
        population.rows,
        policy=population.policy,
        training_cutoff=population.parameters["training_cutoff"],
        validation_window=population.parameters["validation_window"],
        max_inventory_records=36,
    )
    cycle = CYCLES[mix]
    assert len(memberships) == 36
    for index, row in enumerate(memberships):
        partition, reasons, cohorts, unseen = EXPECTED[cycle[index % len(cycle)]]
        assert row == {
            "observation_id": population.rows[index]["observation_id"],
            "partition": partition,
            "eligibility_exclusions": reasons,
            "cohorts": cohorts,
            "unseen_property_exclusions": unseen,
        }


@pytest.mark.parametrize("length", [probe.MIN_ID_LENGTH, 16, probe.MAX_ID_LENGTH])
def test_identifiers_have_the_requested_length_and_every_row_validates(length):
    population = probe.build_population(24, length, "typical", per_source=12)
    for row in population.rows:
        validate_observation_reference(row)
        lengths = {len(row["observation_id"]), len(row["listing_id"])}
        lengths.add(len(row["property_identity"]["property_id"]))
        assert lengths == {length}
    keys = [row["observation_id"] for row in population.rows]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)
    assert probe.build_population(24, length, "typical", per_source=12) == population


@pytest.mark.parametrize("length", [probe.MIN_RECORD_ID_LENGTH, 64, probe.MAX_ID_LENGTH])
def test_source_record_identifiers_have_the_requested_length_and_pass_production(length):
    population = probe.build_population(24, 16, "typical", per_source=12, record_id_length=length)
    for raw in population.sources:
        envelope = load_document(raw)
        validate_document("observation-source", envelope)
        keys = [record["source_record_id"] for record in envelope["records"]]
        assert {len(key) for key in keys} == {length}
        assert len(set(keys)) == len(keys)


@pytest.mark.parametrize(
    "arguments",
    [
        (0, 16, "typical"),
        (MAX_INVENTORY_RECORDS + 1, 16, "typical"),
        (12, probe.MIN_ID_LENGTH - 1, "typical"),
        (12, probe.MAX_ID_LENGTH + 1, "typical"),
        (12, 16, "unknown"),
        (12, 16, "typical", 0),
        (12, 16, "typical", 12, probe.MIN_RECORD_ID_LENGTH - 1),
        (12, 16, "typical", 12, probe.MAX_ID_LENGTH + 1),
    ],
)
def test_unusable_population_arguments_are_rejected(arguments):
    with pytest.raises(ValueError):
        probe.build_population(*arguments)


# --- Stage runner --------------------------------------------------------------------------


def test_a_complete_run_reports_every_stage_and_deterministic_artifacts():
    first, second = run_small(), run_small()
    assert first["outcome"] == "ok"
    assert first["failed_stage"] is None
    assert [stage["stage"] for stage in first["stages"]] == list(probe.STAGES)
    assert {stage["outcome"] for stage in first["stages"]} == {"ok"}
    assert set(first["sizes"]) == {
        "source_bytes",
        "source_documents",
        "largest_source_bytes",
        "parquet_bytes",
        "candidate_bytes",
        "release_bytes",
        "split_bytes",
    }
    assert set(first["identities"]) == {"release_digest", "split_digest"}
    assert first["sizes"] == second["sizes"]
    assert first["identities"] == second["identities"]
    population = probe.build_population(24, 16, "typical", per_source=12)
    assert first["sizes"]["source_bytes"] == sum(len(raw) for raw in population.sources)
    assert first["sizes"]["source_documents"] == len(population.sources) == 2
    peaks = [stage["peak_rss_mib"] for stage in first["stages"]]
    if peaks[0] is not None:  # resource is unavailable on some platforms
        assert first["baseline_rss_mib"] <= peaks[0]
        # A Python process with these imports is tens of MiB. A bytes-versus-KiB unit error
        # would put it near zero or in the millions.
        assert 10 < peaks[0] < 16_384
    assert all(stage["seconds"] >= 0 for stage in first["stages"])


def test_recorded_sizes_and_identities_are_those_of_the_production_artifacts(monkeypatch, tmp_path):
    captured = {}

    def spy(name):
        real = getattr(probe, name)

        def wrapper(*arguments, **keywords):
            captured[name] = real(*arguments, **keywords)
            return captured[name]

        monkeypatch.setattr(probe, name, wrapper)

    for name in (
        "build_observation_candidate",
        "build_dataset_release",
        "materialize_development_split",
    ):
        spy(name)
    result = run_small()

    def size(document):
        return len(canonical_json(document).encode("utf-8"))

    assert result["sizes"]["candidate_bytes"] == size(captured["build_observation_candidate"])
    assert result["sizes"]["release_bytes"] == size(captured["build_dataset_release"])
    assert result["sizes"]["split_bytes"] == size(captured["materialize_development_split"])
    assert result["identities"] == {
        "release_digest": captured["build_dataset_release"]["release_digest"],
        "split_digest": captured["materialize_development_split"]["split_digest"],
    }
    # The Parquet inventory is written by the same deterministic production writer.
    population = probe.build_population(24, 16, "typical", per_source=12)
    write_observation_inventory(tmp_path / "inventory", population.rows)
    assert (
        result["sizes"]["parquet_bytes"] == (tmp_path / "inventory" / PARQUET_FILE).stat().st_size
    )


def test_the_split_size_follows_the_closed_form_for_identical_rows():
    row = {
        "observation_id": "x" * 16,
        "partition": "excluded",
        "eligibility_exclusions": ["temporal_evidence_missing"],
        "cohorts": [],
        "unseen_property_exclusions": ["not_development_validation"],
    }
    row_bytes = len(canonical_json(row).encode("utf-8"))
    # 733 fixed bytes (734 with an empty array), then each row and one comma between rows.
    for count in (6, 24):
        sizes = run_small(count, mix="excluded", through="split")["sizes"]
        assert sizes["split_bytes"] == 733 + count * (row_bytes + 1)


def test_the_run_stops_after_the_requested_stage():
    result = run_small(through="candidate")
    assert [stage["stage"] for stage in result["stages"]] == ["derive", "inventory", "candidate"]
    assert set(result["sizes"]) == {
        "source_bytes",
        "source_documents",
        "largest_source_bytes",
        "parquet_bytes",
        "candidate_bytes",
    }
    assert result["identities"] == {}
    with pytest.raises(ValueError):
        run_small(through="finished")


def test_a_production_failure_is_reported_with_its_message_and_stops_the_run(monkeypatch, tmp_path):
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", 1_000)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    result = run_small()
    source_gate = probe.GATES[0]
    assert result["outcome"] == "failed"
    assert result["failed_stage"] == source_gate.stage == "candidate"
    assert result["message"] == source_gate.message
    assert [(s["stage"], s["outcome"]) for s in result["stages"]] == [
        ("derive", "ok"),
        ("inventory", "ok"),
        ("candidate", "failed"),
    ]
    assert result["stages"][-1]["message"] == source_gate.message
    assert "candidate_bytes" not in result["sizes"]
    assert list(tmp_path.iterdir()) == []  # the owned directory is removed after a failure


def test_a_run_removes_its_owned_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert run_small()["outcome"] == "ok"
    assert list(tmp_path.iterdir()) == []


def test_an_envelope_above_the_document_limit_is_a_population_failure():
    # 1,100 maximum-length rows exceed 1 MiB in one envelope; the candidate gate is not reached.
    result = probe.run_stages(1_100, 128, "training", per_source=1_100)
    assert result["outcome"] == "failed"
    assert result["failed_stage"] == "population"
    assert result["message"] == "document size limit exceeded"
    assert [stage["stage"] for stage in result["stages"]] == ["population"]
    assert result["sizes"] == {}


def test_the_quadratic_derivation_is_skipped_above_the_production_ceiling(monkeypatch):
    monkeypatch.setattr(probe, "MAX_SPLIT_OBSERVATIONS", 10)
    result = run_small(through="derive")
    assert result["outcome"] == "ok"
    (stage,) = result["stages"]
    assert (stage["stage"], stage["outcome"]) == ("derive", "skipped")
    assert stage["message"] == "above the production split population ceiling"


# --- Size model ----------------------------------------------------------------------------


def test_fit_series_recovers_the_coefficients_and_reports_the_held_out_residual():
    def size(records, sources):
        return 7 * records + 100 * sources + 31

    points = [(10, 1, size(10, 1)), (20, 1, size(20, 1)), (20, 2, size(20, 2))]
    fit = probe.fit_series(*points, (30, 3, size(30, 3)))
    assert (fit.per_record, fit.per_source, fit.fixed, fit.residual) == (7, 100, 31, 0)
    drifted = probe.fit_series(*points, (30, 3, size(30, 3) + 4))
    assert drifted.residual == -4  # predicted minus measured


def test_a_fit_with_phases_is_exact_at_counts_that_are_not_whole_cycles():
    weights = (3, 10, 4)  # the bytes of the three rows of a cycle, deliberately unequal

    def size(records, sources):
        whole, rest = divmod(records, len(weights))
        return sum(weights) * whole + sum(weights[:rest]) + 100 * sources + 31

    points = [(60, 1, size(60, 1)), (120, 1, size(120, 1)), (120, 2, size(120, 2))]
    held_out = (182, 4, size(182, 4))  # ends two rows into a cycle
    fit = probe.fit_series(*points, held_out, (0, weights[0], weights[0] + weights[1]))
    assert fit.residual == 0
    for records in range(1, 40):
        assert fit.predict(records, 2) == size(records, 2)
    # An average row size is wrong at counts that end part-way through a cycle.
    assert probe.fit_series(*points, held_out).residual != 0


@pytest.mark.parametrize(
    ("points", "phases"),
    [
        ([(10, 1, 5), (20, 1, 9), (20, 2, 12)], (0, 1, 2)),  # the first run is not a whole cycle
        ([(12, 1, 5), (24, 1, 9), (24, 2, 12)], (1, 2, 3)),  # the first phase is not zero
        ([(12, 1, 5), (24, 1, 9), (24, 2, 12)], ()),  # no phases at all
    ],
)
def test_phases_that_do_not_match_the_runs_are_rejected(points, phases):
    with pytest.raises(ValueError):
        probe.fit_series(*points, (36, 3, 20), phases)


@pytest.mark.parametrize(
    "points",
    [
        [(10, 1, 5), (20, 2, 9), (20, 3, 12)],  # the first two runs differ in sources
        [(10, 1, 5), (20, 1, 9), (30, 2, 12)],  # the last two runs differ in records
        [(10, 1, 5), (10, 1, 5), (10, 2, 9)],  # no record difference
        [(10, 1, 5), (20, 1, 9), (20, 1, 9)],  # no source difference
    ],
)
def test_runs_that_do_not_identify_the_model_are_rejected(points):
    with pytest.raises(ValueError):
        probe.fit_series(*points, (30, 3, 20))


@pytest.mark.parametrize(
    "fit",
    [
        probe.Fit(Fraction(193), Fraction(0), Fraction(733), Fraction(0)),
        probe.Fit(Fraction(161083, 1000), Fraction(297), Fraction(1973), Fraction(0)),
        probe.Fit(Fraction(1, 15), Fraction(488), Fraction(2475), Fraction(0)),
    ],
)
@pytest.mark.parametrize("rows_per_source", [1, 7, 600])
def test_the_largest_population_is_the_exact_boundary_of_the_predicted_size(fit, rows_per_source):
    limit = MAX_DOCUMENT_BYTES

    def size(records):
        return fit.predict(records, -(-records // rows_per_source))

    largest = probe.largest_population(fit, rows_per_source, limit)
    assert size(largest) <= limit < size(largest + 1)


@pytest.mark.parametrize(
    ("limit", "expected"),
    # 80 and 160 hit the limit exactly at 8 and 16, the points where the search doubles.
    [(99, 9), (100, 10), (101, 10), (109, 10), (79, 7), (80, 8), (160, 16)],
)
def test_a_size_equal_to_the_limit_is_admitted(limit, expected):
    exact = probe.Fit(Fraction(10), Fraction(0), Fraction(0), Fraction(0))
    assert probe.largest_population(exact, 1, limit) == expected


def test_the_largest_population_handles_the_degenerate_models():
    flat = probe.Fit(Fraction(0), Fraction(0), Fraction(10), Fraction(0))
    assert probe.largest_population(flat, 600, 100) is None
    already_over = probe.Fit(Fraction(5), Fraction(0), Fraction(500), Fraction(0))
    assert probe.largest_population(already_over, 600, 100) == 0
    for shrinking in (
        probe.Fit(Fraction(-1), Fraction(1), Fraction(0), Fraction(0)),
        probe.Fit(Fraction(1), Fraction(-1), Fraction(0), Fraction(0)),
    ):
        with pytest.raises(ValueError):
            probe.largest_population(shrinking, 600, 100)


def test_fitted_sizes_predict_the_held_out_production_run():
    for length, mix, record_length in (
        (16, "typical", 14),
        (128, "training", 14),
        (16, "typical", 128),
    ):
        fits = probe.fit_runs(length, mix, 12, record_length)
        assert set(fits) == {gate.series for gate in probe.GATES}
        # Source bytes and the split are exactly affine. The candidate and release carry
        # decimal counters and sizes whose digits grow, so they may drift by a few bytes.
        assert fits["source_bytes"].residual == 0
        assert fits["split_bytes"].residual == 0
        assert abs(fits["candidate_bytes"].residual) <= 16
        assert abs(fits["release_bytes"].residual) <= 16


def fake_runner(requested, *, phase_sources=None):
    """A production stand-in whose sizes follow a known, phase-free model exactly."""

    def run(count, id_length, mix, *, per_source, record_id_length, through):
        requested.append((count, per_source, through))
        sources = -(-count // per_source)
        if phase_sources is not None and per_source == 18:
            sources = phase_sources
        size = 100 * count + 10 * sources + 7
        series = ("source_bytes", "candidate_bytes", "release_bytes", "split_bytes")
        return {
            "outcome": "ok",
            "parameters": {"records": count},
            "sizes": {"source_documents": sources, **{name: size for name in series}},
        }

    return run


@pytest.mark.parametrize(
    ("mix", "layout"),
    [
        # Three runs identify the model; the fourth ends part-way through a cycle and is held out.
        # Each further observation of the cycle adds one run in a single envelope.
        (
            "typical",
            [
                (12, 12),
                (24, 24),
                (24, 12),
                (41, 12),
                (13, 18),
                (14, 18),
                (15, 18),
                (16, 18),
                (17, 18),
            ],
        ),
        ("balanced", [(12, 12), (24, 24), (24, 12), (37, 12), (13, 14)]),
        ("training", [(12, 12), (24, 24), (24, 12), (36, 12)]),
    ],
)
def test_the_fit_requests_the_documented_runs(monkeypatch, mix, layout):
    requested = []
    monkeypatch.setattr(probe, "run_stages", fake_runner(requested))
    fits = probe.fit_runs(16, mix, 12)
    assert requested == [(count, rows, "split") for count, rows in layout]
    assert all(fit.residual == 0 for fit in fits.values())  # the stand-in follows the model
    assert {len(fit.phases) for fit in fits.values()} == {len(probe.MIXES[mix])}


def test_phase_runs_in_a_different_number_of_envelopes_are_a_tool_error(monkeypatch):
    monkeypatch.setattr(probe, "run_stages", fake_runner([], phase_sources=2))
    with pytest.raises(RuntimeError, match="same number of source envelopes"):
        probe.fit_runs(16, "typical", 12)


def check_model_at(fits, count, mix):
    sizes = run_small(count, 16, mix, through="split")["sizes"]
    sources = sizes["source_documents"]
    # The source bytes and the split are exact. The candidate and release carry decimal
    # counters, so they may drift by a few bytes.
    assert fits["source_bytes"].predict(count, sources) == sizes["source_bytes"]
    assert fits["split_bytes"].predict(count, sources) == sizes["split_bytes"]
    assert abs(fits["candidate_bytes"].predict(count, sources) - sizes["candidate_bytes"]) <= 16
    assert abs(fits["release_bytes"].predict(count, sources) - sizes["release_bytes"]) <= 16


@pytest.mark.parametrize("count", [14, 17, 25])
def test_the_model_is_exact_at_counts_that_are_not_whole_cycles(typical_fit, count):
    check_model_at(typical_fit, count, "typical")


def test_the_model_is_exact_at_odd_counts_of_a_two_row_cycle():
    check_model_at(probe.fit_runs(16, "balanced", 12), 13, "balanced")


@pytest.mark.parametrize(("length", "record_length"), [(16, 14), (64, 128)])
def test_fitted_slopes_equal_the_independently_computed_entry_sizes(length, record_length):
    fits = probe.fit_runs(length, "training", 12, record_length)
    population = probe.build_population(6, length, "training", record_id_length=record_length)
    row = population.rows[3]
    record = {"source_record_id": "r" * record_length, "observation": row}
    # Each source record adds its JSON and one comma. The slope is exact for identical rows.
    assert fits["source_bytes"].per_record == len(canonical_json(record).encode("utf-8")) + 1
    # The candidate holds one lineage entry per observation and nothing else that grows with
    # the population. The quality report's decimal counters add a fraction of a byte.
    entry = {
        "observation_id": row["observation_id"],
        "source_ref": "sha256:" + "0" * 64,
        "source_record_id": "r" * record_length,
    }
    entry_bytes = len(canonical_json(entry).encode("utf-8")) + 1
    assert entry_bytes == length + record_length + 131
    assert abs(fits["candidate_bytes"].per_record - entry_bytes) < 1


def test_the_fitted_split_capacity_equals_the_documented_closed_form():
    def closed_form(length):
        """The fixed split fields plus identical one-reason excluded rows, from the design."""
        row = {
            "observation_id": "x" * length,
            "partition": "excluded",
            "eligibility_exclusions": ["temporal_evidence_missing"],
            "cohorts": [],
            "unseen_property_exclusions": ["not_development_validation"],
        }
        empty = {
            "contract_version": "1.0.0",
            "access_domain": "development",
            "dataset_ref": "sha256:" + "0" * 64,
            "observations_digest": "sha256:" + "0" * 64,
            "policy_ref": "sha256:" + "0" * 64,
            "training_cutoff": probe.TRAINING_CUTOFF,
            "validation_window": probe.VALIDATION_WINDOW,
            "memberships": [],
            "creation_provenance": {
                "source_snapshot_ref": "sha256:" + "0" * 64,
                "created_at": "2026-03-03T12:00:00Z",
            },
            "split_digest": "sha256:" + "0" * 64,
        }
        fixed = len(canonical_json(empty).encode("utf-8"))
        return (MAX_DOCUMENT_BYTES - fixed + 1) // (len(canonical_json(row).encode("utf-8")) + 1)

    lengths = (16, 32, 64, 128)
    fitted = [
        probe.capacity_report(length, "excluded", fit_unit=12)["gates"]["split document"]
        for length in lengths
    ]
    assert fitted == [closed_form(length) for length in lengths]
    assert fitted == [5_544, 5_111, 4_421, 3_481]  # the figures the design documents


def test_the_default_fit_unit_is_one_the_command_line_accepts():
    # A default that the option's own validation rejected would make the plain command fail.
    assert probe._fit_unit(str(probe.DEFAULT_FIT_UNIT)) == probe.DEFAULT_FIT_UNIT
    assert probe.DEFAULT_FIT_UNIT % probe.MIX_PERIOD == 0
    assert probe.DEFAULT_FIT_UNIT <= probe.MAX_FIT_UNIT


def test_fit_populations_must_align_with_the_row_size_period():
    assert probe.MIX_PERIOD == 6  # the least common multiple of every mix cycle
    for unit in (0, -6, 7, 9):
        with pytest.raises(ValueError):
            probe.fit_runs(16, "typical", unit)
    with pytest.raises(ValueError):
        probe.capacity_report(16, "typical", per_source=0)


def test_a_gate_that_admits_no_records_is_reported_without_dividing_by_zero(monkeypatch):
    monkeypatch.setattr(probe, "largest_population", lambda *arguments: 0)
    report = probe.capacity_report(16, "training", fit_unit=6, confirm=True)
    assert report["capacity"] == 0
    assert report["headroom_percent"] is None
    assert report["confirmation"] == {
        "gate": report["first_limit"],
        "confirmed": None,
        "note": "no population fits",
    }


@pytest.mark.parametrize(
    ("candidate_limit", "tied", "next_limit", "next_capacity", "headroom"),
    [
        (1_010, ["candidate document"], "candidate document", 101, 1.0),  # one row beyond the first
        (1_500, [], "candidate document", 150, 50.0),  # clear of the first
    ],
)
def test_the_report_names_the_first_limit_ties_and_headroom_from_hand_computed_fits(
    monkeypatch, candidate_limit, tied, next_limit, next_capacity, headroom
):
    def linear(slope):
        return probe.Fit(Fraction(slope), Fraction(0), Fraction(0), Fraction(0))

    fits = {
        "source_bytes": linear(10),
        "candidate_bytes": linear(10),
        "release_bytes": linear(1),
        "split_bytes": linear(5),
    }
    monkeypatch.setattr(probe, "fit_runs", lambda *arguments: fits)
    limits = (1_000, candidate_limit, 5_000, 800)  # in the order of the gate table
    monkeypatch.setattr(
        probe,
        "GATES",
        tuple(dataclasses.replace(gate, limit=cap) for gate, cap in zip(probe.GATES, limits)),
    )
    report = probe.capacity_report(16, "typical")
    # By hand: 1,000 / 10 = 100, candidate_limit / 10, 5,000 / 1 = 5,000 and 800 / 5 = 160.
    assert report["gates"] == {
        "source bytes": 100,
        "candidate document": candidate_limit // 10,
        "release document": 5_000,
        "split document": 160,
        probe.INVENTORY_RECORDS: MAX_INVENTORY_RECORDS,
    }
    assert (report["first_limit"], report["capacity"]) == ("source bytes", 100)
    assert report["tied_limits"] == tied
    assert (report["next_limit"], report["next_capacity"]) == (next_limit, next_capacity)
    assert report["headroom_percent"] == headroom
    assert report["confirmation"] is None


# --- Boundary confirmation -----------------------------------------------------------------


def threshold_runner(threshold, calls):
    def passes(count):
        calls.append(count)
        return {"outcome": "ok" if count <= threshold else "failed", "count": count}

    return passes


@pytest.mark.parametrize(("predicted", "threshold"), [(50, 50), (50, 53), (50, 47), (50, 40)])
def test_find_boundary_returns_the_largest_passing_count_and_the_failure_beyond_it(
    predicted, threshold
):
    calls = []
    runner = threshold_runner(threshold, calls)
    observed, failure = probe.find_boundary(runner, predicted, window=16)
    assert observed == threshold
    assert failure == {"outcome": "failed", "count": threshold + 1}
    assert len(calls) <= abs(predicted - threshold) + 2  # a good prediction costs two runs


@pytest.mark.parametrize(("threshold", "found"), [(54, True), (55, False), (46, True), (45, False)])
def test_the_default_window_bounds_the_number_of_production_runs(threshold, found):
    calls = []
    boundary = probe.find_boundary(threshold_runner(threshold, calls), 50)
    assert (boundary is not None) is found
    # The window must reach a boundary that is one row of tolerance away, and bounds the cost.
    assert probe.SEARCH_WINDOW > probe.TIE_ROWS
    assert len(calls) <= probe.SEARCH_WINDOW + 2


@pytest.mark.parametrize("threshold", [10, 100])
def test_find_boundary_gives_up_outside_its_window(threshold):
    assert probe.find_boundary(threshold_runner(threshold, []), 50, window=5) is None


def test_confirmation_checks_the_production_boundary_of_the_first_limit(monkeypatch):
    # Shrink the source gate so the first limit is reachable with a tiny population, then
    # let the real production code decide where it fails.
    limit = 30_000
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", limit)
    monkeypatch.setattr(
        probe, "GATES", (dataclasses.replace(probe.GATES[0], limit=limit), *probe.GATES[1:])
    )
    report = probe.capacity_report(16, "training", per_source=12, fit_unit=12, confirm=True)
    check = report["confirmation"]
    assert report["first_limit"] == "source bytes"
    assert 12 < report["capacity"] < 100
    assert check == {
        "gate": "source bytes",
        "predicted": report["capacity"],
        "observed": report["capacity"],
        "tolerance_rows": 0,
        "failed_stage": "candidate",
        "message": "source inventory size limit exceeded",
        "confirmed": True,
    }


@pytest.mark.parametrize("step", [0, 1, 2, 3, 4, 5])
def test_confirmation_matches_production_for_a_mix_with_unequal_rows(
    monkeypatch, typical_fit, step
):
    # Each step moves the boundary by about one row, through every phase of the six-row cycle.
    # The rows of the typical mix differ in size, so an average row size would be a row off.
    limit = 30_000 + 692 * step
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", limit)
    monkeypatch.setattr(
        probe, "GATES", (dataclasses.replace(probe.GATES[0], limit=limit), *probe.GATES[1:])
    )
    monkeypatch.setattr(probe, "fit_runs", lambda *arguments: typical_fit)
    report = probe.capacity_report(16, "typical", per_source=12, fit_unit=12, confirm=True)
    assert report["first_limit"] == "source bytes"
    assert report["confirmation"]["observed"] == report["capacity"]
    assert report["confirmation"]["confirmed"] is True


def test_confirmation_reports_progress_before_every_production_run(monkeypatch):
    limit = 30_000
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", limit)
    monkeypatch.setattr(
        probe, "GATES", (dataclasses.replace(probe.GATES[0], limit=limit), *probe.GATES[1:])
    )
    messages = []
    report = probe.capacity_report(
        16, "training", per_source=12, fit_unit=12, confirm=True, progress=messages.append
    )
    assert report["confirmation"]["confirmed"] is True
    assert len(messages) == 2  # the capacity itself, then one record beyond it
    assert messages[0] == (
        f"confirming training, 16-character identifiers: {report['capacity']:,} observations"
    )
    assert messages[1].endswith(f"{report['capacity'] + 1:,} observations")


@pytest.mark.parametrize(
    "mismatch", [{"stage": "release"}, {"message": "document size limit exceeded"}]
)
def test_a_boundary_that_fails_somewhere_else_is_not_confirmed(monkeypatch, mismatch):
    # The boundary is right, but production fails in another stage or with another message than
    # the gate table says. That means the table no longer describes production.
    limit = 30_000
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", limit)
    gate = dataclasses.replace(probe.GATES[0], limit=limit, **mismatch)
    monkeypatch.setattr(probe, "GATES", (gate, *probe.GATES[1:]))
    check = probe.capacity_report(16, "training", per_source=12, fit_unit=12, confirm=True)[
        "confirmation"
    ]
    assert check["observed"] == check["predicted"]
    assert (check["failed_stage"], check["message"]) == (
        "candidate",
        "source inventory size limit exceeded",
    )
    assert check["confirmed"] is False


def stub_boundary(monkeypatch, *, first_exact, tied_exact=None):
    """A report whose first limit may be tied with a second, and a controllable production."""
    first = dataclasses.replace(
        probe.GATES[1], name="first", stage="candidate", message="m1", exact=first_exact
    )
    far = dataclasses.replace(probe.GATES[2], name="far", stage="release", message="m3", exact=True)
    gates, tied = [first, far], []
    if tied_exact is not None:
        gates.append(
            dataclasses.replace(
                probe.GATES[3], name="tied", stage="split", message="m2", exact=tied_exact
            )
        )
        tied = ["tied"]
    monkeypatch.setattr(probe, "GATES", tuple(gates))
    report = {"first_limit": "first", "tied_limits": tied, "capacity": 100, "record_id_length": 14}

    def confirm(stage, message, observed=100):
        failure = {"failed_stage": stage, "message": message}
        monkeypatch.setattr(probe, "find_boundary", lambda *arguments: (observed, failure))
        return probe.confirm_boundary(report, 16, "training", 600)

    return confirm


def test_a_failure_from_a_limit_tied_with_the_first_is_accepted(monkeypatch):
    confirm = stub_boundary(monkeypatch, first_exact=True, tied_exact=True)
    assert confirm("candidate", "m1")["confirmed"] is True
    assert confirm("split", "m2")["confirmed"] is True  # the tied limit may fail first
    assert confirm("release", "m3")["confirmed"] is False  # a limit that was not near the first
    assert confirm("candidate", "m1", observed=101)["confirmed"] is False  # exact models allow none


@pytest.mark.parametrize(
    ("first_exact", "tied_exact", "observed", "tolerance", "confirmed"),
    [
        (True, None, 100, 0, True),
        (True, None, 101, 0, False),  # an exact model must match
        (False, None, 99, 1, True),  # a model with decimal counters may be a row off
        (False, None, 101, 1, True),
        (False, None, 102, 1, False),
        (True, False, 101, 1, True),  # an uncertain limit tied with an exact one
        (True, True, 101, 0, False),
    ],
)
def test_only_a_model_with_uncertain_counters_may_be_a_row_off(
    monkeypatch, first_exact, tied_exact, observed, tolerance, confirmed
):
    confirm = stub_boundary(monkeypatch, first_exact=first_exact, tied_exact=tied_exact)
    check = confirm("candidate", "m1", observed=observed)
    assert check["tolerance_rows"] == tolerance
    assert check["confirmed"] is confirmed


def test_a_boundary_that_cannot_be_found_is_not_confirmed_and_has_no_observation(monkeypatch):
    confirm = stub_boundary(monkeypatch, first_exact=True)
    monkeypatch.setattr(probe, "find_boundary", lambda *arguments: None)
    report = {"first_limit": "first", "tied_limits": [], "capacity": 100, "record_id_length": 14}
    assert probe.confirm_boundary(report, 16, "training", 600) == {
        "gate": "first",
        "predicted": 100,
        "confirmed": False,
    }
    del confirm


def test_a_wrong_prediction_is_detected_and_the_observed_boundary_is_reported(monkeypatch):
    limit = 30_000
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", limit)
    monkeypatch.setattr(
        probe, "GATES", (dataclasses.replace(probe.GATES[0], limit=limit), *probe.GATES[1:])
    )
    exact = probe.largest_population
    # A model that overshoots by one record is exactly what confirmation exists to catch.
    monkeypatch.setattr(
        probe, "largest_population", lambda fit, rows, cap: (exact(fit, rows, cap) or 0) + 1
    )
    report = probe.capacity_report(16, "training", per_source=12, fit_unit=12, confirm=True)
    check = report["confirmation"]
    assert report["first_limit"] == "source bytes"
    assert check["confirmed"] is False
    assert check["predicted"] == report["capacity"]
    assert check["observed"] == report["capacity"] - 1
    assert (check["failed_stage"], check["message"]) == (
        "candidate",
        "source inventory size limit exceeded",
    )


def candidate_first_at(monkeypatch, capacity):
    answers = iter([10**6, capacity, 10**6, 10**6])  # in the order of the gates
    monkeypatch.setattr(probe, "largest_population", lambda *arguments: next(answers))


@pytest.mark.parametrize("margin", [0, 1, probe.SEARCH_WINDOW])
def test_a_capacity_whose_search_would_pass_the_record_limit_is_not_confirmed(monkeypatch, margin):
    # The search tries up to a window and one more record above the prediction, and no stage
    # accepts a population above the record limit, so none is attempted.
    candidate_first_at(monkeypatch, MAX_INVENTORY_RECORDS - margin)
    monkeypatch.setattr(probe, "find_boundary", lambda *arguments: pytest.fail("searched"))
    report = probe.capacity_report(16, "training", fit_unit=6, confirm=True)
    assert report["first_limit"] == "candidate document"
    assert report["confirmation"] == {
        "gate": "candidate document",
        "confirmed": None,
        "note": "at the inventory record limit",
    }


def test_the_last_capacity_that_can_be_searched_never_asks_for_too_many_records(monkeypatch):
    capacity = MAX_INVENTORY_RECORDS - probe.SEARCH_WINDOW - 1  # the last one that is searched
    candidate_first_at(monkeypatch, capacity)
    searched = []

    def search(passes, predicted, window=probe.SEARCH_WINDOW):
        searched.append(predicted + window + 1)  # the highest count the search can try
        failure = {"failed_stage": "candidate", "message": "document size limit exceeded"}
        return predicted, failure

    monkeypatch.setattr(probe, "find_boundary", search)
    report = probe.capacity_report(16, "training", fit_unit=6, confirm=True)
    assert report["confirmation"]["confirmed"] is True
    assert searched == [MAX_INVENTORY_RECORDS]  # the search just reaches the limit


def test_the_envelope_guard_matches_the_production_document_limit_exactly(monkeypatch):
    fits = probe.fit_runs(16, "training", 12)
    source = fits["source_bytes"]
    largest = int((MAX_DOCUMENT_BYTES - source.per_source) // source.per_record)
    monkeypatch.setattr(probe, "fit_runs", lambda *arguments: fits)
    # Production accepts an envelope of the largest size and rejects one record more...
    probe.build_population(largest, 16, "training", per_source=largest)
    with pytest.raises(ContractError, match="document size limit exceeded"):
        probe.build_population(largest + 1, 16, "training", per_source=largest + 1)
    # ...and the guard draws the same line.
    probe.capacity_report(16, "training", per_source=largest, fit_unit=12)
    with pytest.raises(ValueError, match="records per source exceed the document limit"):
        probe.capacity_report(16, "training", per_source=largest + 1, fit_unit=12)


def test_an_envelope_that_exactly_fills_the_document_limit_is_accepted(monkeypatch):
    # With 8 bytes per record and no header, 131,072 records fill the 1 MiB limit to the byte.
    def linear(slope):
        return probe.Fit(Fraction(slope), Fraction(0), Fraction(0), Fraction(0))

    fits = {
        "source_bytes": linear(8),
        "candidate_bytes": linear(1),
        "release_bytes": linear(1),
        "split_bytes": linear(1),
    }
    monkeypatch.setattr(probe, "fit_runs", lambda *arguments: fits)
    assert 8 * 131_072 == MAX_DOCUMENT_BYTES
    probe.capacity_report(16, "typical", per_source=131_072)
    with pytest.raises(ValueError, match="records per source exceed the document limit"):
        probe.capacity_report(16, "typical", per_source=131_073)


def test_a_source_envelope_above_the_document_limit_is_rejected_before_any_prediction():
    with pytest.raises(ValueError, match="records per source exceed the document limit"):
        probe.capacity_report(16, "training", per_source=5_000, fit_unit=12)


def test_a_first_limit_that_is_not_a_size_gate_is_reported_but_not_confirmed(monkeypatch):
    # With every size gate far above the inventory record limit, that limit binds first. It is a
    # declared count rather than a size, so there is nothing to confirm against production.
    monkeypatch.setattr(
        probe,
        "GATES",
        tuple(dataclasses.replace(gate, limit=gate.limit * 1_000) for gate in probe.GATES),
    )
    report = probe.capacity_report(16, "training", fit_unit=6, confirm=True)
    assert report["first_limit"] == probe.INVENTORY_RECORDS
    assert report["capacity"] == MAX_INVENTORY_RECORDS
    assert report["confirmation"] == {
        "gate": probe.INVENTORY_RECORDS,
        "confirmed": None,
        "note": "not a size gate",
    }


# --- Command line --------------------------------------------------------------------------


def run_cli(capsys, *arguments):
    status = probe.main(list(arguments))
    return status, capsys.readouterr()


def test_stages_prints_json_with_the_environment_and_exits_zero(capsys):
    status, output = run_cli(
        capsys, "stages", "--records", "24", "--id-length", "16", "--per-source", "12"
    )
    document = json.loads(output.out)
    assert status == 0
    assert document["outcome"] == "ok"
    assert set(document["environment"]) == {"python", "system", "machine", "pyarrow", "cpu_count"}
    assert document["parameters"] == {
        "records": 24,
        "id_length": 16,
        "mix": "typical",
        "per_source": 12,
        "record_id_length": 14,
        "through": "readback",
    }
    assert [stage["stage"] for stage in document["stages"]] == list(probe.STAGES)


def test_stages_markdown_names_the_stages_and_sizes(capsys):
    status, output = run_cli(
        capsys, "stages", "--records", "24", "--per-source", "12", "--format", "markdown"
    )
    assert status == 0
    assert output.out.startswith("Environment: CPython ")
    assert "| Stage | Outcome | Seconds | Peak RSS (MiB) |" in output.out
    assert "| readback | ok |" in output.out
    assert "Bytes: source " in output.out


def test_a_failing_production_gate_is_a_finding_not_a_tool_error(capsys, monkeypatch):
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", 1_000)
    status, output = run_cli(capsys, "stages", "--records", "24", "--per-source", "12")
    document = json.loads(output.out)
    assert status == 0
    assert (document["outcome"], document["failed_stage"]) == ("failed", "candidate")
    assert document["message"] == "source inventory size limit exceeded"
    _, markdown = run_cli(
        capsys, "stages", "--records", "24", "--per-source", "12", "--format", "markdown"
    )
    assert "| candidate | failed: source inventory size limit exceeded |" in markdown.out


def test_capacity_prints_json_and_a_markdown_table(capsys):
    status, output = run_cli(
        capsys, "capacity", "--id-lengths", "16", "--mixes", "training", "--fit-unit", "6"
    )
    document = json.loads(output.out)
    (report,) = document["reports"]
    assert status == 0
    assert document["basis"] == probe.CAPACITY_BASIS
    assert (report["mix"], report["id_length"], report["fit_unit"]) == ("training", 16, 6)
    assert report["record_id_length"] == 14
    status, output = run_cli(
        capsys,
        "capacity",
        "--id-lengths",
        "16",
        "--mixes",
        "training",
        "--fit-unit",
        "6",
        "--record-id-length",
        "128",
    )
    (report,) = json.loads(output.out)["reports"]
    assert report["record_id_length"] == 128
    # Longer record identifiers make every lineage entry larger, so the candidate admits fewer.
    assert report["gates"]["candidate document"] < 4_000
    status, output = run_cli(
        capsys,
        "capacity",
        "--id-lengths",
        "16,32",
        "--mixes",
        "training",
        "--fit-unit",
        "6",
        "--format",
        "markdown",
    )
    lines = output.out.splitlines()
    rows = [line for line in lines if line.startswith("| training |")]
    assert status == 0
    assert lines[2].startswith("| Mix | ID chars |")
    assert [row.split("|")[1:3] for row in rows] == [[" training ", " 16 "], [" training ", " 32 "]]
    assert all(row.endswith("| not run |") for row in rows)
    assert lines[-2] == (
        "A slash joins limits within 1 row of each other. "
        "Limits are predicted by a size model fitted to small production runs; "
        "only a confirmation is a production measurement."
    )
    assert lines[-1] == (
        "Fit units below 198 run faster but can leave the candidate and release predictions "
        "several rows off."
    )


def test_confirmation_progress_goes_to_standard_error_and_the_report_stays_clean(
    capsys, monkeypatch
):
    limit = 30_000
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", limit)
    monkeypatch.setattr(
        probe, "GATES", (dataclasses.replace(probe.GATES[0], limit=limit), *probe.GATES[1:])
    )
    status, output = run_cli(
        capsys,
        "capacity",
        "--id-lengths",
        "16",
        "--mixes",
        "training",
        "--fit-unit",
        "12",
        "--per-source",
        "12",
        "--confirm",
    )
    (report,) = json.loads(output.out)["reports"]
    assert status == 0
    assert report["confirmation"]["confirmed"] is True
    lines = output.err.splitlines()
    assert len(lines) == 2
    assert all(line.startswith("confirming training, 16-character identifiers: ") for line in lines)


def test_a_source_envelope_above_the_document_limit_is_a_tool_error(capsys):
    status, output = run_cli(
        capsys,
        "capacity",
        "--id-lengths",
        "16",
        "--mixes",
        "training",
        "--fit-unit",
        "6",
        "--per-source",
        "5000",
    )
    assert status == 1
    assert output.out == ""
    assert output.err == (
        "error: records per source exceed the document limit at this identifier length\n"
    )


def capacity_report_for(**changes):
    gates = {"source bytes": 5_863, "candidate document": 6_477, "split document": 5_886}
    report = {
        "mix": "training",
        "id_length": 16,
        "record_id_length": 14,
        "fit_unit": probe.DEFAULT_FIT_UNIT,
        "gates": gates,
        "first_limit": "source bytes",
        "tied_limits": [],
        "capacity": 5_863,
        "next_limit": "split document",
        "headroom_percent": 0.4,
        "confirmation": None,
    }
    return {**report, **changes}


def test_the_markdown_flags_fit_units_below_the_default_and_only_those():
    default = probe.format_capacity([capacity_report_for()])
    assert "Fit units below" not in default
    small = probe.format_capacity([capacity_report_for(), capacity_report_for(fit_unit=12)])
    assert small.splitlines()[-1].startswith(f"Fit units below {probe.DEFAULT_FIT_UNIT} run faster")


@pytest.mark.parametrize(
    ("changes", "boundary", "limit", "headroom"),
    [
        ({}, "not run", "source bytes (5,863)", "+0.4% (split document)"),
        (
            {"confirmation": {"confirmed": True, "observed": 5_863}},
            "confirmed at 5,863",
            "source bytes (5,863)",
            "+0.4% (split document)",
        ),
        (
            {"confirmation": {"confirmed": False, "observed": 5_864}},
            "observed 5,864",
            "source bytes (5,863)",
            "+0.4% (split document)",
        ),
        (
            {
                "confirmation": {"confirmed": False}
            },  # the boundary was not found near the prediction
            "observed none",
            "source bytes (5,863)",
            "+0.4% (split document)",
        ),
        (
            {"confirmation": {"confirmed": None, "note": "not a size gate"}},
            "not applicable",
            "source bytes (5,863)",
            "+0.4% (split document)",
        ),
        (
            {"tied_limits": ["split document"], "headroom_percent": None},
            "not run",
            "source bytes / split document (5,863)",
            "none",
        ),
    ],
)
def test_the_markdown_row_shows_the_limit_ties_headroom_and_confirmation(
    changes, boundary, limit, headroom
):
    table = probe.format_capacity([capacity_report_for(**changes)])
    row = [line for line in table.splitlines() if line.startswith("| training |")]
    assert row == [
        f"| training | 16 | 14 | 5,863 | 6,477 | 5,886 | {limit} | {headroom} | {boundary} |"
    ]


def test_an_unconfirmed_boundary_exits_nonzero(capsys, monkeypatch):
    monkeypatch.setattr(probe, "find_boundary", lambda *args, **kwargs: None)
    status, output = run_cli(
        capsys,
        "capacity",
        "--id-lengths",
        "16",
        "--mixes",
        "training",
        "--fit-unit",
        "6",
        "--confirm",
    )
    (report,) = json.loads(output.out)["reports"]
    assert status == 1
    assert report["confirmation"]["confirmed"] is False


def test_a_failed_fit_run_is_a_tool_error(capsys, monkeypatch):
    monkeypatch.setattr("rent_data.candidates.MAX_REFERENCE_SOURCE_BYTES", 1_000)
    status, output = run_cli(
        capsys, "capacity", "--id-lengths", "16", "--mixes", "training", "--fit-unit", "6"
    )
    assert status == 1
    assert output.out == ""
    assert output.err == (
        "error: a small fit run failed at candidate: source inventory size limit exceeded\n"
    )


def test_a_model_that_does_not_grow_is_a_tool_error(capsys, monkeypatch):
    def shrinking(*arguments):
        raise ValueError("size model does not grow with the population")

    monkeypatch.setattr(probe, "largest_population", shrinking)
    status, output = run_cli(
        capsys, "capacity", "--id-lengths", "16", "--mixes", "training", "--fit-unit", "6"
    )
    assert status == 1
    assert output.out == ""
    assert output.err == "error: size model does not grow with the population\n"


@pytest.mark.parametrize(
    "arguments",
    [
        ("stages",),
        ("stages", "--records", "0"),
        ("stages", "--records", str(MAX_INVENTORY_RECORDS + 1)),
        ("stages", "--records", "many"),
        ("stages", "--records", "12", "--id-length", str(probe.MIN_ID_LENGTH - 1)),
        ("stages", "--records", "12", "--id-length", str(probe.MAX_ID_LENGTH + 1)),
        ("stages", "--records", "12", "--mix", "unknown"),
        ("stages", "--records", "12", "--through", "unknown"),
        ("stages", "--records", "12", "--per-source", "0"),
        ("stages", "--records", "12", "--record-id-length", "13"),
        ("capacity", "--record-id-length", "129"),
        ("capacity", "--fit-unit", "7"),
        ("capacity", "--fit-unit", "0"),
        ("capacity", "--fit-unit", str(probe.MAX_FIT_UNIT + probe.MIX_PERIOD)),
        ("capacity", "--fit-unit", str(MAX_INVENTORY_RECORDS)),
        ("capacity", "--id-lengths", "16,300"),
        ("capacity", "--mixes", "typical,unknown"),
        ("capacity", "--format", "xml"),
        (),
    ],
)
def test_malformed_arguments_exit_with_status_two_before_any_work(arguments, capsys):
    with pytest.raises(SystemExit) as exit_status:
        probe.main(list(arguments))
    assert exit_status.value.code == 2
    assert capsys.readouterr().out == ""


# --- Determinism across interpreters -------------------------------------------------------


def test_sizes_and_sealed_identities_do_not_depend_on_the_hash_seed():
    results = []
    for seed in ("1", "97", "4242"):
        completed = subprocess.run(
            [
                sys.executable,
                "-P",
                str(SCRIPT),
                "stages",
                "--records",
                "48",
                "--id-length",
                "16",
                "--per-source",
                "24",
            ],
            env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=True,
        )
        document = json.loads(completed.stdout)
        assert document["outcome"] == "ok"
        results.append((document["sizes"], document["identities"]))
    assert results[0] == results[1] == results[2]
    assert set(results[0][1]) == {"release_digest", "split_digest"}


def test_capacity_reports_do_not_depend_on_the_hash_seed():
    reports = []
    for seed in ("1", "4242"):
        completed = subprocess.run(
            [
                sys.executable,
                "-P",
                str(SCRIPT),
                "capacity",
                "--id-lengths",
                "16",
                "--mixes",
                "typical",
                "--fit-unit",
                "6",
            ],
            env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=True,
        )
        reports.append(json.loads(completed.stdout)["reports"])
    assert reports[0] == reports[1]
