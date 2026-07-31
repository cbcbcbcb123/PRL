"""Stage 0 v06 deterministic coarse/base/fine discretization family."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .contracts import assert_stage0_inputs, repository_root
from .geometry import load_reference_bundle, reference_arrays


FAMILY_ID = "DISCRETIZATION-FAMILY-PRL-ROUTE-H-STAGE0-V06"
CONTRACT_ID = "CONTRACT-PRL-ROUTE-H-STAGE0-V06"
GEOMETRY_SPEC_ID = "GEOMETRY-FAMILY-PRL-ROUTE-H-STAGE0-V06"
FAMILY_DIRECTORY = Path("data/route_h/stage0_v06_discretization_family")
CELL_ECM_MATERIALIZATION_GAP_CEILING = 0.075
CELL_CELL_MATERIALIZATION_GAP_CEILING = 0.15


@dataclass(frozen=True)
class DiscretizationLevel:
    name: str
    subdivision_level: int
    ecm_intervals: tuple[int, int, int]
    expected_cell_vertices: int
    expected_cell_faces: int
    expected_ecm_vertices: int
    expected_ecm_tetrahedra: int


LEVELS = (
    DiscretizationLevel("coarse", 1, (6, 4, 2), 42, 80, 105, 288),
    DiscretizationLevel("base", 2, (12, 8, 2), 162, 320, 351, 1152),
    DiscretizationLevel("fine", 3, (24, 16, 4), 642, 1280, 2125, 9216),
)
LEVEL_BY_NAME = {level.name: level for level in LEVELS}


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_array(array: np.ndarray) -> np.ndarray:
    if array.dtype.kind == "f":
        result = np.asarray(array, dtype="<f8", order="C").copy()
        result[result == 0.0] = 0.0
        if not np.all(np.isfinite(result)):
            raise ValueError("NaN and infinity are forbidden")
        return result
    return np.asarray(array, dtype="<i8", order="C")


def _seal_payload(records: list[dict[str, Any]], *, include_metadata: bool) -> bytes:
    selected = (
        records
        if include_metadata
        else [record for record in records if record["name"] != "metadata"]
    )
    return b"".join(
        f"{record['name']}\0{record['sha256']}\n".encode()
        for record in sorted(selected, key=lambda item: str(item["name"]))
    )


def _level_arrays(level: DiscretizationLevel) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    arrays, inherited_metadata = reference_arrays(
        level.subdivision_level,
        level.ecm_intervals,
        cell_ecm_maximum_gap=CELL_ECM_MATERIALIZATION_GAP_CEILING,
        cell_cell_maximum_gap=CELL_CELL_MATERIALIZATION_GAP_CEILING,
        vectorized_ray_search=level.name != "base",
        snap_reference_planes=level.name != "base",
    )
    metadata = dict(inherited_metadata)
    metadata.update(
        {
            "bundle_id": f"REFERENCE-BUNDLE-PRL-ROUTE-H-STAGE0-V06-{level.name.upper()}",
            "contract_id": CONTRACT_ID,
            "geometry_spec_id": GEOMETRY_SPEC_ID,
            "discretization_family_id": FAMILY_ID,
            "discretization_level": level.name,
            "surface_subdivision_level": level.subdivision_level,
            "ecm_intervals": list(level.ecm_intervals),
            "stage": 0,
            "purpose": "pre-Stage-2 sealed spatial discretization family",
            "cell_ECM_materialization_gap_ceiling": (
                CELL_ECM_MATERIALIZATION_GAP_CEILING
            ),
            "cell_cell_materialization_gap_ceiling": (
                CELL_CELL_MATERIALIZATION_GAP_CEILING
            ),
            "materialization_gap_ceiling_enters_mechanics": False,
            "reference_plane_snap": (
                "8*eps one-ULP-class snap of analytic cell extrema for coarse/fine"
                if level.name != "base"
                else "disabled to preserve byte-exact v05 base arrays"
            ),
            "active_mechanism_enabled": False,
            "full_patch_trajectory_enabled": False,
        }
    )
    return arrays, metadata


def regenerate_discretization_level(
    level_name: str,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if level_name not in LEVEL_BY_NAME:
        raise ValueError(f"unknown discretization level: {level_name}")
    return _level_arrays(LEVEL_BY_NAME[level_name])


def _materialize_level(
    level: DiscretizationLevel,
    destination: Path,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    arrays, metadata = _level_arrays(level)
    destination.mkdir(parents=True, exist_ok=True)
    metadata_bytes = _canonical_json_bytes(metadata)
    (destination / "metadata.json").write_bytes(metadata_bytes)
    file_records: list[dict[str, Any]] = [
        {
            "name": "metadata",
            "path": "metadata.json",
            "kind": "canonical_json",
            "sha256": hashlib.sha256(metadata_bytes).hexdigest().upper(),
        }
    ]
    for name in sorted(arrays):
        canonical = _canonical_array(arrays[name])
        filename = f"{name}.bin"
        payload = canonical.tobytes(order="C")
        (destination / filename).write_bytes(payload)
        file_records.append(
            {
                "name": name,
                "path": filename,
                "dtype": (
                    "float64_le" if canonical.dtype.kind == "f" else "int64_le"
                ),
                "shape": list(canonical.shape),
                "sha256": hashlib.sha256(payload).hexdigest().upper(),
            }
        )
    manifest: dict[str, Any] = {
        "bundle_id": metadata["bundle_id"],
        "status": "materialized_v06_candidate",
        "family_id": FAMILY_ID,
        "level": level.name,
        "canonical_serialization": {
            "integer": "signed little-endian int64 C-order",
            "floating": (
                "little-endian IEEE-754 binary64 C-order; negative zero canonicalized"
            ),
            "metadata": "UTF-8 canonical JSON",
            "hash": "SHA-256",
        },
        "files": file_records,
        "array_payload_sha256": hashlib.sha256(
            _seal_payload(file_records, include_metadata=False)
        )
        .hexdigest()
        .upper(),
        "bundle_sha256": hashlib.sha256(
            _seal_payload(file_records, include_metadata=True)
        )
        .hexdigest()
        .upper(),
    }
    (destination / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
    return manifest, arrays


def materialize_discretization_family(
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Materialize all three levels and enforce byte-exact reuse of the v05 base."""
    root = repository_root()
    assert_stage0_inputs(root)
    destination = root / FAMILY_DIRECTORY if output_dir is None else Path(output_dir)
    sealed_base, _ = load_reference_bundle()
    level_records: list[dict[str, Any]] = []
    for level in LEVELS:
        manifest, arrays = _materialize_level(level, destination / level.name)
        if level.name == "base":
            unequal = [
                name
                for name in sorted(sealed_base)
                if not np.array_equal(sealed_base[name], arrays[name])
            ]
            if unequal:
                raise RuntimeError(
                    "v06 base does not byte-reuse v05 arrays: " + ", ".join(unequal)
                )
        level_records.append(
            {
                "name": level.name,
                "subdivision_level": level.subdivision_level,
                "ecm_intervals": list(level.ecm_intervals),
                "manifest_path": f"{level.name}/manifest.json",
                "manifest_sha256": hashlib.sha256(
                    (destination / level.name / "manifest.json").read_bytes()
                )
                .hexdigest()
                .upper(),
                "array_payload_sha256": manifest["array_payload_sha256"],
                "bundle_sha256": manifest["bundle_sha256"],
            }
        )
    v05_manifest = json.loads(
        (
            root / "data/route_h/stage1_reference_bundle_v01/manifest.json"
        ).read_text(encoding="utf-8")
    )
    v05_array_payload = hashlib.sha256(
        _seal_payload(v05_manifest["files"], include_metadata=False)
    ).hexdigest().upper()
    base_record = next(record for record in level_records if record["name"] == "base")
    family_manifest: dict[str, Any] = {
        "family_id": FAMILY_ID,
        "status": "materialized_v06_candidate",
        "contract_id": CONTRACT_ID,
        "geometry_spec_id": GEOMETRY_SPEC_ID,
        "levels": level_records,
        "base_reuse": {
            "source_bundle": "REFERENCE-BUNDLE-PRL-ROUTE-H-STAGE1-V01",
            "source_bundle_sha256": v05_manifest["bundle_sha256"],
            "source_array_payload_sha256": v05_array_payload,
            "v06_base_array_payload_sha256": base_record["array_payload_sha256"],
            "all_22_arrays_byte_exact": (
                v05_array_payload == base_record["array_payload_sha256"]
            ),
        },
    }
    if not family_manifest["base_reuse"]["all_22_arrays_byte_exact"]:
        raise RuntimeError("v06 base array seal differs from the frozen v05 base")
    family_seal = b"".join(
        (
            f"{record['name']}\0{record['manifest_sha256']}\0"
            f"{record['bundle_sha256']}\n"
        ).encode()
        for record in level_records
    )
    family_manifest["family_sha256"] = (
        hashlib.sha256(family_seal).hexdigest().upper()
    )
    (destination / "manifest.json").write_bytes(
        _canonical_json_bytes(family_manifest)
    )
    return family_manifest


