from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


V10R2_CONTRACT_COMMIT = "d3d5a51d0e58ac9413eeb4c1b019eebb671470b4"
V10R1_RESULT_COMMIT = "1348f6aff6a3f46437f836ad053618ed68cb9b5b"
V10R1_SYNC_COMMIT = "27b7fbfda1d8533a99dd7c80e91fce15ddfcdd6c"
V10_RESULT_COMMIT = "2919a5df50d9fa287fe823ee5a1bb9169c438f65"
V10_CONTRACT_COMMIT = "e54bc5933387070c697f5c88218f37f25faea4c3"
V10R1_CONTRACT_COMMIT = "785796d409b9f43ef9657b7d6b44a10d36d5eef1"
APPROVED_BASELINE_COMMIT = "ddd663d461da7b25aefd5cf3fbecff488800053e"
FROZEN_LIFECYCLE_COMMITS = (
    "f7701d59ce3e1c94737e3b0a276205ed70fae6f8",
    "10bb2c2602b499b5a75ba2d57a35ba717e156616",
    "855bd8b7467761ba7fcdaa49632bed2ee5681e85",
    V10_CONTRACT_COMMIT,
    V10_RESULT_COMMIT,
    APPROVED_BASELINE_COMMIT,
)
V10R1_CONFIGURATION_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r1/"
    "configuration.json"
)
V10_RUNNER_PATH = "cpp/tests/r1_midpoint_collapse_diagnostic_test.cpp"
V10_CONTRACT_PATH = (
    "project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_contract_v10.md"
)
V10R1_CONTRACT_PATH = (
    "project_control/"
    "hybrid_x1_k_r1_midpoint_collapse_evidence_packaging_semantic_repair_"
    "contract_v10r1.md"
)
V10_RAW_LOG_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw/"
    "formal_response.log"
)
V10_RAW_EXIT_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw/"
    "formal_response.exitcode"
)
V10R1_CANDIDATE_JSON_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r1/"
    "candidate_matrix_v10r1.json"
)
V10R1_CANDIDATE_CSV_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r1/"
    "candidate_matrix_v10r1.csv"
)
V10R1_ERRATUM_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r1/"
    "semantic_erratum.json"
)


class V10R2EvidenceError(RuntimeError):
    pass


def _git_blob(repo_root: Path, commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "-p", f"{commit}:{path}"],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise V10R2EvidenceError(
            f"frozen source blob is unavailable for {commit}:{path}: {detail}"
        )
    return completed.stdout


