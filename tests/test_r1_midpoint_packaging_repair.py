from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Any

from hybrid.r1_midpoint_packaging_repair import (
    export_v10r1_package,
    repair_candidate_topology_semantics,
    verify_frozen_v10_integrity,
)


ROOT = Path(__file__).resolve().parents[1]


def _configuration_fields(
    value: Any,
    prefix: str = "configuration",
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    flattened: dict[str, Any] = {}
    for key, child in value.items():
        flattened.update(_configuration_fields(child, f"{prefix}.{key}"))
    return flattened


def test_v10r1_export_reconstructs_configuration_with_closed_provenance(
    tmp_path: Path,
) -> None:
    export_v10r1_package(ROOT, tmp_path)
    configuration_path = tmp_path / "configuration.json"

    assert configuration_path.is_file(), "v10 omitted its contracted configuration"
    payload = json.loads(configuration_path.read_text(encoding="utf-8"))
    assert payload["artifact_status"] == (
        "reconstructed_after_v10_freeze_for_v10r1_packaging_repair"
    )
    assert payload["historical_v10_delivery_claim"] is False
    assert payload["new_scientific_response_generated"] is False

    fields = _configuration_fields(payload["configuration"])
    provenance = {
        item["field"]: item for item in payload["field_provenance"]
    }
    assert set(provenance) == set(fields)
    for field, value in fields.items():
        source = provenance[field]
        assert source["value"] == value
        assert len(source["sources"]) >= 1
        for citation in source["sources"]:
            assert len(citation["commit"]) == 40
            assert citation["path"]
            assert citation["locator"]
            assert citation["source_value"] == value

    assert fields["configuration.tolerance"] == 1.0e-12
    assert fields["configuration.initial_state.cell_id"] == 17
    assert fields["configuration.initial_state.revision"] == 0
    assert fields["configuration.initial_state.vertex_count"] == 8
    assert fields["configuration.initial_state.face_count"] == 12
    assert fields["configuration.material_transfer.maximum_rebind_distance"] == 1.0e-12
    assert fields["configuration.refiner.edge_length_threshold"] == 0.1
    assert fields["configuration.refiner.curvature_threshold"] == 10.0
    assert fields["configuration.refiner.enable_edge_swap"] is True
    assert fields["configuration.active_contraction.unit_id"] == 501
    assert fields["configuration.active_contraction.stiffness"] == 10.0
    assert fields["configuration.active_contraction.minimum_axis_fiber_alignment"] == 0.9
    assert fields["configuration.formal_response.expected_exit_code"] == 1
    assert fields["configuration.execution.new_microprobe_run"] is False
    assert fields["configuration.execution.new_formal_response_run"] is False


def test_v10r1_candidate_parser_uses_exception_aware_topology_states() -> None:
    repaired = repair_candidate_topology_semantics(
        ROOT
        / "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/"
        "candidate_matrix.csv"
    )

    assert [row["candidate_id"] for row in repaired] == [1, 2, 3, 4]
    assert [row["topology_status"] for row in repaired] == [
        "adjudicated_legal",
        "adjudicated_legal",
        "not_adjudicated_due_to_production_sink_exception",
        "adjudicated_legal",
    ]
    failed = repaired[2]
    assert failed["can_be_merged"] is True
    assert failed["merge_succeeded"] is False
    assert failed["topology_legal"] is None
    assert failed["exception"] == (
        "material point cannot be rebound within the configured distance: "
        "id=101; distance=0.047434164902525666"
    )
    assert failed["rebind_distance"] == 0.047434164902525666
    assert failed["rebind_distance_threshold"] == 1.0e-12
    assert failed["rebind_distance_exceeded"] is True
    assert all(row["topology_status"] != "adjudicated_illegal" for row in repaired)


def test_v10r1_export_emits_unambiguous_packaging_repair_artifacts(
    tmp_path: Path,
) -> None:
    exported = export_v10r1_package(ROOT, tmp_path)

    candidate_payload = json.loads(
        (tmp_path / "candidate_matrix_v10r1.json").read_text(encoding="utf-8")
    )
    candidate_rows = candidate_payload["candidates"]
    with (tmp_path / "candidate_matrix_v10r1.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        csv_rows = list(csv.DictReader(source))
    assert candidate_rows[2]["topology_status"] == (
        "not_adjudicated_due_to_production_sink_exception"
    )
    assert candidate_rows[2]["topology_legal"] is None
    assert csv_rows[2]["topology_legal"] == ""
    assert csv_rows[2]["merge_succeeded"] == "False"

    erratum = json.loads(
        (tmp_path / "semantic_erratum.json").read_text(encoding="utf-8")
    )
    assert erratum["original_serialization"]["topology_legal"] is False
    assert erratum["corrected_semantics"]["topology_status"] == (
        "not_adjudicated_due_to_production_sink_exception"
    )
    assert erratum["corrected_semantics"]["topology_legal"] is None
    assert erratum["preservation"]["frozen_v10_bytes_modified"] is False
    assert erratum["preservation"]["new_scientific_adjudication"] is False

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert exported == summary
    assert summary["status"] == (
        "packaging_repair_complete_scientific_failure_preserved"
    )
    assert summary["v10_scientific_status"] == (
        "failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind"
    )
    assert summary["classification_status"] == "not_adjudicated_due_to_first_failure"
    assert summary["x1_k_passed"] is False
    assert summary["r1_passed"] is False
    assert summary["c1_f1"] == "not_executed"
    assert summary["downstream_authorized"] is False
    assert summary["new_microprobe_run"] is False
    assert summary["new_formal_response_run"] is False
    assert summary["new_physical_data_generated"] is False

    assert (tmp_path / "criteria.csv").is_file()
    commands = (tmp_path / "reproduction_commands.md").read_text(encoding="utf-8")
    assert "export_x1k_r1_v10r1.py" in commands
    assert "无需也不得重跑 C++ 科学响应" in commands


def test_v10r1_integrity_gate_closes_frozen_git_and_28_manifest_entries() -> None:
    integrity = verify_frozen_v10_integrity(ROOT)

    assert integrity["status"] == "passed_frozen_v10_v09_integrity"
    assert integrity["baseline_commit"] == (
        "ddd663d461da7b25aefd5cf3fbecff488800053e"
    )
    assert integrity["frozen_git"]["mismatches"] == []
    assert integrity["frozen_git"]["worktree_changes"] == []
    assert integrity["frozen_git"]["files_verified"] > 28
    assert integrity["manifest_entries"] == {
        "expected": 28,
        "observed": 28,
        "verified": 28,
        "raw_evidence": 10,
        "verification_evidence": 18,
    }
    assert integrity["candidate_3_frozen_observation"] == {
        "merge_succeeded": False,
        "legacy_topology_legal_serialized": False,
        "rebind_distance": 0.047434164902525666,
        "rebind_distance_threshold": 1.0e-12,
        "rebind_distance_exceeded": True,
    }


def test_v10r1_manifest_closes_sources_and_generated_core_artifacts(
    tmp_path: Path,
) -> None:
    export_v10r1_package(ROOT, tmp_path)

    integrity = json.loads(
        (tmp_path / "frozen_integrity.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (tmp_path / "provenance_manifest.json").read_text(encoding="utf-8")
    )
    assert integrity["status"] == "passed_frozen_v10_v09_integrity"
    assert manifest["status"] == "passed_v10r1_provenance_closure"
    assert manifest["frozen_manifest_entries"] == {
        "expected": 28,
        "observed": 28,
        "verified": 28,
    }
    assert manifest["configuration_provenance"]["fields"] >= 30
    assert manifest["configuration_provenance"]["fields_closed"] == (
        manifest["configuration_provenance"]["fields"]
    )
    assert manifest["configuration_provenance"]["source_objects_verified"] >= 3
    generated = {item["path"]: item for item in manifest["generated_artifacts"]}
    assert set(generated) == {
        "candidate_matrix_v10r1.csv",
        "candidate_matrix_v10r1.json",
        "configuration.json",
        "criteria.csv",
        "frozen_integrity.json",
        "reproduction_commands.md",
        "semantic_erratum.json",
        "summary.json",
        "project_control/hybrid_x1_k_r1_midpoint_collapse_evidence_packaging_semantic_repair_report_v10r1.md",
    }
    for item in generated.values():
        assert len(item["sha256"]) == 64
        assert item["bytes"] > 0
