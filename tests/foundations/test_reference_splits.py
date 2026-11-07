"""Reference-backed (v2) development splits: parity with v1, bounds and failure handling.

Synthetic metadata only: no clock, private row, DVC claim or real chronology. Actual
Git/DVC restoration of these releases is exercised by tests/integration.
"""

import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from itertools import chain, combinations
from pathlib import Path

import pytest

from rent_contracts import ContractError, load_document
from rent_contracts.evaluation import (
    ObservationInventoryHasher,
    derive_development_memberships,
    development_split_digest,
    observation_inventory_digest,
    validate_development_population,
    validate_development_split,
)
from rent_contracts.inventory import MANIFEST_FILE, PARQUET_FILE
from rent_contracts.validation import MAX_DOCUMENT_BYTES, DocumentSizeError, canonical_json
from rent_data import release_io, splits
from rent_data.candidates import build_observation_candidate
from rent_data.inventory_io import write_observation_inventory
from rent_data.release_io import (
    COMPLETION_FILE,
    finalize_restoration,
    read_verified_restore,
    read_verified_restore_observations,
    write_payload,
)
from rent_data.releases import (
    DVC_VERSION,
    ReleaseError,
    build_dataset_release,
    build_restoration_report,
    content_digest,
    restoration_report_digest,
)
from rent_data.split_io import (
    SPLIT_FILE,
    materialize_development_split,
    read_verified_development_split,
)
from rent_data.splits import (
    MAX_SPLIT_OBSERVATIONS,
    build_development_split,
    validate_release_split,
)

OUTPUT_LIMIT = "development split output size limit exceeded"
FUTURE = ("future_market",)
BOTH = ("future_market", "unseen_property")
FOUR_REASONS = (
    "invalid_non_target_domain",
    "outside_development_windows",
    "temporal_evidence_missing",
    "temporal_order_invalid",
)


def canonical_bytes(document):
    return canonical_json(document).encode("utf-8")


def membership(
    key, partition, *, exclusions=(), cohorts=(), unseen=("not_development_validation",)
):
    # Expected assignments are handwritten from the v1 rules, never generated.
    return {
        "observation_id": key,
        "partition": partition,
        "eligibility_exclusions": list(exclusions),
        "cohorts": list(cohorts),
        "unseen_property_exclusions": list(unseen),
    }


HANDWRITTEN = [
    membership("obs-end", "excluded", exclusions=("outside_development_windows",)),
    membership("obs-gap", "excluded", exclusions=("outside_development_windows",)),
    membership("obs-invalid", "excluded", exclusions=("invalid_non_target_domain",)),
    membership("obs-multi", "excluded", exclusions=FOUR_REASONS),
    membership("obs-new", "development_validation", cohorts=BOTH, unseen=()),
    membership("obs-notime", "excluded", exclusions=("temporal_evidence_missing",)),
    membership("obs-pending", "excluded", exclusions=("unresolved_non_target_domain",)),
    membership(
        "obs-probable",
        "development_validation",
        cohorts=FUTURE,
        unseen=("property_identity_unconfirmed",),
    ),
    membership(
        "obs-refresh",
        "development_validation",
        cohorts=FUTURE,
        unseen=("listing_seen_in_training", "property_overlap_training"),
    ),
    membership(
        "obs-seen",
        "development_validation",
        cohorts=FUTURE,
        unseen=("property_overlap_training",),
    ),
    membership("obs-train-a", "training"),
    membership("obs-train-b", "training"),
    membership(
        "obs-unresolved",
        "development_validation",
        cohorts=FUTURE,
        unseen=("property_identity_unconfirmed",),
    ),
]
BOUNDARY_INSTANTS = (
    "2026-01-19T23:59:59.999999Z",  # strictly before the training cutoff
    "2026-01-20T00:00:00Z",  # the cutoff itself falls in the declared gap
    "2026-02-01T00:00:00Z",  # window start is inclusive
    "2026-02-01T02:00:00+02:00",  # the same instant with an offset
    "2026-03-01T00:00:00Z",  # window end is exclusive
)
BOUNDARY = [
    membership("boundary-0", "training"),
    membership("boundary-1", "excluded", exclusions=("outside_development_windows",)),
    membership("boundary-2", "development_validation", cohorts=BOTH, unseen=()),
    membership("boundary-3", "development_validation", cohorts=BOTH, unseen=()),
    membership("boundary-4", "excluded", exclusions=("outside_development_windows",)),
]


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): content_digest(path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }


def envelope(rows, label):
    source = {
        "contract_version": "1.0.0",
        "raw_source_ref": content_digest(f"synthetic boundary source {label}".encode()),
        "acquisition_provenance_ref": None,
        "acquisition_period": {"start": None, "end": None},
        "records": [
            {"source_record_id": f"capture-{index}", "observation": row}
            for index, row in enumerate(rows)
        ],
    }
    return canonical_bytes(source)


def binding_for(artifacts):
    return {
        "metadata": {
            "commit": "e" * 40,
            "path": "payload.dvc",
            "digest": content_digest(b"synthetic metadata fixture"),
        },
        "dvc": {
            "version": DVC_VERSION,
            "hash_algorithm": "md5",
            "object_id": "b" * 32 + ".dir",
            "size_bytes": sum(row["size_bytes"] for row in artifacts),
            "file_count": len(artifacts),
            "tool_profile_ref": content_digest(b"synthetic tool profile"),
        },
    }


