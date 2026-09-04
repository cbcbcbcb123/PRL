"""Exact, single-file EOF compatibility policy for Paper 2 M2A v06.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any


@dataclass(frozen=True)
class TestEofCompatibilityProtocolV061:
    """Freeze the only source-lock exception authorized for the v06.1 retry."""

    schema: str = "paper2_m2a_v06_1_test_eof_compatibility_protocol"
    source_label: str = "T64"
    relative_path: str = "tests/paper2_m2/test_protocol_v03.py"
    t64_manifest_expected_sha256: str = (
        "4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f"
    )
    current_sha256: str = (
        "502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5"
    )
    current_bytes: int = 1681
    appended_byte_hex: str = "0a"
    transformed_bytes: int = 1682
    transformed_sha256: str = (
        "4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f"
    )
    t128_manifest_relative_path: str = (
        "results/paper2_m2/identity_2d_v04_t128_v02_20260903/run_manifest.json"
    )
    t128_manifest_sha256: str = (
        "302931097e9117d48b8f5a49325c9286711a291562fcee9eea997034be5fd16c"
    )
    t256_manifest_relative_path: str = (
        "results/paper2_m2/identity_2d_v05_t256_v02_20260904/run_manifest.json"
    )
    t256_manifest_sha256: str = (
        "fc65096b2c51fcaaba0c8d47405a3549a191be4d73a8cabf554019437884f123"
    )
    manifest_hash_container: str = "read_only_sha256_before"
    accepted_label: str = "ACCEPTED_TEST_EOF_FORMATTING_DELTA"

    def checked(self) -> "TestEofCompatibilityProtocolV061":
        expected = TestEofCompatibilityProtocolV061()
        if self != expected:
            raise ValueError("the exact v06.1 EOF compatibility singleton was changed")
        if self.appended_byte_hex != "0a":
            raise ValueError("v06.1 permits exactly one appended LF byte")
        if self.transformed_sha256 != self.t64_manifest_expected_sha256:
            raise ValueError("the v06.1 transformed hash must equal the T64 manifest hash")
        return self

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


FROZEN_TEST_EOF_COMPATIBILITY_V06_1 = TestEofCompatibilityProtocolV061().checked()


def evaluate_exact_test_eof_compatibility(
    *,
    source_label: str,
    relative_path: str,
    manifest_expected_sha256: str,
    current_content: bytes,
    git_clean: bool,
    t128_manifest_sha256: str,
    t128_recorded_current_sha256: str | None,
    t256_manifest_sha256: str,
    t256_recorded_current_sha256: str | None,
    t64_other_source_locks_pass: bool,
    t128_source_lock_pass: bool,
    t256_source_lock_pass: bool,
    host_tests_pass: bool,
    protocol: TestEofCompatibilityProtocolV061 = FROZEN_TEST_EOF_COMPATIBILITY_V06_1,
) -> dict[str, Any]:
    """Evaluate the byte-exact exception without changing the source file."""

    protocol.checked()
    current_sha256 = hashlib.sha256(current_content).hexdigest()
    transformed_content = current_content + b"\x0a"
    transformed_sha256 = hashlib.sha256(transformed_content).hexdigest()
    checks = {
        "source_label_is_exactly_T64": source_label == protocol.source_label,
        "relative_path_is_exact": relative_path == protocol.relative_path,
        "T64_manifest_expected_sha256_is_exact": (
            manifest_expected_sha256 == protocol.t64_manifest_expected_sha256
        ),
        "current_sha256_is_exact": current_sha256 == protocol.current_sha256,
        "current_byte_count_is_exact": len(current_content) == protocol.current_bytes,
        "current_content_ends_with_one_LF": current_content.endswith(b"\x0a")
        and not current_content.endswith(b"\x0a\x0a"),
        "one_appended_byte_is_exactly_LF": bytes.fromhex(protocol.appended_byte_hex)
        == b"\x0a",
        "append_one_LF_byte_count_is_exact": (
            len(transformed_content) == protocol.transformed_bytes
        ),
        "append_one_LF_sha256_is_exact": (
            transformed_sha256 == protocol.transformed_sha256
        ),
        "current_test_file_is_git_clean": git_clean,
        "T128_manifest_sha256_is_exact": (
            t128_manifest_sha256 == protocol.t128_manifest_sha256
        ),
        "T128_manifest_records_current_sha256": (
            t128_recorded_current_sha256 == protocol.current_sha256
        ),
        "T256_manifest_sha256_is_exact": (
            t256_manifest_sha256 == protocol.t256_manifest_sha256
        ),
        "T256_manifest_records_current_sha256": (
            t256_recorded_current_sha256 == protocol.current_sha256
        ),
        "all_other_T64_source_locks_pass": t64_other_source_locks_pass,
        "all_T128_source_locks_pass": t128_source_lock_pass,
        "all_T256_source_locks_pass": t256_source_lock_pass,
        "directed_and_related_host_tests_pass": host_tests_pass,
    }
    failures = [name for name, passed in checks.items() if not passed]
    accepted = not failures
    return {
        "schema": "paper2_m2a_v06_1_exact_test_eof_compatibility_evaluation",
        "policy": protocol.as_dict(),
        "observed": {
            "source_label": source_label,
            "relative_path": relative_path,
            "manifest_expected_sha256": manifest_expected_sha256,
            "current_sha256": current_sha256,
            "current_bytes": len(current_content),
            "current_tail_hex": current_content[-4:].hex(),
            "in_memory_transform": "append_exactly_one_0x0A_byte",
            "transformed_sha256": transformed_sha256,
            "transformed_bytes": len(transformed_content),
            "source_file_written": False,
            "whitespace_normalization_used": False,
        },
        "checks": checks,
        "failures": failures,
        "accepted_label": protocol.accepted_label if accepted else None,
        "pass": accepted,
    }