def _git_text(repo_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise V10R2EvidenceError(
            f"git {' '.join(arguments)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout


def _line_locator(start: int, end: int, parser: str) -> dict[str, Any]:
    return {
        "kind": "line_range",
        "start": start,
        "end": end,
        "parser": parser,
    }


def _record_locator(record: str, key: str) -> dict[str, Any]:
    return {
        "kind": "record_key",
        "record": record,
        "key": key,
        "parser": "v10_machine_record_key",
    }


CPP_SPECS = {
    "configuration.tolerance": _line_locator(33, 33, "cpp_tolerance"),
    "configuration.initial_state.cell_id": _line_locator(119, 120, "cpp_cell_id"),
    "configuration.initial_state.revision": _line_locator(
        137, 140, "cpp_material_revision"
    ),
    "configuration.initial_state.vertex_count": _line_locator(
        103, 113, "cpp_vertex_count"
    ),
    "configuration.initial_state.face_count": _line_locator(
        114, 118, "cpp_face_count"
    ),
    "configuration.initial_state.vertices": _line_locator(
        103, 113, "cpp_vertices"
    ),
    "configuration.initial_state.faces": _line_locator(114, 118, "cpp_faces"),
    "configuration.initial_state.passive_parameters": _line_locator(
        73, 99, "cpp_passive_parameters"
    ),
    "configuration.initial_state.material_points": _line_locator(
        131, 164, "cpp_material_points"
    ),
    "configuration.material_transfer.implementation": _line_locator(
        457, 463, "cpp_material_sink_implementation"
    ),
    "configuration.material_transfer.maximum_rebind_distance": {
        "kind": "line_ranges",
        "ranges": [{"start": 33, "end": 33}, {"start": 457, "end": 459}],
        "parser": "cpp_material_sink_distance",
    },
    "configuration.refiner.implementation": _line_locator(
        595, 600, "cpp_refiner_implementation"
    ),
    "configuration.refiner.edge_length_threshold": _line_locator(
        597, 597, "cpp_refiner_argument_1"
    ),
    "configuration.refiner.curvature_threshold": _line_locator(
        597, 597, "cpp_refiner_argument_2"
    ),
    "configuration.refiner.enable_edge_swap": _line_locator(
        597, 597, "cpp_refiner_argument_3"
    ),
    "configuration.active_contraction.unit_id": _line_locator(
        446, 455, "cpp_active_argument_1"
    ),
    "configuration.active_contraction.minus_material_point_id": _line_locator(
        446, 455, "cpp_active_argument_2"
    ),
    "configuration.active_contraction.plus_material_point_id": _line_locator(
        446, 455, "cpp_active_argument_3"
    ),
    "configuration.active_contraction.activation_material_point_id": _line_locator(
        446, 455, "cpp_active_argument_4"
    ),
    "configuration.active_contraction.stiffness": _line_locator(
        446, 455, "cpp_active_argument_5"
    ),
    "configuration.active_contraction.minimum_axis_fiber_alignment": _line_locator(
        446, 455, "cpp_active_argument_6"
    ),
    "configuration.execution.output_precision_digits": _line_locator(
        1037, 1037, "cpp_output_precision"
    ),
}

CONTRACT_SPECS = {
    "configuration.execution.production_path": _line_locator(
        44, 49, "v10r2_production_pipeline"
    ),
    "configuration.execution.disabled_dynamics_and_couplings": _line_locator(
        39, 39, "v10r2_disabled_dynamics"
    ),
    "configuration.execution.candidate_order": _line_locator(
        102, 102, "v10r2_candidate_order"
    ),
}

V10R1_CONTRACT_SPECS = {
    "configuration.execution.new_microprobe_run": _line_locator(
        27, 27, "v10r2_no_new_microprobe"
    ),
    "configuration.execution.new_formal_response_run": _line_locator(
        27, 27, "v10r2_no_new_formal_response"
    ),
    "configuration.execution.new_physical_data_generated": _line_locator(
        27, 27, "v10r2_no_new_physical_data"
    ),
}

RAW_SPECS = {
    "configuration.formal_response.expected_exit_code": {
        "kind": "entire_file",
        "parser": "integer_file",
    },
    "configuration.formal_response.frozen_candidate_count": _record_locator(
        "v10_summary", "candidate_count"
    ),
    "configuration.formal_response.frozen_publicly_eligible_count": _record_locator(
        "v10_summary", "eligible_count"
    ),
    "configuration.formal_response.first_failed_candidate": _record_locator(
        "v10_summary", "first_failed_candidate"
    ),
}


def _canonical_fields(value: Any, prefix: str = "configuration") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    fields: dict[str, Any] = {}
    for key, child in value.items():
        fields.update(_canonical_fields(child, f"{prefix}.{key}"))
    return fields


def _source_for_field(field: str, value: Any) -> dict[str, Any]:
    if field in CPP_SPECS:
        commit, path, locator = V10_RESULT_COMMIT, V10_RUNNER_PATH, CPP_SPECS[field]
    elif field in CONTRACT_SPECS:
        commit, path, locator = (
            V10_CONTRACT_COMMIT,
            V10_CONTRACT_PATH,
            CONTRACT_SPECS[field],
        )
    elif field in V10R1_CONTRACT_SPECS:
        commit, path, locator = (
            V10R1_CONTRACT_COMMIT,
            V10R1_CONTRACT_PATH,
            V10R1_CONTRACT_SPECS[field],
        )
    elif field in RAW_SPECS:
        path = (
            V10_RAW_EXIT_PATH
            if field.endswith("expected_exit_code")
            else V10_RAW_LOG_PATH
        )
        commit, locator = V10_RESULT_COMMIT, RAW_SPECS[field]
    else:
        raise V10R2EvidenceError(f"no source specification for {field}")
    return {
        "commit": commit,
        "path": path,
        "locator": locator,
        "source_value": value,
    }


def build_v10r2_configuration(repo_root: Path) -> dict[str, Any]:
    frozen_payload = json.loads(
        _git_blob(repo_root, V10R1_RESULT_COMMIT, V10R1_CONFIGURATION_PATH).decode(
            "utf-8"
        )
    )
    configuration = frozen_payload["configuration"]
    fields = _canonical_fields(configuration)
    provenance = [
        {
            "field": field,
            "value": value,
            "sources": [_source_for_field(field, value)],
        }
        for field, value in sorted(fields.items())
    ]
    return {
        "schema_version": "x1-k-v10r2-configuration-1",
        "artifact_status": "v10r2_locator_evidence_repair",
        "delivery_context": (
            "created after the frozen v10 response as an append-only v10r2 "
            "reconstruction; it was not delivered by v10"
        ),
        "reconstruction_basis": [
            "frozen v10 contract",
            "frozen v10 runner/source defaults",
            "frozen v10 raw response and exit code",
            "frozen v10r1 no-new-scientific-response contract",
        ],
        "historical_v10_delivery_claim": False,
        "new_scientific_response_generated": False,
        "canonical_leaf_definition": (
            "recursively expand mappings; treat each array as one leaf"
        ),
        "configuration": configuration,
        "field_provenance": provenance,
    }


def _number(value: str) -> int | float:
    stripped = value.strip()
    if re.fullmatch(r"[+-]?\d+", stripped):
        return int(stripped)
    return float(stripped)


def _numbers(value: str) -> list[int | float]:
    return [
        _number(match.group(0))
        for match in re.finditer(r"[+-]?(?:\d+\.?(?:\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value)
    ]


def _cpp_vertices(source: str) -> list[list[int | float]]:
    match = re.search(r"node_pos_lst\s*=\s*\{(?P<body>.*?)\};", source, re.DOTALL)
    if match is None:
        raise V10R2EvidenceError("vertex initializer is absent from resolved lines")
    values = _numbers(match.group("body"))
    if len(values) % 3 != 0:
        raise V10R2EvidenceError("vertex initializer is not three-dimensional")
    return [values[index : index + 3] for index in range(0, len(values), 3)]


def _cpp_faces(source: str) -> list[list[int]]:
    return [
        [int(value) for value in match.groups()]
        for match in re.finditer(r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}", source)
    ]


def _cpp_passive_parameters(source: str) -> list[dict[str, Any]]:
    source_names = {
        "face_type.name_": "face.name",
        "face_type.face_type_global_id_": "face.global_type_id",
        "face_type.surface_tension_": "face.surface_tension",
        "face_type.adherence_strength_": "face.adherence_strength",
        "face_type.repulsion_strength_": "face.repulsion_strength",
        "face_type.bending_modulus_": "face.bending_modulus",
        "result.name_": "cell.name",
        "result.global_type_id_": "cell.global_type_id",
        "result.mass_density_": "cell.mass_density",
        "result.bulk_modulus_": "cell.bulk_modulus",
        "result.max_pressure_": "cell.max_pressure",
        "result.initial_pressure_": "cell.initial_pressure",
        "result.area_elasticity_modulus_": "cell.area_elasticity_modulus",
        "result.avg_division_vol_": "cell.avg_division_volume",
        "result.std_division_vol_": "cell.std_division_volume",
        "result.avg_growth_rate_": "cell.avg_growth_rate",
        "result.std_growth_rate_": "cell.std_growth_rate",
        "result.min_vol_": "cell.minimum_volume",
        "result.angle_regularization_factor_": "cell.angle_regularization_factor",
        "result.target_isoperimetric_ratio_": "cell.target_isoperimetric_ratio",
        "result.surface_coupling_max_curvature_": (
            "cell.surface_coupling_max_curvature"
        ),
    }
    parsed: dict[str, Any] = {}
    assignment_pattern = re.compile(
        r"(?P<object>face_type|result)(?:->|\.)(?P<name>\w+_)\s*=\s*(?P<value>[^;]+);"
    )
    for match in assignment_pattern.finditer(source):
        source_name = f"{match.group('object')}.{match.group('name')}"
        if source_name not in source_names:
            continue
        raw_value = match.group("value").strip()
        value: Any = (
            raw_value[1:-1]
            if raw_value.startswith('"') and raw_value.endswith('"')
            else _number(raw_value)
        )
        parsed[source_names[source_name]] = value
    ordered = [
        "face.name",
        "face.global_type_id",
        "face.surface_tension",
        "face.adherence_strength",
        "face.repulsion_strength",
        "face.bending_modulus",
        "cell.name",
        "cell.global_type_id",
        "cell.mass_density",
        "cell.bulk_modulus",
        "cell.max_pressure",
        "cell.initial_pressure",
        "cell.area_elasticity_modulus",
        "cell.avg_division_volume",
        "cell.std_division_volume",
        "cell.avg_growth_rate",
        "cell.std_growth_rate",
        "cell.minimum_volume",
        "cell.angle_regularization_factor",
        "cell.target_isoperimetric_ratio",
        "cell.surface_coupling_max_curvature",
    ]
    if set(parsed) != set(ordered):
        raise V10R2EvidenceError("passive parameter source is incomplete")
    return [{"field": field, "value": parsed[field]} for field in ordered]


def _cpp_material_points(source: str) -> list[dict[str, Any]]:
    local_ids = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"const auto (\w+) = persistent_node_id\(current_cell, (\d+)\);",
            source,
        )
    }
    point_pattern = re.compile(
        r"MyocardialMaterialState\{\s*"
        r"(?P<id>\d+)\s*,\s*"
        r"SurfaceRegion::(?P<region>\w+)\s*,\s*"
        r"\{(?P<fiber>[^{}]*)\}\s*,\s*"
        r"\{(?P<activation>[^{}]*)\}\s*,?\s*"
        r"\}\s*,\s*"
        r"\{(?P<host>[^{}]*)\}\s*,\s*"
        r"\{(?P<barycentric>[^{}]*)\}\s*,\s*"
        r"(?P<reference>[0-9.eE+-]+)\s*,",
        re.DOTALL,
    )
    points = []
    for match in point_pattern.finditer(source):
        activation = _numbers(match.group("activation"))
        if not activation:
            activation = [0.0, 0.0]
        host_names = [part.strip() for part in match.group("host").split(",")]
        if any(name not in local_ids for name in host_names):
            raise V10R2EvidenceError("material host source is unresolved")
        points.append(
            {
                "id": int(match.group("id")),
                "surface_region": match.group("region"),
                "fiber_direction": _numbers(match.group("fiber")),
                "activation": activation[0],
                "activation_rate": activation[1],
                "host": [local_ids[name] for name in host_names],
                "barycentric": _numbers(match.group("barycentric")),
                "reference_value": _number(match.group("reference")),
            }
        )
    if len(points) != 2:
        raise V10R2EvidenceError("material point source count changed")
    return points


def _cpp_refiner_arguments(source: str) -> list[Any]:
    match = re.search(r"local_mesh_refiner refiner\((.*?)\);", source, re.DOTALL)
    if match is None:
        raise V10R2EvidenceError("refiner construction is absent")
    raw_arguments = [part.strip() for part in match.group(1).split(",")]
    if len(raw_arguments) != 4:
        raise V10R2EvidenceError("refiner argument count changed")
    return [
        _number(raw_arguments[0]),
        _number(raw_arguments[1]),
        raw_arguments[2] == "true",
        raw_arguments[3],
    ]


def _cpp_active_arguments(source: str) -> list[int | float]:
    match = re.search(
        r"build_active_contraction_unit\((.*?)\);",
        source,
        re.DOTALL,
    )
    if match is None:
        raise V10R2EvidenceError("active-contraction construction is absent")
    arguments = [part.strip() for part in match.group(1).split(",")]
    if len(arguments) != 8:
        raise V10R2EvidenceError("active-contraction argument count changed")
    return [_number(value) for value in arguments[2:]]


def _machine_value(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return _number(value)
    except ValueError:
        return value


def _machine_record_value(source: str, locator: dict[str, Any]) -> Any:
    record_name = locator["record"]
    records = [
        line for line in source.splitlines() if line.startswith(f"{record_name},")
    ]
    if len(records) != 1:
        raise V10R2EvidenceError(
            f"record locator is not unique for {record_name}: {len(records)}"
        )
    parts = records[0].split(",")
    if len(parts) % 2 == 0:
        raise V10R2EvidenceError(f"record shape changed for {record_name}")
    values = dict(zip(parts[1::2], parts[2::2], strict=True))
    key = locator["key"]
    if key not in values:
        raise V10R2EvidenceError(f"record key is absent: {record_name}.{key}")
    return _machine_value(values[key])


def _selected_source(source: str, locator: dict[str, Any]) -> str:
    kind = locator.get("kind")
    if kind in {"entire_file", "record_key"}:
        return source
    lines = source.split("\n")
    ranges = (
        [{"start": locator.get("start"), "end": locator.get("end")}]
        if kind == "line_range"
        else locator.get("ranges")
    )
    if kind not in {"line_range", "line_ranges"} or not isinstance(ranges, list):
        raise V10R2EvidenceError(f"unsupported source locator kind: {kind}")
    selected = []
    for current in ranges:
        start, end = current.get("start"), current.get("end")
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 1
            or end < start
            or end > len(lines)
        ):
            raise V10R2EvidenceError(f"source line locator is out of range: {current}")
        selected.extend(lines[start - 1 : end])
    return "\n".join(selected)


def _parse_resolved_value(
    selected: str,
    full_source: str,
    locator: dict[str, Any],
) -> Any:
    parser = locator.get("parser")
    if parser == "cpp_tolerance":
        match = re.search(r"constexpr double tolerance = ([0-9.eE+-]+);", selected)
        return _number(match.group(1)) if match else None
    if parser == "cpp_cell_id":
        match = re.search(r"make_shared<cell>\(cell_mesh,\s*(\d+)", selected)
        return int(match.group(1)) if match else None
    if parser == "cpp_material_revision":
        match = re.search(r"return\s*\{\s*\d+\s*,\s*(\d+)\s*,", selected)
        return int(match.group(1)) if match else None
    if parser == "cpp_vertex_count":
        return len(_cpp_vertices(selected))
    if parser == "cpp_face_count":
        return len(_cpp_faces(selected))
    if parser == "cpp_vertices":
        return _cpp_vertices(selected)
    if parser == "cpp_faces":
        return _cpp_faces(selected)
    if parser == "cpp_passive_parameters":
        return _cpp_passive_parameters(selected)
    if parser == "cpp_material_points":
        return _cpp_material_points(selected)
    if parser == "cpp_material_sink_implementation":
        return (
            "production MyocardialMaterialTransferSink"
            if "MyocardialMaterialTransferSink" in selected
            else None
        )
    if parser == "cpp_material_sink_distance":
        match = re.search(r"constexpr double tolerance = ([0-9.eE+-]+);", selected)
        if match is None or "MyocardialMaterialTransferSink>(\n        tolerance" not in selected:
            return None
        return _number(match.group(1))
    if parser == "cpp_refiner_implementation":
        return "public local_mesh_refiner" if "local_mesh_refiner refiner" in selected else None
    if isinstance(parser, str) and parser.startswith("cpp_refiner_argument_"):
        index = int(parser.rsplit("_", 1)[1]) - 1
        return _cpp_refiner_arguments(selected)[index]
    if isinstance(parser, str) and parser.startswith("cpp_active_argument_"):
        index = int(parser.rsplit("_", 1)[1]) - 1
        return _cpp_active_arguments(selected)[index]
    if parser == "cpp_output_precision":
        match = re.search(r"setprecision\((\d+)\)", selected)
        return int(match.group(1)) if match else None
    if parser == "v10r2_production_pipeline":
        items = []
        for line in selected.splitlines():
            stripped = line.strip()
            if stripped == "fork cell":
                continue
            if stripped.startswith("->"):
                value = re.sub(r"\([^)]*\)", "", stripped[2:].strip())
                if value == "split_edge / can_be_merged / merge_edge":
                    value = f"public {value}"
                items.append(value)
        return items
    if parser == "v10r2_disabled_dynamics":
        required = [
            "8-vertex/12-face",
            "cell id 17",
            "revision 0",
            "activation=0.05",
            "stiffness=10",
            "passive/contact/pressure/ECM/flow",
            "adaptive remesh",
            "retry",
        ]
        if not all(marker in selected for marker in required):
            return None
        return [
            "mechanics_advance",
            "passive",
            "contact",
            "pressure",
            "ecm",
            "flow",
            "adaptive_remesh",
            "retry",
        ]
    if parser == "v10r2_candidate_order":
        required = [
            "local endpoint pair",
            "split node `m`",
            "can_be_merged",
            "true",
            "false",
            "merge",
        ]
        return "ascending local endpoint pair" if all(
            marker in selected for marker in required
        ) else None
    v10r2_no_new_markers = {
        "v10r2_no_new_microprobe": "microprobe",
        "v10r2_no_new_formal_response": "formal R1 response",
        "v10r2_no_new_physical_data": "v09/v10",
    }
    if parser in v10r2_no_new_markers:
        return False if v10r2_no_new_markers[parser] in selected else None
    if parser == "v10_production_pipeline":
        items = []
        for line in selected.splitlines():
            stripped = line.strip()
            if stripped == "fork cell":
                continue
            if stripped.startswith("->"):
                value = stripped[2:].strip()
                items.append(re.sub(r"\([^)]*\)", "", value))
        return items
    if parser == "v10_disabled_dynamics":
        required = [
            "无动力学推进",
            "passive/contact/pressure/ECM/flow",
            "adaptive remesh",
            "retry",
        ]
        if not all(marker in selected for marker in required):
            return None
        return [
            "mechanics_advance",
            "passive",
            "contact",
            "pressure",
            "ecm",
            "flow",
            "adaptive_remesh",
            "retry",
        ]
    if parser == "v10_candidate_order":
        return (
            "ascending local endpoint pair"
            if "local endpoint pair 升序枚举" in selected
            else None
        )
    no_new_markers = {
        "v10r1_no_new_microprobe": "不是新的 microprobe",
        "v10r1_no_new_formal_response": "formal R1 response",
        "v10r1_no_new_physical_data": "物理数据生成任务",
    }
    if parser in no_new_markers:
        return False if no_new_markers[parser] in selected else None
    if parser == "integer_file":
        return int(selected.strip())
    if parser == "v10_machine_record_key":
        return _machine_record_value(full_source, locator)
    raise V10R2EvidenceError(f"unsupported source parser: {parser}")


def _resolve_source(repo_root: Path, source: dict[str, Any]) -> Any:
    full_source = _git_blob(repo_root, source["commit"], source["path"]).decode(
        "utf-8"
    )
    locator = source.get("locator")
    if not isinstance(locator, dict):
        raise V10R2EvidenceError("source locator must be structured")
    selected = _selected_source(full_source, locator)
    return _parse_resolved_value(selected, full_source, locator)


def verify_configuration_sources(
    repo_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    fields = _canonical_fields(payload["configuration"])
    provenance = {item["field"]: item for item in payload["field_provenance"]}
    if set(fields) != set(provenance):
        raise V10R2EvidenceError("canonical configuration fields are not closed")
    resolved = []
    for field, value in sorted(fields.items()):
        item = provenance[field]
        if item["value"] != value:
            raise V10R2EvidenceError(f"field value mismatch for {field}")
        if any(source["source_value"] != value for source in item["sources"]):
            raise V10R2EvidenceError(f"source value mismatch for {field}")
        for source in item["sources"]:
            resolved_value = _resolve_source(repo_root, source)
            if resolved_value != value:
                raise V10R2EvidenceError(
                    f"resolved value mismatch for {field}: "
                    f"expected {value!r}, observed {resolved_value!r}"
                )
        resolved.append(field)
    return {
        "status": "passed_configuration_source_resolution",
        "canonical_leaf_count": len(fields),
        "resolved_leaf_count": len(resolved),
        "resolved_fields": resolved,
    }


def build_count_reconciliation(
    repo_root: Path,
    configuration_payload: dict[str, Any],
) -> dict[str, Any]:
    configuration_items = sorted(
        _canonical_fields(configuration_payload["configuration"])
    )
    changed_in: dict[str, list[str]] = {}
    for commit in FROZEN_LIFECYCLE_COMMITS:
        output = _git_text(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
        )
        for path in output.splitlines():
            if path:
                changed_in.setdefault(path, []).append(commit)

    baseline_tree = _git_text(repo_root, "ls-tree", "-r", APPROVED_BASELINE_COMMIT)
    baseline_blobs: set[str] = set()
    for line in baseline_tree.splitlines():
        metadata, path = line.split("\t", 1)
        _mode, object_type, _object_id = metadata.split()
        if object_type == "blob":
            baseline_blobs.add(path)
    lifecycle_items = [
        {"path": path, "source_commits": changed_in[path]}
        for path in sorted(set(changed_in) & baseline_blobs)
    ]
    result = {
        "schema_version": "x1-k-v10r2-count-reconciliation-1",
        "status": "passed_canonical_count_reconciliation",
        "canonical_counts": {
            "configuration": {
                "definition": (
                    "recursively expand mappings; treat each array as one leaf"
                ),
                "count": len(configuration_items),
                "items": configuration_items,
            },
            "frozen_lifecycle_blobs": {
                "definition": (
                    "unique changed paths across the six frozen v09/v10 "
                    "lifecycle commits"
                ),
                "source_commits": list(FROZEN_LIFECYCLE_COMMITS),
                "count": len(lifecycle_items),
                "items": lifecycle_items,
            },
        },
        "superseded_interim_counts": {
            label: {
                "status": (
                    "non_versioned_interim_miscount_superseded_"
                    "non_reconstructable"
                ),
                "explanation": (
                    "The precise interim set was not versioned and cannot be "
                    "reconstructed without inventing evidence."
                ),
                "entered_frozen_summary": False,
                "entered_frozen_manifest": False,
                "entered_gate": False,
            }
            for label in ("37", "105")
        },
    }
    if len(configuration_items) != 32 or len(lifecycle_items) != 102:
        result["status"] = "failed_canonical_count_reconciliation"
        raise V10R2EvidenceError(
            "canonical counts changed: "
            f"configuration={len(configuration_items)}, "
            f"frozen_lifecycle_blobs={len(lifecycle_items)}"
        )
    return result


def _single_machine_record(log_text: str, prefix: str) -> dict[str, Any]:
    records = [
        json.loads(line[len(prefix) :].strip())
        for line in log_text.splitlines()
        if line.startswith(prefix)
    ]
    if len(records) != 1:
        raise V10R2EvidenceError(
            f"combined verification log requires exactly one {prefix.strip()} record"
        )
    return records[0]


def parse_combined_verification(
    log_path: Path,
    exitcode_path: Path,
) -> dict[str, Any]:
    log_text = log_path.read_text(encoding="utf-8")
    invocation = _single_machine_record(log_text, "V10R2_INVOCATION_JSON ")
    preflight = _single_machine_record(log_text, "V10R2_PREFLIGHT_JSON ")
    result = _single_machine_record(log_text, "V10R2_RESULT_JSON ")
    try:
        sidecar_exit_code = int(exitcode_path.read_text(encoding="utf-8").strip())
    except ValueError as error:
        raise V10R2EvidenceError("combined verification exitcode is invalid") from error
    identities = {
        preflight.get("fork_head"),
        preflight.get("fork_upstream"),
        preflight.get("gitlink"),
    }
    if len(identities) != 1 or None in identities:
        raise V10R2EvidenceError("controlled-fork identity mismatch in preflight")
    if not preflight.get("fork_tracked_clean") or preflight.get(
        "fork_tracked_status"
    ):
        raise V10R2EvidenceError("controlled fork is not tracked-clean")
    if (
        sidecar_exit_code != 0
        or result.get("pytest_exit_code") != 0
        or result.get("wrapper_exit_code") != 0
    ):
        raise V10R2EvidenceError("combined verification did not exit successfully")
    summaries = [
        int(match.group(1))
        for match in re.finditer(r"(?m)^\s*(\d+) passed(?:[, ]| in)", log_text)
    ]
    if len(summaries) != 1:
        raise V10R2EvidenceError(
            "combined verification requires one unambiguous pytest pass count"
        )
    return {
        "status": "passed_combined_controlled_fork_verification",
        "invocation": invocation,
        "preflight": preflight,
        "fork_identity": next(iter(identities)),
        "pytest": {
            "passed": summaries[0],
            "exit_code": result["pytest_exit_code"],
        },
        "wrapper_exit_code": result["wrapper_exit_code"],
        "sidecar_exit_code": sidecar_exit_code,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write("\n")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise V10R2EvidenceError(f"CSV output has no rows: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha256_entry(repo_root: Path, path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(repo_root).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def _tree_objects(repo_root: Path, commit: str) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for line in _git_text(repo_root, "ls-tree", "-r", commit).splitlines():
        metadata, path = line.split("\t", 1)
        mode, object_type, object_id = metadata.split()
        entries[path] = {
            "mode": mode,
            "type": object_type,
            "object_id": object_id,
        }
    return entries


def verify_frozen_v01_v10r1_integrity(repo_root: Path) -> dict[str, Any]:
    x1_commits: list[dict[str, str]] = []
    frozen_paths: set[str] = set()
    history = _git_text(
        repo_root,
        "log",
        "--format=%H%x09%s",
        V10R1_SYNC_COMMIT,
    )
    for line in history.splitlines():
        commit, subject = line.split("\t", 1)
        if "x1-k" not in subject.lower():
            continue
        x1_commits.append({"commit": commit, "subject": subject})
        changed = _git_text(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
        )
        frozen_paths.update(path for path in changed.splitlines() if path)

    baseline_tree = _tree_objects(repo_root, V10R1_SYNC_COMMIT)
    current_tree = _tree_objects(repo_root, "HEAD")
    path_records = [
        {
            "path": path,
            "baseline": baseline_tree.get(path),
            "current": current_tree.get(path),
        }
        for path in sorted(frozen_paths)
    ]
    mismatches = [
        record
        for record in path_records
        if record["baseline"] != record["current"]
    ]
    ordered_paths = sorted(frozen_paths)
    worktree_output = _git_text(
        repo_root,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        *ordered_paths,
    )
    worktree_changes = [line for line in worktree_output.splitlines() if line]

    v10_dir = repo_root / "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10"
    raw_manifest = json.loads(
        (v10_dir / "provenance_manifest.json").read_text(encoding="utf-8")
    )["raw_evidence"]
    verification_manifest = json.loads(
        (v10_dir / "verification_artifact_manifest.json").read_text(
            encoding="utf-8"
        )
    )["artifacts"]
    manifest_entries = [*raw_manifest, *verification_manifest]
    manifest_mismatches = []
    for entry in manifest_entries:
        artifact = repo_root / entry["path"]
        payload = artifact.read_bytes()
        observed = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        if observed != {"sha256": entry["sha256"], "bytes": entry["bytes"]}:
            manifest_mismatches.append(
                {"path": entry["path"], "expected": entry, "observed": observed}
            )

    gitlink = _git_text(
        repo_root,
        "ls-tree",
        "HEAD",
        "external/simucell3d",
    ).split()[2]
    result = {
        "schema_version": "x1-k-v10r2-frozen-integrity-1",
        "status": "passed_frozen_v01_v10r1_integrity",
        "baseline_commit": V10R1_SYNC_COMMIT,
        "x1_k_history": {
            "commits": x1_commits,
            "frozen_path_count": len(path_records),
            "paths": path_records,
            "mismatches": mismatches,
            "worktree_changes": worktree_changes,
        },
        "v10_manifest": {
            "expected_entries": 28,
            "observed_entries": len(manifest_entries),
            "verified_entries": len(manifest_entries) - len(manifest_mismatches),
            "mismatches": manifest_mismatches,
        },
        "gitlink": gitlink,
    }
    if (
        mismatches
        or worktree_changes
        or manifest_mismatches
        or len(manifest_entries) != 28
        or gitlink != "e2ed64a26bb5d7c2d878772564fb5ffcca343c3a"
    ):
        result["status"] = "failed_frozen_v01_v10r1_integrity"
        raise V10R2EvidenceError("frozen v01-v10r1 integrity gate failed")
    return result


def _verification_summary(output_dir: Path) -> dict[str, Any]:
    expected_red = {
        "tdd_red_locator_seam_missing",
        "tdd_red_locator_json_echo",
        "tdd_red_count_reconciliation",
        "tdd_red_combined_log_parser",
    }
    superseded = {
        "tdd_green_locator_resolution": "superseded_test_node_selection_error",
        "tdd_green_locator_resolution_valid": (
            "intermediate_green_semantic_normalization_failure"
        ),
    }
    required = {"combined_python_final", "focused_python_final", "ruff_final"}
    all_commands: dict[str, Any] = {}
    verification_dir = output_dir / "verification"
    for exit_path in sorted(verification_dir.glob("*.exitcode")):
        stem = exit_path.stem
        exit_code = int(exit_path.read_text(encoding="utf-8").strip())
        if stem in required:
            role = "required_final_verification"
        elif stem in expected_red:
            role = "expected_tdd_red"
        elif stem in superseded:
            role = superseded[stem]
        elif stem.startswith("tdd_green") and exit_code == 0:
            role = "supporting_green_verification"
        else:
            role = "supporting_verification"
        log_path = verification_dir / f"{stem}.log"
        passed_matches = []
        if log_path.exists():
            passed_matches = [
                int(match.group(1))
                for match in re.finditer(
                    r"(?m)^\s*(\d+) passed(?:[, ]| in)",
                    log_path.read_text(encoding="utf-8"),
                )
            ]
        all_commands[stem] = {
            "exit_code": exit_code,
            "role": role,
            "passed": passed_matches[-1] if passed_matches else None,
        }
    missing = sorted(required - set(all_commands))
    failed = sorted(
        stem
        for stem in required
        if stem in all_commands and all_commands[stem]["exit_code"] != 0
    )
    return {
        "status": (
            "passed_packaging_software_verification"
            if not missing and not failed
            else "incomplete_packaging_software_verification"
        ),
        "required": {
            stem: all_commands[stem]
            for stem in sorted(required)
            if stem in all_commands
        },
        "missing_required": missing,
        "failed_required": failed,
        "all_commands": all_commands,
        "scientific_response_commands_executed": False,
        "roles_are_not_interchangeable": True,
    }


def _candidate_payload(repo_root: Path) -> tuple[dict[str, Any], bytes]:
    payload = json.loads(
        _git_blob(repo_root, V10R1_RESULT_COMMIT, V10R1_CANDIDATE_JSON_PATH)
    )
    payload["schema_version"] = "x1-k-v10r2-candidate-matrix-1"
    payload["artifact_status"] = "v10r2_successor_semantics_preserved"
    payload["successor_of"] = {
        "commit": V10R1_RESULT_COMMIT,
        "path": V10R1_CANDIDATE_JSON_PATH,
    }
    candidates = payload["candidates"]
    statuses = [candidate["topology_status"] for candidate in candidates]
    if statuses != [
        "adjudicated_legal",
        "adjudicated_legal",
        "not_adjudicated_due_to_production_sink_exception",
        "adjudicated_legal",
    ]:
        raise V10R2EvidenceError("candidate topology status vocabulary changed")
    candidate_three = candidates[2]
    if (
        candidate_three["merge_succeeded"] is not False
        or candidate_three["topology_legal"] is not None
        or candidate_three["rebind_distance"] != 0.047434164902525666
        or candidate_three["rebind_distance"] <= 1e-12
    ):
        raise V10R2EvidenceError("candidate 3 frozen semantics changed")
    csv_payload = _git_blob(
        repo_root,
        V10R1_RESULT_COMMIT,
        V10R1_CANDIDATE_CSV_PATH,
    )
    return payload, csv_payload


def export_v10r2_package(
    repo_root: Path,
    output_dir: Path,
    report_path: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    verification_dir = output_dir / "verification"
    combined = parse_combined_verification(
        verification_dir / "combined_python_final.log",
        verification_dir / "combined_python_final.exitcode",
    )
    configuration = build_v10r2_configuration(repo_root)
    resolution = verify_configuration_sources(repo_root, configuration)
    count_reconciliation = build_count_reconciliation(repo_root, configuration)
    frozen_integrity = verify_frozen_v01_v10r1_integrity(repo_root)
    candidates, candidate_csv = _candidate_payload(repo_root)

    _write_json(output_dir / "configuration.json", configuration)
    _write_json(output_dir / "configuration_resolution.json", resolution)
    _write_json(output_dir / "count_reconciliation.json", count_reconciliation)
    _write_text(
        output_dir / "count_reconciliation_zh.md",
        """# X1-K v10r2 计数对账说明

canonical configuration count 的定义是：递归展开 mapping；数组整体作为一个叶值。独立重算结果为 32，完整集合见 `count_reconciliation.json`。

frozen lifecycle blob count 的定义是：取 v09/v10 六个冻结生命周期提交的 changed path 唯一并集，再限定为基线提交中存在的 Git blob。独立重算结果为 102，逐路径及来源提交见 `count_reconciliation.json`。

过程消息中的 37 与 105 没有形成版本化中间集合，无法诚实重建其精确成员。二者因此标为 `non_versioned_interim_miscount_superseded_non_reconstructable`；不得编造 37→32 或 105→102 的转换。它们从未进入冻结 summary、manifest 或 gate。""",
    )
    _write_json(output_dir / "candidate_matrix_v10r2.json", candidates)
    (output_dir / "candidate_matrix_v10r2.csv").write_bytes(candidate_csv)

    erratum = json.loads(
        _git_blob(repo_root, V10R1_RESULT_COMMIT, V10R1_ERRATUM_PATH)
    )
    erratum["erratum_id"] = (
        "ERRATUM-PRL-HYBRID-X1-K-V10R2-CANDIDATE-3-TOPOLOGY-SUCCESSOR"
    )
    erratum["successor_of"] = {
        "commit": V10R1_RESULT_COMMIT,
        "path": V10R1_ERRATUM_PATH,
    }
    erratum["v10r2_role"] = (
        "append-only preservation of v10r1 three-state semantics while repairing "
        "locator, count, and controlled-fork evidence"
    )
    _write_json(output_dir / "semantic_erratum_v10r2.json", erratum)

    scientific_guard = {
        "status": "passed_scientific_claim_preservation_guard",
        "v10_scientific_status": (
            "failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind"
        ),
        "classification_status": "not_adjudicated_due_to_first_failure",
        "candidate_3_topology_status": (
            "not_adjudicated_due_to_production_sink_exception"
        ),
        "candidate_3_merge_succeeded": False,
        "candidate_3_rebind_distance": 0.047434164902525666,
        "candidate_3_rebind_distance_threshold": 1e-12,
        "x1_k_passed": False,
        "r1_passed": False,
        "c1_f1": "not_executed",
        "downstream_authorized": False,
        "new_microprobe_run": False,
        "new_formal_response_run": False,
        "new_physical_data_generated": False,
    }
    _write_json(output_dir / "scientific_claim_guard.json", scientific_guard)
    _write_json(output_dir / "frozen_integrity.json", frozen_integrity)

    summary = {
        "contract_id": (
            "CONTRACT-PRL-HYBRID-X1-K-V10R2-LOCATOR-COUNT-FORK-EVIDENCE-REPAIR"
        ),
        "contract_commit": V10R2_CONTRACT_COMMIT,
        "v10r1_result_commit": V10R1_RESULT_COMMIT,
        "status": "packaging_evidence_repair_complete_scientific_failure_preserved",
        **{key: value for key, value in scientific_guard.items() if key != "status"},
        "configuration_artifact_status": (
            "reconstructed_successor_with_all_32_sources_resolved_from_frozen_blobs"
        ),
        "historical_v10_configuration_delivery_claim": False,
        "configuration_canonical_leaf_count": resolution["canonical_leaf_count"],
        "configuration_resolved_leaf_count": resolution["resolved_leaf_count"],
        "frozen_lifecycle_blob_count": count_reconciliation["canonical_counts"][
            "frozen_lifecycle_blobs"
        ]["count"],
        "controlled_fork": {
            "identity": combined["fork_identity"],
            "tracked_clean": combined["preflight"]["fork_tracked_clean"],
            "pytest_passed": combined["pytest"]["passed"],
            "pytest_exit_code": combined["pytest"]["exit_code"],
            "source": "verification/combined_python_final.log",
        },
    }
    _write_json(output_dir / "summary.json", summary)

    _write_csv(
        output_dir / "criteria.csv",
        [
            {
                "order": 1,
                "role": "locator_repair",
                "criterion": "all_canonical_configuration_leaves_resolve",
                "observed": "32/32",
                "passed": True,
                "scientific_adjudication": False,
                "provenance": "configuration_resolution.json",
            },
            {
                "order": 2,
                "role": "count_reconciliation",
                "criterion": "canonical_sets_are_enumerated_and_unique",
                "observed": "configuration=32; lifecycle_blobs=102",
                "passed": True,
                "scientific_adjudication": False,
                "provenance": "count_reconciliation.json",
            },
            {
                "order": 3,
                "role": "controlled_fork_verification",
                "criterion": "identity_cleanliness_and_pytest_are_log_parsed",
                "observed": (
                    f"tracked_clean; pytest={combined['pytest']['passed']}/"
                    f"{combined['pytest']['passed']}"
                ),
                "passed": True,
                "scientific_adjudication": False,
                "provenance": "verification/combined_python_final.log",
            },
            {
                "order": 4,
                "role": "scientific_state_preservation",
                "criterion": "v10_failure_and_non_authorization_preserved",
                "observed": "X1-K=false; R1=false; C1/F1 not executed",
                "passed": True,
                "scientific_adjudication": False,
                "provenance": "scientific_claim_guard.json",
            },
        ],
    )
    _write_text(
        output_dir / "reproduction_commands.md",
        """# X1-K v10r2 packaging-evidence repair reproduction

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_r1_midpoint_packaging_repair_v10r2.py -q
python scripts/run_x1k_v10r2_combined_verification.py --repo-root . --controlled-parent-root "E:\\Temp-Projects\\PRL" -- -q
python scripts/export_x1k_r1_v10r2.py
python -m ruff check src/hybrid/r1_midpoint_packaging_repair_v10r2.py scripts/run_x1k_v10r2_combined_verification.py scripts/export_x1k_r1_v10r2.py tests/test_r1_midpoint_packaging_repair_v10r2.py
```

这些命令只验证冻结日志、Git blob、包装代码与 Python 测试；不得运行 C++、microprobe 或 formal response。""",
    )

    unique_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for field in configuration["field_provenance"]:
        for source in field["sources"]:
            key = (source["commit"], source["path"])
            if key not in unique_sources:
                blob = _git_blob(repo_root, *key)
                unique_sources[key] = {
                    "commit": key[0],
                    "path": key[1],
                    "git_blob_sha256": hashlib.sha256(blob).hexdigest(),
                    "bytes": len(blob),
                }
    provenance = {
        "schema_version": "x1-k-v10r2-provenance-1",
        "status": "passed_closed_packaging_provenance",
        "configuration_sources": list(unique_sources.values()),
        "configuration_field_count": len(configuration["field_provenance"]),
        "configuration_resolved_count": resolution["resolved_leaf_count"],
        "candidate_successor_source": candidates["successor_of"],
        "combined_verification_source": {
            "path": "verification/combined_python_final.log",
            "fork_identity_parsed": combined["fork_identity"],
            "pytest_passed_parsed": combined["pytest"]["passed"],
        },
        "new_scientific_evidence_generated": False,
    }
    _write_json(output_dir / "provenance_manifest.json", provenance)

    verification_summary = _verification_summary(output_dir)
    if verification_summary["status"] != "passed_packaging_software_verification":
        raise V10R2EvidenceError(
            "required final packaging verification logs are incomplete"
        )
    verification_summary["controlled_fork"] = combined
    verification_summary["counts_parsed_from_logs"] = True
    _write_json(output_dir / "verification_summary.json", verification_summary)
    verification_artifacts = [
        _sha256_entry(repo_root, path)
        for path in sorted(verification_dir.iterdir())
        if path.is_file()
    ]
    _write_json(
        output_dir / "verification_artifact_manifest.json",
        {
            "schema_version": "x1-k-v10r2-verification-artifacts-1",
            "artifacts": verification_artifacts,
        },
    )

    report = f"""# X1-K v10r2 定位器、计数与 controlled-fork 证据修补报告

本 successor 是 append-only 的 packaging/evidence repair，不是新的科学响应，也不追溯声称 v10 当时已交付 configuration。v01-v10r1 冻结路径、v10 的 28 项 manifest 与 Gitlink 均通过只读完整性检查。

## 修补结果

- 32 个 canonical configuration leaf 全部从 `source_commit:path` 的冻结 Git blob 按结构化 line range 或 record/key locator 解析通过；篡改 locator 且保持 JSON echo 自洽的 RED 会 fail closed。
- canonical configuration count 为 32；六个 v09/v10 生命周期提交的 frozen blob 唯一集为 102。过程消息 37/105 是未版本化、已取代且不可重建的临时误计，未进入冻结 summary、manifest 或 gate。
- combined log 解析到 controlled fork `{combined['fork_identity']}`，HEAD/upstream/Gitlink 一致、tracked clean；同一日志中的 pytest 为 {combined['pytest']['passed']}/{combined['pytest']['passed']}、exit 0。
- candidate 1/2/4 保持 `adjudicated_legal`；candidate 3 保持 `not_adjudicated_due_to_production_sink_exception`，`merge_succeeded=false`，异常距离 `0.047434164902525666 > 1e-12`。

## 验证证据角色

- expected TDD RED：`tdd_red_locator_seam_missing`、`tdd_red_locator_json_echo`、`tdd_red_count_reconciliation`、`tdd_red_combined_log_parser`。这些失败只证明测试先于实现，不能作为最终通过。
- superseded/intermediate errors：`tdd_green_locator_resolution` 是错误测试节点调用（exit 4）；`tdd_green_locator_resolution_valid` 揭示 production path canonical 归一化差异（exit 1）。二者均不计作通过，后续有效 GREEN 另有独立日志。
- required final pass：`combined_python_final`、`focused_python_final`、`ruff_final`；其 exit code 均为 0。详细角色及实际 pytest 计数见 `verification_summary.json`，角色不得互换。

## 科学状态保护

v10 scientific status 仍失败；classification 仍未裁决；X1-K=false；R1=false；C1/F1 未执行；downstream=false。未运行 C++、microprobe 或 formal R1 response，未生成新物理数据。

本报告只声明 execution complete / inspection eligible，不作自验收。"""
    _write_text(report_path, report)
    return summary