def finish(population, restored, candidate, release):
    finalize_restoration(
        restored,
        build_restoration_report(release),
        manifest=release,
        expected_release_ref=release["release_digest"],
    )
    return {**population, "restored": restored, "candidate": candidate, "release": release}


def stage_v1(directory, population):
    restored = directory / "restored-v1"
    restored.mkdir()
    candidate = build_observation_candidate(population["sources"], **population["recipe"])
    artifacts = write_payload(
        restored / "payload",
        candidate,
        source_documents=population["sources"],
        expected_candidate_ref=candidate["candidate_digest"],
    )
    release = build_dataset_release(
        candidate,
        source_documents=population["sources"],
        binding=binding_for(artifacts),
        artifacts=artifacts,
    )
    return finish(population, restored, candidate, release)


def stage_v2(directory, population):
    inventory = directory / "inventory"
    write_observation_inventory(inventory, population["rows"])
    candidate = build_observation_candidate(
        population["sources"], **population["recipe"], inventory_directory=inventory
    )
    restored = directory / "restored-v2"
    restored.mkdir()
    artifacts = write_payload(
        restored / "payload",
        candidate,
        source_documents=population["sources"],
        expected_candidate_ref=candidate["candidate_digest"],
        inventory_directory=inventory,
    )
    release = build_dataset_release(
        candidate,
        source_documents=population["sources"],
        inventory_directory=restored / "payload" / "inventory",
        binding=binding_for(artifacts),
        artifacts=artifacts,
    )
    return finish(population, restored, candidate, release)


def materialize(case, destination, **overrides):
    return materialize_development_split(
        **(
            {
                "restored_directory": case["restored"],
                "destination": destination,
                "release": case["release"],
                "policy": case["policy"],
                "expected_release_ref": case["release"]["release_digest"],
                "expected_policy_ref": case["policy"]["policy_digest"],
                **case["parameters"],
            }
            | overrides
        )
    )


def read(case, destination, split_ref, **overrides):
    return read_verified_development_split(
        **(
            {
                "destination": destination,
                "restored_directory": case["restored"],
                "release": case["release"],
                "policy": case["policy"],
                "expected_release_ref": case["release"]["release_digest"],
                "expected_policy_ref": case["policy"]["policy_digest"],
                "expected_split_ref": split_ref,
            }
            | overrides
        )
    )


def build(case, **overrides):
    return build_development_split(
        **(
            {
                "release": case["release"],
                "observations": case["rows"],
                "policy": case["policy"],
                "expected_release_ref": case["release"]["release_digest"],
                "expected_policy_ref": case["policy"]["policy_digest"],
                **case["parameters"],
            }
            | overrides
        )
    )


@pytest.fixture(scope="module")
def handwritten(split_input_factory):
    case = split_input_factory()
    return {
        "rows": case["candidate"]["observations"],
        "sources": case["sources"],
        "recipe": case["recipe"],
        "policy": case["policy"],
        "parameters": case["parameters"],
        "expected": HANDWRITTEN,
    }


@pytest.fixture(scope="module")
def patterned(reference_population_factory):
    return reference_population_factory(600, long_ids=True)


@pytest.fixture(scope="module")
def boundary(split_input_factory):
    case = split_input_factory()
    recipe = case["recipe"]
    rows = [
        {
            "contract_version": "1.0.0",
            "observation_id": f"boundary-{index}",
            "listing_id": f"boundary-listing-{index}",
            "property_identity": {
                "status": "confirmed",
                "property_id": f"boundary-property-{index}",
                "confidence": None,
                "policy_ref": recipe["property_matching_policy_ref"],
            },
            "domain_policy_ref": recipe["domain_policy_ref"],
            "domain_status": "valid",
            "published_at": instant,
            "collected_at": instant,
            "features_available_at": instant,
            "prediction_cutoff_at": instant,
            "temporal_evidence_ref": content_digest(b"synthetic temporal evidence"),
        }
        for index, instant in enumerate(BOUNDARY_INSTANTS)
    ]
    return {
        "rows": rows,
        "sources": [envelope(rows, "boundary")],
        "recipe": recipe,
        "policy": case["policy"],
        "parameters": case["parameters"],
        "expected": BOUNDARY,
    }


@pytest.fixture(scope="module", params=["handwritten", "patterned", "boundary"])
def pair(request, tmp_path_factory):
    population = request.getfixturevalue(request.param)
    directory = tmp_path_factory.mktemp(request.param)
    cases = {"v1": stage_v1(directory, population), "v2": stage_v2(directory, population)}
    for key, case in cases.items():
        case["output"] = directory / f"split-{key}"
        case["manifest"] = materialize(case, case["output"])
    return cases


@pytest.fixture(scope="module")
def template(handwritten, tmp_path_factory):
    directory = tmp_path_factory.mktemp("template")
    return {"v1": stage_v1(directory, handwritten), "v2": stage_v2(directory, handwritten)}


@pytest.fixture(scope="module")
def other_release(boundary, tmp_path_factory):
    return stage_v2(tmp_path_factory.mktemp("other-release"), boundary)


@pytest.fixture
def fresh(template, tmp_path):
    """An owned copy of the verified small v2 restoration that a test may damage."""
    restored = tmp_path / "restored"
    shutil.copytree(template["v2"]["restored"], restored)
    return {**template["v2"], "restored": restored, "output": tmp_path / "split"}


