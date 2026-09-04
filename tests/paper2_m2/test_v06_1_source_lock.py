from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import pytest

from paper2_m2.protocol_v06_1 import (
    FROZEN_TEST_EOF_COMPATIBILITY_V06_1,
    evaluate_exact_test_eof_compatibility,
)


PROJECT_ROOT = Path(__file__).parents[2]


def _load_runner():
    runner_path = PROJECT_ROOT / "scripts/run_paper2_m2_identity_gate_v06_1.py"
    specification = importlib.util.spec_from_file_location("v06_1_runner", runner_path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _exact_arguments() -> dict:
    protocol = FROZEN_TEST_EOF_COMPATIBILITY_V06_1
    content = (PROJECT_ROOT / protocol.relative_path).read_bytes()
    return {
        "source_label": protocol.source_label,
        "relative_path": protocol.relative_path,
        "manifest_expected_sha256": protocol.t64_manifest_expected_sha256,
        "current_content": content,
        "git_clean": True,
        "t128_manifest_sha256": protocol.t128_manifest_sha256,
        "t128_recorded_current_sha256": protocol.current_sha256,
        "t256_manifest_sha256": protocol.t256_manifest_sha256,
        "t256_recorded_current_sha256": protocol.current_sha256,
        "t64_other_source_locks_pass": True,
        "t128_source_lock_pass": True,
        "t256_source_lock_pass": True,
        "host_tests_pass": True,
    }


def test_exact_singleton_accepts_only_the_frozen_T64_eof_delta() -> None:
    result = evaluate_exact_test_eof_compatibility(**_exact_arguments())
    assert result["pass"] is True
    assert result["accepted_label"] == "ACCEPTED_TEST_EOF_FORMATTING_DELTA"
    assert result["observed"]["current_bytes"] == 1681
    assert result["observed"]["transformed_bytes"] == 1682
    assert result["observed"]["source_file_written"] is False
    assert result["observed"]["whitespace_normalization_used"] is False


@pytest.mark.parametrize(
    ("changed_field", "changed_value", "failed_check"),
    [
        ("source_label", "T128", "source_label_is_exactly_T64"),
        (
            "relative_path",
            "tests/paper2_m2/test_protocol_v02.py",
            "relative_path_is_exact",
        ),
        ("manifest_expected_sha256", "0" * 64, "T64_manifest_expected_sha256_is_exact"),
        ("git_clean", False, "current_test_file_is_git_clean"),
        ("t128_manifest_sha256", "0" * 64, "T128_manifest_sha256_is_exact"),
        (
            "t128_recorded_current_sha256",
            "0" * 64,
            "T128_manifest_records_current_sha256",
        ),
        ("t256_manifest_sha256", "0" * 64, "T256_manifest_sha256_is_exact"),
        (
            "t256_recorded_current_sha256",
            "0" * 64,
            "T256_manifest_records_current_sha256",
        ),
        ("t64_other_source_locks_pass", False, "all_other_T64_source_locks_pass"),
        ("t128_source_lock_pass", False, "all_T128_source_locks_pass"),
        ("t256_source_lock_pass", False, "all_T256_source_locks_pass"),
        ("host_tests_pass", False, "directed_and_related_host_tests_pass"),
    ],
)
def test_exact_singleton_rejects_every_generalization(
    changed_field: str, changed_value: object, failed_check: str
) -> None:
    arguments = _exact_arguments()
    arguments[changed_field] = changed_value
    result = evaluate_exact_test_eof_compatibility(**arguments)
    assert result["pass"] is False
    assert result["accepted_label"] is None
    assert failed_check in result["failures"]


def test_whitespace_normalization_or_second_eof_lf_is_not_accepted() -> None:
    arguments = _exact_arguments()
    content = arguments["current_content"]
    assert isinstance(content, bytes)
    arguments["current_content"] = content + b"\n"
    result = evaluate_exact_test_eof_compatibility(**arguments)
    assert result["pass"] is False
    assert result["checks"]["current_content_ends_with_one_LF"] is False
    assert result["observed"]["whitespace_normalization_used"] is False


def test_compatibility_protocol_cannot_be_relaxed() -> None:
    with pytest.raises(ValueError, match="singleton"):
        replace(
            FROZEN_TEST_EOF_COMPATIBILITY_V06_1,
            relative_path="tests/paper2_m2/test_protocol_v02.py",
        ).checked()


def test_current_manifests_endorse_current_test_hash_and_path_is_git_clean() -> None:
    runner = _load_runner()
    protocol = FROZEN_TEST_EOF_COMPATIBILITY_V06_1
    assert runner._git_path_is_clean(protocol.relative_path)
    for label, manifest_relative in (
        ("T128", protocol.t128_manifest_relative_path),
        ("T256", protocol.t256_manifest_relative_path),
    ):
        manifest_path = PROJECT_ROOT / manifest_relative
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert runner.sha256_file(manifest_path) == getattr(
            protocol, f"{label.lower()}_manifest_sha256"
        )
        assert runner._manifest_recorded_hash(manifest, protocol.relative_path) == (
            protocol.current_sha256
        )


def test_effective_lock_accepts_exactly_one_T64_failure_and_no_other_lock_failure() -> None:
    runner = _load_runner()
    source_dirs = {
        label: (PROJECT_ROOT / specification["relative_path"]).resolve()
        for label, specification in runner.SOURCE_SPECS.items()
    }
    locks, summaries, structural, snapshots, compatibility = (
        runner._effective_source_locks(
            source_dirs=source_dirs,
            host_pytest_summary="directed: passed; related regression: passed",
        )
    )
    assert compatibility["pass"] is True
    assert locks["T64"]["v06_raw_failures"] == [
        "implementation_hash:tests/paper2_m2/test_protocol_v03.py"
    ]
    assert locks["T64"]["pass"] is True
    assert locks["T128"]["pass"] is True
    assert locks["T256"]["pass"] is True
    assert all(len(summaries[label]) == 54 for label in ("T64", "T128", "T256"))
    assert all(len(structural[label]) == 54 for label in ("T64", "T128", "T256"))
    assert all("hash_ledger.json" in snapshots[label] for label in snapshots)
