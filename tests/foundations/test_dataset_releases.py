"""Pure synthetic release contracts; fixture bindings do not claim a DVC run."""

import copy

import pytest

from rent_contracts import ContractError, validate_document
from rent_contracts.validation import canonical_json
from rent_data.releases import (
    build_dataset_release,
    build_restoration_report,
    content_digest,
    data_tool_profile_digest,
    dataset_release_digest,
    document_digest,
    restoration_report_digest,
    validate_dataset_release,
    validate_release_candidate_binding,
    validate_restoration_report,
)


def test_closed_manifest_binds_complete_population_and_independent_identities(release_case):
    manifest = release_case["manifest"]
    candidate = release_case["candidate"]
    validate_document("dataset-release", manifest)
    validate_dataset_release(manifest, expected_release_ref=manifest["release_digest"])
    validate_release_candidate_binding(manifest, candidate)
    assert manifest["observation_count"] == len(candidate["observations"]) == 4
    assert manifest["observation_count"] == sum(
        s["record_count"] for s in manifest["acquisition_sources"]
    )
    assert len(manifest["artifacts"]) == 4
    assert manifest["candidate_ref"] == candidate["candidate_digest"]
    assert manifest["quality_report_ref"] == candidate["quality_report"]["report_digest"]
    assert manifest["observations_digest"] == candidate["observations_digest"]
    assert manifest["dvc"]["hash_algorithm"] == "md5"
    assert all(a["digest"].startswith("sha256:") for a in manifest["artifacts"])
    assert manifest["retention"] == {"status": "PENDING_REVIEW", "policy_ref": None}
    assert manifest["release_state"] == "SEALED_CANDIDATE"
    assert manifest["access_domain"] == "development"
    assert "split_ref" not in manifest  # Release identity does not imply evaluation membership.


def test_manifest_determinism_copying_and_no_git_digest_cycle(release_case):
    case = release_case
    snapshot = copy.deepcopy(case)
    rebuilt = build_dataset_release(
        case["candidate"],
        source_documents=case["sources"],
        binding=case["binding"],
        artifacts=case["artifacts"],
    )
    assert canonical_json(rebuilt) == canonical_json(case["manifest"])
    assert case == snapshot
    rebuilt["metadata"]["commit"] = "c" * 40
    rebuilt["release_digest"] = dataset_release_digest(rebuilt)
    assert rebuilt["release_digest"] != case["manifest"]["release_digest"]
    assert rebuilt["candidate_ref"] == case["manifest"]["candidate_ref"]
    assert case == snapshot


@pytest.mark.parametrize(
    "field,value",
    [
        ("access_domain", "final_holdout"),
        ("release_state", "PUBLISHED"),
        ("retention", {"status": "PENDING_REVIEW", "policy_ref": None, "days": 30}),
        ("observation_schema_version", "2.0.0"),
        ("observation_count", True),
        ("contract_version", "1.0.1"),
        ("extra", "unexpected"),
    ],
)
def test_manifest_rejects_policy_lifecycle_and_schema_extensions(release_case, field, value):
    manifest = release_case["manifest"]
    manifest[field] = value
    manifest["release_digest"] = dataset_release_digest(manifest)
    with pytest.raises(ContractError):
        validate_dataset_release(manifest, expected_release_ref=manifest["release_digest"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("commit", "main"),
        ("commit", "a" * 39),
        ("commit", "a" * 40 + "\n"),
        ("path", "../payload.dvc"),
        ("digest", "md5:" + "a" * 32),
    ],
)
def test_manifest_requires_exact_safe_git_metadata(release_case, field, value):
    manifest = release_case["manifest"]
    manifest["metadata"][field] = value
    manifest["release_digest"] = dataset_release_digest(manifest)
    with pytest.raises(ContractError):
        validate_dataset_release(manifest, expected_release_ref=manifest["release_digest"])


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "reorder",
        "traversal",
        "absolute",
        "backslash",
        "extra",
        "missing",
        "wrong-total-size",
        "wrong-total-count",
        "wrong-population",
        "wrong-source-digest",
        "duplicate-source",
        "source-reorder",
        "duplicate-raw-source",
    ],
)
def test_resealed_manifest_still_enforces_roster_and_population(release_case, mutation):
    m = release_case["manifest"]
    if mutation == "duplicate":
        m["artifacts"].append(copy.deepcopy(m["artifacts"][0]))
    elif mutation == "reorder":
        m["artifacts"].reverse()
    elif mutation in ("traversal", "absolute", "backslash"):
        m["artifacts"][0]["path"] = {
            "traversal": "../candidate.json",
            "absolute": "/candidate.json",
            "backslash": "sources\\x.json",
        }[mutation]
    elif mutation == "extra":
        m["artifacts"].append(
            {"path": "secret.json", "digest": content_digest(b"x"), "size_bytes": 1}
        )
    elif mutation == "missing":
        m["artifacts"].pop()
    elif mutation == "wrong-total-size":
        m["dvc"]["size_bytes"] += 1
    elif mutation == "wrong-total-count":
        m["dvc"]["file_count"] += 1
    elif mutation == "wrong-population":
        m["observation_count"] += 1
    elif mutation == "wrong-source-digest":
        m["artifacts"][-1]["digest"] = content_digest(b"wrong")
    elif mutation == "duplicate-source":
        m["acquisition_sources"].append(copy.deepcopy(m["acquisition_sources"][0]))
    elif mutation == "source-reorder":
        m["acquisition_sources"].reverse()
    elif mutation == "duplicate-raw-source":
        m["acquisition_sources"][1]["raw_source_ref"] = m["acquisition_sources"][0][
            "raw_source_ref"
        ]
    m["release_digest"] = dataset_release_digest(m)
    with pytest.raises(ContractError):
        validate_dataset_release(m, expected_release_ref=m["release_digest"])