@pytest.fixture(scope="module")
def large(reference_population_factory, tmp_path_factory):
    # Logical inventory JSON above 1 MiB. Its complete split stays well below the bound.
    population = reference_population_factory(1_500, long_ids=True)
    return stage_v2(tmp_path_factory.mktemp("large"), population)


@pytest.fixture(scope="module")
def over_bound(reference_population_factory, tmp_path_factory):
    # A supported v2 release whose complete split cannot fit one JSON document.
    population = reference_population_factory(3_000, long_ids=True, multi=True)
    return stage_v2(tmp_path_factory.mktemp("over-bound"), population)


def logical_inventory(rows):
    return json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def identity_ids(expected, cohort):
    return [row["observation_id"] for row in expected if cohort in row["cohorts"]]


def split_document(population, memberships, *, observations_digest):
    """A sealed split assembled outside the production builder, for contract-level checks."""
    parameters = population["parameters"]
    manifest = {
        "contract_version": "1.0.0",
        "access_domain": "development",
        "dataset_ref": content_digest(b"synthetic dataset envelope"),
        "observations_digest": observations_digest,
        "policy_ref": population["policy"]["policy_digest"],
        "training_cutoff": parameters["training_cutoff"],
        "validation_window": parameters["validation_window"],
        "memberships": memberships,
        "creation_provenance": parameters["creation_provenance"],
    }
    manifest["split_digest"] = development_split_digest(manifest)
    return manifest


# --- Parity and version-specific lineage -------------------------------------------------


def test_v1_and_v2_releases_produce_the_same_assignments_with_version_specific_lineage(pair):
    v1, v2 = pair["v1"], pair["v2"]
    assert (v1["release"]["contract_version"], v2["release"]["contract_version"]) == (
        "1.0.0",
        "2.0.0",
    )
    manifests = {}
    for key, case in (("v1", v1), ("v2", v2)):
        manifest = case["manifest"]
        assert read(case, case["output"], manifest["split_digest"]) == manifest
        assert (case["output"] / SPLIT_FILE).read_bytes() == canonical_bytes(manifest)
        assert [path.name for path in case["output"].iterdir()] == [SPLIT_FILE]
        manifests[key] = manifest
    one, two = manifests["v1"], manifests["v2"]

    # Partition, exclusion reasons and both cohorts equal each other and the handwritten rules.
    assert one["memberships"] == two["memberships"] == v1["expected"]
    independent = "sha256:" + hashlib.sha256(logical_inventory(v1["rows"])).hexdigest()
    assert one["observations_digest"] == two["observations_digest"] == independent
    for cohort in ("future_market", "unseen_property"):
        ids = identity_ids(v1["expected"], cohort)
        assert ids
        for manifest in manifests.values():
            validate_development_population(
                manifest, ids[::-1], cohort=cohort, expected_split_ref=manifest["split_digest"]
            )

    # Only release lineage differs: each split names its own release version's identity.
    assert one["dataset_ref"] == v1["release"]["release_digest"]
    assert two["dataset_ref"] == v2["release"]["release_digest"]
    assert one["dataset_ref"] != two["dataset_ref"]
    assert one["split_digest"] != two["split_digest"]
    shared = {"dataset_ref", "split_digest"}
    assert {k: v for k, v in one.items() if k not in shared} == {
        k: v for k, v in two.items() if k not in shared
    }


def test_a_split_cannot_be_presented_under_the_other_release_version(pair):
    manifests = {key: pair[key]["manifest"] for key in ("v1", "v2")}
    for own, other in (("v1", "v2"), ("v2", "v1")):
        case = pair[other]
        with pytest.raises(ContractError, match="dataset identity mismatch"):
            read(case, pair[own]["output"], manifests[own]["split_digest"])
        with pytest.raises(ContractError, match="dataset identity mismatch"):
            validate_release_split(
                manifests[own],
                release=case["release"],
                observations=case["rows"],
                policy=case["policy"],
                expected_release_ref=case["release"]["release_digest"],
                expected_policy_ref=case["policy"]["policy_digest"],
                expected_split_ref=manifests[own]["split_digest"],
            )


def test_verified_population_is_the_complete_projection_for_both_versions(template):
    for key in ("v1", "v2"):
        case = template[key]
        arguments = {
            "manifest": case["release"],
            "expected_release_ref": case["release"]["release_digest"],
        }
        rows = read_verified_restore_observations(case["restored"], **arguments)
        assert rows == case["rows"]
        rows[0]["domain_status"] = "invalid"
        rows[0]["property_identity"]["policy_ref"] = "synthetic mutation"
        assert read_verified_restore_observations(case["restored"], **arguments) == case["rows"]
    inline = read_verified_restore(
        template["v1"]["restored"],
        manifest=template["v1"]["release"],
        expected_release_ref=template["v1"]["release"]["release_digest"],
    )
    assert inline["observations"] == template["v1"]["rows"]


def test_reordered_population_and_independent_staging_give_identical_bytes(
    handwritten, template, tmp_path
):
    case = template["v2"]
    expected = canonical_bytes(build(case))
    assert canonical_bytes(build(case, observations=case["rows"][::-1])) == expected
    again = stage_v2(tmp_path, handwritten)  # an independent, separately staged copy
    assert again["release"] == case["release"]
    assert canonical_bytes(materialize(again, tmp_path / "split")) == expected


# --- The opt-in inventory bound in the evaluation contract --------------------------------


