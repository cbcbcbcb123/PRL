from pathlib import Path
import unittest

from prl.storage import GIB, MIB, StoragePolicy, StorageSnapshot, evaluate_storage
from prl.workspace import find_workspace


ROOT = Path(__file__).resolve().parents[2]


class StoragePublicInterfaceTests(unittest.TestCase):
    def test_workspace_is_discovered_from_a_nested_existing_path(self):
        self.assertEqual(find_workspace(ROOT / "results"), ROOT)

    def test_default_stage_is_blocked_when_stop_reserve_would_cross_limit(self):
        snapshot = StorageSnapshot(
            workspace=str(ROOT),
            file_count=1,
            directory_count=0,
            logical_bytes=3 * GIB - 300 * MIB,
        )
        report = evaluate_storage(snapshot)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["level"], "preflight_rejected")
        self.assertFalse(report["can_start"])

    def test_incomplete_scan_never_grants_admission(self):
        snapshot = StorageSnapshot(
            workspace=str(ROOT),
            file_count=0,
            directory_count=0,
            logical_bytes=0,
            scan_errors=("fixture: AccessDenied",),
        )
        report = evaluate_storage(snapshot, policy=StoragePolicy())
        self.assertEqual(report["status"], "unknown")
        self.assertFalse(report["can_start"])


if __name__ == "__main__":
    unittest.main()