def load_discretization_level(
    level_name: str,
    family_dir: Path | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if level_name not in LEVEL_BY_NAME:
        raise ValueError(f"unknown discretization level: {level_name}")
    root = repository_root()
    location = (
        root / FAMILY_DIRECTORY / level_name
        if family_dir is None
        else Path(family_dir) / level_name
    )
    manifest = json.loads((location / "manifest.json").read_text(encoding="utf-8"))
    arrays: dict[str, np.ndarray] = {}
    verified: list[dict[str, Any]] = []
    for record in manifest["files"]:
        payload = (location / record["path"]).read_bytes()
        observed = hashlib.sha256(payload).hexdigest().upper()
        if observed != record["sha256"]:
            raise RuntimeError(f"v06 bundle hash mismatch: {level_name}/{record['path']}")
        verified.append(record)
        if "dtype" in record:
            dtype = "<f8" if record["dtype"] == "float64_le" else "<i8"
            arrays[record["name"]] = (
                np.frombuffer(payload, dtype=dtype)
                .reshape(record["shape"])
                .copy()
            )
    observed_bundle = hashlib.sha256(
        _seal_payload(verified, include_metadata=True)
    ).hexdigest().upper()
    if observed_bundle != manifest["bundle_sha256"]:
        raise RuntimeError(f"v06 bundle seal mismatch: {level_name}")
    metadata = json.loads((location / "metadata.json").read_text(encoding="utf-8"))
    return arrays, metadata