def test_default_inventory_bound_is_unchanged_and_the_opt_in_digest_is_identical(
    handwritten, reference_population_factory
):
    rows = handwritten["rows"]
    default = observation_inventory_digest(rows)
    assert observation_inventory_digest(rows, max_inventory_records=len(rows)) == default
    assert observation_inventory_digest(rows[::-1], max_inventory_records=10_000) == default

    population = reference_population_factory(1_500, long_ids=True)
    big = population["rows"]
    logical = logical_inventory(big)
    assert len(logical) > MAX_DOCUMENT_BYTES
    with pytest.raises(DocumentSizeError, match="size limit"):
        observation_inventory_digest(big)
    expected = content_digest(logical)
    assert observation_inventory_digest(big, max_inventory_records=len(big)) == expected
    streamed = ObservationInventoryHasher(max_records=len(big))
    for row in big:
        streamed.add(row)
    assert streamed.digest() == expected

    parameters = population["parameters"]
    arguments = {
        "policy": population["policy"],
        "training_cutoff": parameters["training_cutoff"],
        "validation_window": parameters["validation_window"],
    }
    with pytest.raises(DocumentSizeError, match="size limit"):
        derive_development_memberships(big, **arguments)
    derived = derive_development_memberships(big, **arguments, max_inventory_records=len(big))
    assert derived == population["expected"]

    manifest = split_document(population, derived, observations_digest=expected)
    check = {
        "policy": population["policy"],
        "observations": big,
        "expected_dataset_ref": manifest["dataset_ref"],
    }
    with pytest.raises(DocumentSizeError, match="size limit"):
        validate_development_split(manifest, **check)
    validate_development_split(manifest, **check, max_inventory_records=len(big))
    manifest["memberships"][0]["partition"] = "excluded"
    manifest["split_digest"] = development_split_digest(manifest)
    with pytest.raises(ContractError, match="eligibility assignment mismatch"):
        validate_development_split(manifest, **check, max_inventory_records=len(big))


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "10", [10]])
def test_invalid_record_limits_are_rejected_by_every_helper(handwritten, limit):
    parameters = handwritten["parameters"]
    seeded = {
        "policy": handwritten["policy"],
        "training_cutoff": parameters["training_cutoff"],
        "validation_window": parameters["validation_window"],
    }
    rows = handwritten["rows"]
    manifest = split_document(
        handwritten,
        derive_development_memberships(rows, **seeded),
        observations_digest=observation_inventory_digest(rows),
    )
    message = "invalid observation inventory record limit"
    with pytest.raises(ContractError, match=message):
        observation_inventory_digest(rows, max_inventory_records=limit)
    with pytest.raises(ContractError, match=message):
        derive_development_memberships(rows, **seeded, max_inventory_records=limit)
    with pytest.raises(ContractError, match=message):
        validate_development_split(
            manifest,
            policy=handwritten["policy"],
            observations=rows,
            expected_dataset_ref=manifest["dataset_ref"],
            max_inventory_records=limit,
        )


def test_a_record_limit_below_the_population_fails_without_truncation(handwritten):
    rows, parameters = handwritten["rows"], handwritten["parameters"]
    message = "observation inventory record limit exceeded"
    with pytest.raises(ContractError, match=message):
        observation_inventory_digest(rows, max_inventory_records=len(rows) - 1)
    with pytest.raises(ContractError, match=message):
        derive_development_memberships(
            rows,
            policy=handwritten["policy"],
            training_cutoff=parameters["training_cutoff"],
            validation_window=parameters["validation_window"],
            max_inventory_records=len(rows) - 1,
        )


def test_size_errors_are_distinguishable_without_changing_contract_error_handling():
    oversized = {"value": "x" * MAX_DOCUMENT_BYTES}
    for call in (
        lambda: canonical_json(oversized),
        lambda: load_document(b" " * (MAX_DOCUMENT_BYTES + 1)),
        lambda: load_document(json.dumps(oversized)),
    ):
        with pytest.raises(DocumentSizeError, match="^document size limit exceeded$") as error:
            call()
        assert isinstance(error.value, ContractError)
    for call in (
        lambda: canonical_json({"value": float("nan")}),
        lambda: canonical_json({1: "non-string key"}),
        lambda: load_document(b"{"),
    ):
        with pytest.raises(ContractError) as error:
            call()
        assert not isinstance(error.value, DocumentSizeError)


# --- Input inventory limits are distinct from split output limits -------------------------


def test_a_v2_inventory_above_the_legacy_limit_materializes_and_reads_back(large, tmp_path):
    case = large
    logical = logical_inventory(case["rows"])
    assert len(logical) > MAX_DOCUMENT_BYTES  # input: far above the legacy inline bound
    assert case["candidate"]["inventory"]["artifact"]["size_bytes"] > MAX_DOCUMENT_BYTES
    with pytest.raises(ContractError, match="source inventory size limit exceeded"):
        build_observation_candidate(case["sources"], **case["recipe"])  # inline v1 cannot hold it
    with pytest.raises(DocumentSizeError):
        observation_inventory_digest(case["rows"])  # the legacy digest cannot hash it
    assert case["release"]["observations_digest"] == content_digest(logical)

    before = snapshot(case["restored"])
    manifest = materialize(case, tmp_path / "split")
    assert read(case, tmp_path / "split", manifest["split_digest"]) == manifest
    assert manifest["memberships"] == case["expected"]  # the closed-form rules, row by row
    assert manifest["observations_digest"] == case["release"]["observations_digest"]
    stored = (tmp_path / "split" / SPLIT_FILE).read_bytes()
    assert stored == canonical_bytes(manifest)
    assert 400_000 < len(stored) < MAX_DOCUMENT_BYTES  # output: a different, smaller bound
    assert snapshot(case["restored"]) == before
    assert [path.name for path in (tmp_path / "split").iterdir()] == [SPLIT_FILE]
    for cohort in ("future_market", "unseen_property"):
        validate_development_population(
            manifest,
            identity_ids(case["expected"], cohort),
            cohort=cohort,
            expected_split_ref=manifest["split_digest"],
        )
    assert identity_ids(case["expected"], "unseen_property") == [
        row["observation_id"] for row in case["expected"][1::6]
    ]