def test_external_ref_and_internal_digest_are_both_required(release_case):
    manifest = release_case["manifest"]
    original_ref = manifest["release_digest"]
    with pytest.raises(ContractError, match="expected dataset"):
        validate_dataset_release(manifest, expected_release_ref=content_digest(b"wrong"))
    manifest["dataset_family"] = "another-synthetic-family"
    with pytest.raises(ContractError, match="digest mismatch"):
        validate_dataset_release(manifest, expected_release_ref=original_ref)
    manifest["release_digest"] = dataset_release_digest(manifest)
    with pytest.raises(ContractError, match="expected dataset"):
        validate_dataset_release(manifest, expected_release_ref=original_ref)


@pytest.mark.parametrize(
    "field",
    [
        "dataset_family",
        "candidate_ref",
        "quality_report_ref",
        "observations_digest",
        "provenance",
    ],
)
def test_candidate_binding_rejects_resealed_provenance_changes(release_case, field):
    manifest = release_case["manifest"]
    if field == "provenance":
        manifest[field]["transformation_ref"] = content_digest(b"other")
    else:
        manifest[field] = (
            "another-family" if field == "dataset_family" else content_digest(b"other")
        )
    manifest["release_digest"] = dataset_release_digest(manifest)
    with pytest.raises(ContractError, match="provenance"):
        validate_release_candidate_binding(manifest, release_case["candidate"])


def test_build_requires_source_backed_candidate_and_complete_binding(release_case):
    case = release_case
    with pytest.raises(ContractError):
        build_dataset_release(
            case["candidate"],
            source_documents=case["sources"][:1],
            binding=case["binding"],
            artifacts=case["artifacts"],
        )
    with pytest.raises(ContractError):
        build_dataset_release(
            case["candidate"],
            source_documents=case["sources"],
            binding={**case["binding"], "extra": None},
            artifacts=case["artifacts"],
        )


@pytest.mark.parametrize("path", ["candidate.json", "quality-report.json"])
def test_builder_rejects_false_canonical_artifact_declarations(release_case, path):
    case = release_case
    artifacts = copy.deepcopy(case["artifacts"])
    next(row for row in artifacts if row["path"] == path)["digest"] = content_digest(b"false")
    with pytest.raises(ContractError, match="artifact correspondence"):
        build_dataset_release(
            case["candidate"],
            source_documents=case["sources"],
            binding=case["binding"],
            artifacts=artifacts,
        )


def test_restoration_report_is_closed_and_matches_every_release_identity(release_case):
    manifest = release_case["manifest"]
    report = build_restoration_report(manifest)
    validate_restoration_report(
        report, manifest=manifest, expected_release_ref=manifest["release_digest"]
    )
    assert report["artifacts_digest"] == document_digest(manifest["artifacts"])
    assert report["fresh_cache"] is True
    assert report["verification_method"] == "fresh-local-dvc-pull-and-sha256-v1"
    assert "timestamp" not in report  # No invented chronology is needed for content identity.
    for field in ("release_ref", "observations_digest", "tool_profile_ref", "artifacts_digest"):
        changed = copy.deepcopy(report)
        changed[field] = content_digest(b"wrong")
        changed["report_digest"] = restoration_report_digest(changed)
        with pytest.raises(ContractError):
            validate_restoration_report(
                changed, manifest=manifest, expected_release_ref=manifest["release_digest"]
            )
    for field, value in (("status", "FAILED"), ("fresh_cache", False), ("extra", "private path")):
        changed = {**report, field: value}
        changed["report_digest"] = restoration_report_digest(changed)
        with pytest.raises(ContractError):
            validate_restoration_report(
                changed, manifest=manifest, expected_release_ref=manifest["release_digest"]
            )
    report["observation_count"] += 1
    with pytest.raises(ContractError, match="digest mismatch"):
        validate_restoration_report(
            report, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )


def test_tool_profile_binds_build_backend_and_tool_closure_separately():
    first = data_tool_profile_digest(tool_lock=b"tools", build_lock=b"build")
    assert first == data_tool_profile_digest(tool_lock=b"tools", build_lock=b"build")
    assert first != data_tool_profile_digest(tool_lock=b"other", build_lock=b"build")
    assert first != data_tool_profile_digest(tool_lock=b"tools", build_lock=b"other")
    with pytest.raises(ContractError):
        data_tool_profile_digest(tool_lock="tools", build_lock=b"build")