def test_a_complete_split_above_the_output_bound_is_rejected_before_finalization(
    over_bound, tmp_path
):
    case = over_bound
    assert len(logical_inventory(case["rows"])) > MAX_DOCUMENT_BYTES  # the input is accepted
    with pytest.raises(DocumentSizeError):
        canonical_json(case["expected"])  # yet the rows alone no longer fit one document

    # Restoration and derivation succeed; only the complete split document is refused.
    before = snapshot(case["restored"])
    destination = tmp_path / "split"
    with pytest.raises(ContractError, match=f"^{OUTPUT_LIMIT}$") as failure:
        materialize(case, destination)
    assert not isinstance(failure.value, DocumentSizeError)
    assert failure.value.__cause__ is None
    assert not destination.exists()
    assert not list(tmp_path.iterdir())  # no directory, final file or staged temporary
    assert snapshot(case["restored"]) == before

    # No readable split exists for this release, whatever reference a reader expects.
    destination.mkdir()
    with pytest.raises(ReleaseError, match="ARTIFACT_UNAVAILABLE"):
        read(case, destination, content_digest(b"no split can exist"))
    assert not list(destination.iterdir())


def test_population_above_the_ceiling_is_rejected_before_any_derivation(template, monkeypatch):
    v1, v2 = template["v1"], template["v2"]
    expected = canonical_bytes(build(v1))
    monkeypatch.setattr(splits, "MAX_SPLIT_OBSERVATIONS", len(v2["rows"]) - 1)

    def forbidden(*args, **kwargs):
        raise AssertionError("derivation must not run for a population that cannot fit")

    with monkeypatch.context() as patch:
        patch.setattr(splits, "derive_development_memberships", forbidden)
        with pytest.raises(ContractError, match=f"^{OUTPUT_LIMIT}$"):
            build(v2)
        with pytest.raises(ContractError, match=f"^{OUTPUT_LIMIT}$"):
            validate_release_split(
                {},
                release=v2["release"],
                observations=v2["rows"],
                policy=v2["policy"],
                expected_release_ref=v2["release"]["release_digest"],
                expected_policy_ref=v2["policy"]["policy_digest"],
                expected_split_ref=content_digest(b"unused"),
            )
    # The ceiling belongs to v2 only; an inline release keeps its exact v1 behavior.
    assert canonical_bytes(build(v1)) == expected


def reachable_rows(observation_id):
    """Every membership shape the existing rules can derive, with sorted reason arrays."""

    def subsets(items):
        return chain.from_iterable(combinations(items, n) for n in range(len(items) + 1))

    def row(partition, eligibility, cohorts, unseen):
        return membership(
            observation_id,
            partition,
            exclusions=sorted(eligibility),
            cohorts=cohorts,
            unseen=sorted(unseen),
        )

    yield row("training", [], [], ["not_development_validation"])
    temporal = [
        "temporal_evidence_missing",
        "temporal_order_invalid",
        "outside_development_windows",
    ]
    for domain in (None, "invalid_non_target_domain", "unresolved_non_target_domain"):
        for rest in subsets(temporal):
            reasons = ([domain] if domain else []) + list(rest)
            if reasons:
                yield row("excluded", reasons, [], ["not_development_validation"])
    yield row("development_validation", [], list(BOTH), [])
    unseen = [
        "listing_seen_in_training",
        "property_overlap_training",
        "property_identity_unconfirmed",
        "training_identity_unresolved",
    ]
    for reasons in subsets(unseen):
        if reasons:
            yield row("development_validation", [], list(FUTURE), reasons)


def test_split_capacity_follows_from_the_smallest_and_largest_reachable_rows():
    def size(document):
        return len(canonical_bytes(document))

    shortest = list(reachable_rows("a"))
    longest = list(reachable_rows("x" * 128))
    assert len(shortest) == 40
    assert min(map(size, shortest)) == size(splits._SMALLEST_MEMBERSHIP) == 146
    assert max(map(size, longest)) == 391
    assert MAX_SPLIT_OBSERVATIONS == MAX_DOCUMENT_BYTES // (146 + 1) == 7_133

    def split_with(rows):
        return {
            "contract_version": "1.0.0",
            "access_domain": "development",
            "dataset_ref": "sha256:" + "0" * 64,
            "observations_digest": "sha256:" + "0" * 64,
            "policy_ref": "sha256:" + "0" * 64,
            "training_cutoff": "2026-01-20T00:00:00Z",
            "validation_window": {
                "start_inclusive": "2026-02-01T00:00:00Z",
                "end_exclusive": "2026-03-01T00:00:00Z",
            },
            "memberships": rows,
            "creation_provenance": {
                "source_snapshot_ref": "sha256:" + "0" * 64,
                "created_at": "2026-03-03T12:00:00Z",
            },
            "split_digest": "sha256:" + "0" * 64,
        }

    def capacity(row):
        """The largest population of identical rows whose complete split fits, checked exactly."""
        count = (MAX_DOCUMENT_BYTES - size(split_with([])) + 1) // (size(row) + 1)
        assert size(split_with([row] * count)) <= MAX_DOCUMENT_BYTES
        with pytest.raises(DocumentSizeError):
            canonical_bytes(split_with([row] * (count + 1)))
        return count

    assert size(split_with([])) == 734  # the fixed fields outside the memberships
    assert capacity(max(longest, key=size)) == 2_673  # always fits, whatever the content
    assert capacity(min(shortest, key=size)) == 7_128  # no population above this ever fits
    assert capacity(membership("x" * 128, "excluded", exclusions=FOUR_REASONS)) == 2_728
    one_reason = ("temporal_evidence_missing",)
    assert [
        capacity(membership("x" * length, "excluded", exclusions=one_reason))
        for length in (16, 32, 64, 128)
    ] == [5_544, 5_111, 4_421, 3_481]


def test_exact_output_size_is_enforced_at_the_digest_boundary(monkeypatch):
    manifest = {"memberships": [], "note": "x" * 50}
    base = len(canonical_bytes(manifest))
    digest_field = len(',"split_digest":"sha256:' + "0" * 64 + '"')
    assert digest_field == 89
    for limit, accepted in ((base - 1, False), (base + 50, False), (base + digest_field, True)):
        with monkeypatch.context() as patch:
            patch.setattr("rent_contracts.validation.MAX_DOCUMENT_BYTES", limit)
            if accepted:
                assert splits._seal(manifest) == development_split_digest(manifest)
            else:
                with pytest.raises(ContractError, match=f"^{OUTPUT_LIMIT}$") as failure:
                    splits._seal(manifest)
                assert not isinstance(failure.value, DocumentSizeError)


# --- Wrong references, missing or tampered evidence and unsafe paths --------------------


@pytest.mark.parametrize(
    "kind", ["release", "candidate", "inventory-digest", "parquet-file", "policy", "split-policy"]
)
def test_wrong_expected_references_fail_before_any_output(fresh, kind):
    release = fresh["release"]
    overrides = {
        "release": {"expected_release_ref": content_digest(b"another release")},
        "candidate": {"expected_release_ref": release["candidate_ref"]},
        "inventory-digest": {"expected_release_ref": release["observations_digest"]},
        "parquet-file": {"expected_release_ref": release["inventory"]["artifact"]["digest"]},
        "policy": {"expected_policy_ref": content_digest(b"another policy")},
        "split-policy": {"expected_policy_ref": release["observations_digest"]},
    }[kind]
    with pytest.raises(ContractError):
        materialize(fresh, fresh["output"], **overrides)
    assert not fresh["output"].exists()


def test_reader_requires_every_external_identity(fresh):
    manifest = materialize(fresh, fresh["output"])
    for name in ("expected_release_ref", "expected_policy_ref", "expected_split_ref"):
        with pytest.raises(ContractError):
            read(
                fresh,
                fresh["output"],
                manifest["split_digest"],
                **{name: content_digest(b"substituted identity")},
            )
    assert read(fresh, fresh["output"], manifest["split_digest"]) == manifest


def test_a_release_for_another_population_cannot_vouch_for_this_payload(fresh, other_release):
    other = other_release
    with pytest.raises(ContractError):
        materialize(
            fresh,
            fresh["output"],
            release=other["release"],
            expected_release_ref=other["release"]["release_digest"],
        )
    assert not fresh["output"].exists()


@pytest.mark.parametrize("kind", ["v1-release", "foreign-payload"])
def test_release_versions_and_payload_layouts_cannot_be_mixed(fresh, template, kind):
    v1 = template["v1"]
    if kind == "v1-release":
        overrides = {
            "release": v1["release"],
            "expected_release_ref": v1["release"]["release_digest"],
        }
    else:
        shutil.rmtree(fresh["restored"] / "payload")
        shutil.copytree(v1["restored"] / "payload", fresh["restored"] / "payload")
        overrides = {}
    with pytest.raises(ContractError):
        materialize(fresh, fresh["output"], **overrides)
    assert not fresh["output"].exists()


def damage(case, kind, tmp_path):
    root = case["restored"]
    payload, inventory = root / "payload", root / "payload/inventory"
    if kind == "parquet-byte":
        raw = (inventory / PARQUET_FILE).read_bytes()
        (inventory / PARQUET_FILE).write_bytes(raw[:4] + bytes([raw[4] ^ 1]) + raw[5:])
    elif kind == "parquet-missing":
        (inventory / PARQUET_FILE).unlink()
    elif kind == "manifest-missing":
        (inventory / MANIFEST_FILE).unlink()
    elif kind == "manifest-whitespace":
        (inventory / MANIFEST_FILE).write_bytes((inventory / MANIFEST_FILE).read_bytes() + b" ")
    elif kind == "inventory-extra":
        (inventory / "synthetic-unlisted").touch()
    elif kind == "parquet-symlink":
        target = tmp_path / "synthetic-outside"
        (inventory / PARQUET_FILE).rename(target)
        (inventory / PARQUET_FILE).symlink_to(target)
    elif kind == "inventory-symlink":
        target = tmp_path / "synthetic-inventory"
        inventory.rename(target)
        inventory.symlink_to(target, target_is_directory=True)
    elif kind == "candidate":
        (payload / "candidate.json").write_bytes(b"{}")
    elif kind == "quality-report":
        (payload / "quality-report.json").write_bytes(b"{}")
    elif kind == "source-altered":
        path = next((payload / "sources").iterdir())
        path.write_bytes(path.read_bytes() + b" ")
    elif kind == "source-missing":
        next((payload / "sources").iterdir()).unlink()
    elif kind == "payload-extra":
        (payload / "extra.json").write_bytes(b"{}")
    elif kind == "payload-symlink":
        target = tmp_path / "synthetic-payload"
        payload.rename(target)
        payload.symlink_to(target, target_is_directory=True)
    else:
        raise AssertionError(kind)


PAYLOAD_DAMAGE = [
    "parquet-byte",
    "parquet-missing",
    "manifest-missing",
    "manifest-whitespace",
    "inventory-extra",
    "parquet-symlink",
    "inventory-symlink",
    "candidate",
    "quality-report",
    "source-altered",
    "source-missing",
    "payload-extra",
    "payload-symlink",
]


@pytest.mark.parametrize("kind", PAYLOAD_DAMAGE)
def test_damaged_inventory_or_payload_is_never_consumed(fresh, tmp_path, kind):
    damage(fresh, kind, tmp_path)
    with pytest.raises(ContractError) as failure:
        materialize(fresh, fresh["output"])
    assert str(tmp_path) not in str(failure.value)
    assert not fresh["output"].exists()


@pytest.mark.parametrize(
    "kind", ["parquet-byte", "manifest-whitespace", "source-altered", "candidate"]
)
def test_a_previously_valid_split_is_not_readable_after_the_payload_changes(fresh, tmp_path, kind):
    manifest = materialize(fresh, fresh["output"])
    assert read(fresh, fresh["output"], manifest["split_digest"]) == manifest
    marker = (fresh["restored"] / COMPLETION_FILE).read_bytes()
    stored = (fresh["output"] / SPLIT_FILE).read_bytes()
    damage(fresh, kind, tmp_path)
    with pytest.raises(ContractError):
        read(fresh, fresh["output"], manifest["split_digest"])
    assert (fresh["restored"] / COMPLETION_FILE).read_bytes() == marker
    assert (fresh["output"] / SPLIT_FILE).read_bytes() == stored


def resealed_report(case, **changes):
    report = load_document((case["restored"] / COMPLETION_FILE).read_bytes())
    report.update(changes)
    report["report_digest"] = restoration_report_digest(report)
    return canonical_bytes(report)


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "empty",
        "other-release",
        "altered",
        "resealed-count",
        "resealed-release",
        "resealed-artifacts",
        "fifo",
        "symlink",
        "oversized",
    ],
)
def test_missing_or_invalid_restoration_evidence_is_never_consumed(fresh, other_release, kind):
    marker = fresh["restored"] / COMPLETION_FILE
    if kind == "missing":
        marker.unlink()
    elif kind == "empty":
        marker.write_bytes(b"{}")
    elif kind == "other-release":
        marker.write_bytes((other_release["restored"] / COMPLETION_FILE).read_bytes())
    elif kind == "altered":
        report = load_document(marker.read_bytes())
        report["artifact_count"] += 1  # the self-digest no longer matches
        marker.write_bytes(canonical_bytes(report))
    elif kind == "resealed-count":
        marker.write_bytes(resealed_report(fresh, observation_count=1))
    elif kind == "resealed-release":
        marker.write_bytes(resealed_report(fresh, release_ref=content_digest(b"other release")))
    elif kind == "resealed-artifacts":
        marker.write_bytes(resealed_report(fresh, artifacts_digest=content_digest(b"other roster")))
    elif kind == "fifo":
        marker.unlink()
        os.mkfifo(marker)
    elif kind == "symlink":
        target = fresh["restored"].parent / "outside-report.json"
        marker.rename(target)
        marker.symlink_to(target)
    else:
        marker.write_bytes(b" " * (MAX_DOCUMENT_BYTES + 1))
    with pytest.raises(ContractError):
        materialize(fresh, fresh["output"])
    assert not fresh["output"].exists()


@pytest.mark.parametrize(
    "kind",
    [
        "directory",
        "file",
        "link",
        "link-parent",
        "relative",
        "traversal",
        "inside-source",
        "inside-inventory",
        "ancestor",
        "source-link",
        "source-relative",
        "source-alias-parent",
    ],
)
def test_output_and_input_paths_cannot_overwrite_or_overlap(fresh, tmp_path, kind):
    destination, restored = fresh["output"], fresh["restored"]
    before = snapshot(restored)
    if kind == "directory":
        destination.mkdir()
        (destination / "preserve").write_bytes(b"existing")
    elif kind == "file":
        destination.write_bytes(b"existing")
    elif kind == "link":
        destination.symlink_to(restored, target_is_directory=True)
    elif kind == "link-parent":
        parent = tmp_path / "parent-link"
        parent.symlink_to(tmp_path, target_is_directory=True)
        destination = parent / "split"
    elif kind == "relative":
        destination = Path("relative-output")
    elif kind == "traversal":
        destination = restored / ".." / "split"
    elif kind == "inside-source":
        destination = restored / "payload/split"
    elif kind == "inside-inventory":
        destination = restored / "payload/inventory/split"
    elif kind == "ancestor":
        destination = tmp_path
    elif kind == "source-link":
        restored = tmp_path / "source-link"
        restored.symlink_to(fresh["restored"], target_is_directory=True)
    elif kind == "source-relative":
        restored = Path("relative-source")
    else:
        # A v2 restoration must be reached by a resolved path, not through an alias.
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        restored = alias / "restored"
    with pytest.raises(ReleaseError):
        materialize(fresh, destination, restored_directory=restored)
    assert snapshot(fresh["restored"]) == before
    if kind == "directory":
        assert (destination / "preserve").read_bytes() == b"existing"
    elif kind == "file":
        assert destination.read_bytes() == b"existing"
    elif kind not in ("link", "ancestor"):
        assert not fresh["output"].exists()


# --- Incomplete or interrupted outputs ------------------------------------------------------


@pytest.mark.parametrize("operation", ["mkstemp", "write", "fsync", "link"])
def test_interrupted_atomic_creation_leaves_no_final_split(fresh, monkeypatch, operation):
    before = snapshot(fresh["restored"])

    def fail(*args, **kwargs):
        raise OSError("synthetic-private-path-do-not-log")

    if operation == "write":
        original = release_io.os.fdopen

        @contextmanager
        def interrupted(*args, **kwargs):
            with original(*args, **kwargs) as stream:
                if "w" not in (args[1] if len(args) > 1 else kwargs.get("mode", "r")):
                    yield stream
                    return

                class Writer:
                    def write(self, raw):
                        stream.write(raw[:5])
                        fail()

                yield Writer()

        monkeypatch.setattr(release_io.os, "fdopen", interrupted)
    elif operation == "mkstemp":
        monkeypatch.setattr(tempfile, operation, fail)
    else:
        monkeypatch.setattr(release_io.os, operation, fail)
    with pytest.raises(ReleaseError, match="FINALIZATION_FAILED") as failure:
        materialize(fresh, fresh["output"])
    assert "synthetic-private-path" not in str(failure.value)
    assert not (fresh["output"] / SPLIT_FILE).exists()
    assert not list(fresh["output"].glob(".artifact-*"))
    assert snapshot(fresh["restored"]) == before
    monkeypatch.undo()
    # A failed attempt is never reused: a new destination succeeds from the same restoration.
    again = materialize(fresh, fresh["output"].with_name("split-retry"))
    assert again["memberships"] == HANDWRITTEN


@pytest.mark.parametrize(
    "kind", ["missing", "json", "bom", "oversized", "file-link", "root-link", "fifo"]
)
def test_invalid_split_file_states_are_not_consumed(fresh, tmp_path, kind):
    manifest = materialize(fresh, fresh["output"])
    path = fresh["output"] / SPLIT_FILE
    if kind == "missing":
        path.unlink()
    elif kind == "json":
        path.write_bytes(b"{")
    elif kind == "bom":
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    elif kind == "oversized":
        path.write_bytes(b" " * (MAX_DOCUMENT_BYTES + 1))
    elif kind == "file-link":
        outside = tmp_path / "outside.json"
        path.rename(outside)
        path.symlink_to(outside)
    elif kind == "root-link":
        outside = tmp_path / "outside-output"
        fresh["output"].rename(outside)
        fresh["output"].symlink_to(outside, target_is_directory=True)
    else:
        path.unlink()
        os.mkfifo(path)
    with pytest.raises(ContractError):
        read(fresh, fresh["output"], manifest["split_digest"])


@pytest.mark.parametrize("kind", ["omitted", "duplicate", "substituted", "cohort", "provenance"])
def test_resealed_incomplete_or_wrong_splits_do_not_bypass_the_reader(fresh, kind):
    original = materialize(fresh, fresh["output"])
    changed = json.loads(canonical_bytes(original))
    new = next(row for row in changed["memberships"] if row["observation_id"] == "obs-new")
    if kind == "omitted":
        changed["memberships"].pop()
    elif kind == "duplicate":
        changed["memberships"].append(dict(new))
    elif kind == "substituted":
        new["observation_id"] = "substituted-observation"
    elif kind == "cohort":
        new["cohorts"] = ["future_market"]
    else:
        changed["creation_provenance"]["created_at"] = "2026-03-04T12:00:00Z"
    changed["split_digest"] = development_split_digest(changed)
    (fresh["output"] / SPLIT_FILE).write_bytes(canonical_bytes(changed))
    # A fixed expected reference rejects even a semantically valid provenance change.
    expected = original if kind == "provenance" else changed
    with pytest.raises(ContractError):
        read(fresh, fresh["output"], expected["split_digest"])


def test_reader_keeps_accepting_previously_valid_array_order(fresh):
    manifest = materialize(fresh, fresh["output"])
    manifest["memberships"].reverse()
    for row in manifest["memberships"]:
        for name in ("cohorts", "eligibility_exclusions", "unseen_property_exclusions"):
            row[name].reverse()
    manifest["split_digest"] = development_split_digest(manifest)
    (fresh["output"] / SPLIT_FILE).write_bytes(canonical_bytes(manifest))
    assert read(fresh, fresh["output"], manifest["split_digest"]) == manifest
