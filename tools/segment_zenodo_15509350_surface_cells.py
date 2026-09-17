"""Build auditable surface-aware cell-segmentation candidates for PRL F1-Seg-A.

The script reads three 72 hpf zebrafish samples directly from Zenodo record
15509350's ZIP archive.  Fish 4 is the sole development sample.  A bounded
12-configuration search is performed there, after which the selected
configuration is frozen.  Fish 3 and Fish 5 are processed exactly once as
holdouts.  The outputs are engineering candidates, not human-validated cell
instances or a mechanics result.

The two phases deliberately have separate commands:

* ``development`` writes Fish 4 patches and ``frozen_config.json``.
* ``holdout`` refuses to run twice, applies the frozen configuration to Fish
  3/5, and renders the final cross-fish audit package.

No archive member is extracted and no upstream MATLAB code is executed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import exposure, feature, filters, measure, morphology, segmentation


SCHEMA_VERSION = "prl.f1seg.surface_cell_candidate.v1"
ALGORITHM_VERSION = "surface-tangent-watershed-v1"
EXPECTED_PIXEL_UM = np.array([0.2071606, 0.2071606, 1.0], dtype=float)
PATCH_SIDE_UM = 48.0
PATCH_SPACING_UM = float(EXPECTED_PIXEL_UM[0])
DEPTHS_UM = np.array([0.0, 1.0, 2.0, 3.0], dtype=float)
QUICK_HALF_WIDTH_UM = 20.0
QUICK_SPACING_UM = 1.0
ROI_COUNT = 3
ROI_MIN_SEPARATION_UM = 50.0
MIN_AREA_UM2 = 20.0
MAX_AREA_UM2 = 600.0
MAX_ASPECT_RATIO = 8.0
RESULT_CAP_BYTES = 64 * 1024 * 1024

SAMPLES = {
    "fish3": {
        "fish_number": 3,
        "role": "frozen_holdout",
        "prefix": "Data/Zebrafish/Fish_72hpf_3/",
    },
    "fish4": {
        "fish_number": 4,
        "role": "development",
        "prefix": "Data/Zebrafish/Fish_72hpf_4_Fig4-5/",
    },
    "fish5": {
        "fish_number": 5,
        "role": "frozen_holdout",
        "prefix": "Data/Zebrafish/Fish_72hpf_5/",
    },
}


@dataclass
class SampleData:
    sample_id: str
    role: str
    prefix: str
    orientation: np.ndarray
    boundary_mask: np.ndarray
    full_mask: np.ndarray
    xyz_um: np.ndarray
    normals: np.ndarray
    pixel_um: np.ndarray
    directors: np.ndarray
    local_order: np.ndarray


@dataclass
class PatchData:
    sample_id: str
    roi_id: str
    surface_index: int
    center_um: np.ndarray
    outward_normal: np.ndarray
    inward_normal: np.ndarray
    e1: np.ndarray
    e2: np.ndarray
    u_um: np.ndarray
    v_um: np.ndarray
    raw_signal: np.ndarray
    tissue_mask: np.ndarray
    coordinate_valid: np.ndarray
    inward_minus_occupancy: float
    inward_plus_occupancy: float
    quick_quality_score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("development", "holdout"), required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def read_hdf5_member(
    archive: zipfile.ZipFile, member_name: str
) -> tuple[io.BytesIO, h5py.File]:
    memory_file = io.BytesIO(archive.read(member_name))
    return memory_file, h5py.File(memory_file, "r")


def read_tiff_member(archive: zipfile.ZipFile, member_name: str) -> np.ndarray:
    with tifffile.TiffFile(io.BytesIO(archive.read(member_name))) as image_file:
        return image_file.asarray()


def load_sample(archive_path: Path, sample_id: str) -> SampleData:
    spec = SAMPLES[sample_id]
    prefix = str(spec["prefix"])
    required = (
        "Orientation_Ch.tif",
        "Mask_Boundary.tif",
        "Mask_Full.tif",
        "SurfacePoints.mat",
        "Analysis_Coarse_Grained_Nematic.mat",
    )
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        missing = [name for name in required if prefix + name not in names]
        if missing:
            raise RuntimeError(f"{sample_id}: missing archive members {missing}")

        orientation = read_tiff_member(archive, prefix + "Orientation_Ch.tif")
        boundary_mask = np.asarray(
            read_tiff_member(archive, prefix + "Mask_Boundary.tif") > 0,
            dtype=np.uint8,
        )
        full_mask = np.asarray(
            read_tiff_member(archive, prefix + "Mask_Full.tif") > 0,
            dtype=np.uint8,
        )

        point_buffer, point_file = read_hdf5_member(
            archive, prefix + "SurfacePoints.mat"
        )
        try:
            xyz_um = np.asarray(point_file["SurfacePoints/xyz"][()], dtype=float)
            normals = np.asarray(
                point_file["SurfacePoints/xyzNormal"][()], dtype=float
            )
            pixel_um = np.asarray(
                point_file["SurfacePoints/Pixel"][()], dtype=float
            ).ravel()
        finally:
            point_file.close()
            point_buffer.close()

        nematic_buffer, nematic_file = read_hdf5_member(
            archive, prefix + "Analysis_Coarse_Grained_Nematic.mat"
        )
        try:
            directors = np.asarray(
                nematic_file["CoarseGrainedNematic/Nematic_Director"][()],
                dtype=float,
            )
            local_order = np.asarray(
                nematic_file["CoarseGrainedNematic/Local_Order"][()], dtype=float
            ).ravel()
        finally:
            nematic_file.close()
            nematic_buffer.close()

    if orientation.ndim != 3 or orientation.shape != boundary_mask.shape:
        raise RuntimeError(f"{sample_id}: incompatible TIFF shapes")
    if orientation.shape != full_mask.shape:
        raise RuntimeError(f"{sample_id}: full-mask shape mismatch")
    if xyz_um.shape != normals.shape or xyz_um.shape[0] != 3:
        raise RuntimeError(f"{sample_id}: incompatible surface arrays")
    if directors.shape != xyz_um.shape or local_order.size != xyz_um.shape[1]:
        raise RuntimeError(f"{sample_id}: incompatible nematic arrays")
    if not np.allclose(pixel_um, EXPECTED_PIXEL_UM, rtol=0, atol=1e-7):
        raise RuntimeError(f"{sample_id}: unexpected physical scale {pixel_um}")

    normal_norms = np.linalg.norm(normals, axis=0)
    if np.any(~np.isfinite(normal_norms)) or np.any(normal_norms < 0.99):
        raise RuntimeError(f"{sample_id}: invalid surface normals")
    normals = normals / normal_norms
    return SampleData(
        sample_id=sample_id,
        role=str(spec["role"]),
        prefix=prefix,
        orientation=orientation,
        boundary_mask=boundary_mask,
        full_mask=full_mask,
        xyz_um=xyz_um,
        normals=normals,
        pixel_um=pixel_um,
        directors=directors,
        local_order=local_order,
    )


def tangent_basis(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    reference_axes = np.eye(3)
    reference = reference_axes[int(np.argmin(np.abs(reference_axes @ normal)))]
    e1 = np.cross(normal, reference)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(normal, e1)
    e2 /= np.linalg.norm(e2)
    return e1, e2


def xyz_to_zyx(xyz_um: np.ndarray, pixel_um: np.ndarray) -> np.ndarray:
    return np.vstack(
        (
            xyz_um[2] / pixel_um[2],
            xyz_um[1] / pixel_um[1],
            xyz_um[0] / pixel_um[0],
        )
    )


def occupancy_along_normal(
    sample: SampleData, center_um: np.ndarray, normal: np.ndarray, sign: float
) -> float:
    probe_depths = np.array([1.0, 2.0, 3.0], dtype=float)
    xyz = center_um[:, None] + sign * normal[:, None] * probe_depths[None, :]
    coordinates = xyz_to_zyx(xyz, sample.pixel_um)
    values = ndimage.map_coordinates(
        sample.full_mask,
        coordinates,
        order=0,
        mode="constant",
        cval=0,
        prefilter=False,
    )
    return float(np.mean(values > 0))


def patch_axis(half_width_um: float, spacing_um: float) -> np.ndarray:
    sample_count = int(round((2.0 * half_width_um) / spacing_um)) + 1
    return np.linspace(-half_width_um, half_width_um, sample_count, dtype=float)


def sample_tangent_patch(
    sample: SampleData,
    surface_index: int,
    half_width_um: float,
    spacing_um: float,
    quick_quality_score: float,
    roi_id: str,
) -> PatchData:
    center_um = sample.xyz_um[:, surface_index].copy()
    outward = sample.normals[:, surface_index].copy()
    e1, e2 = tangent_basis(outward)
    minus_occupancy = occupancy_along_normal(sample, center_um, outward, -1.0)
    plus_occupancy = occupancy_along_normal(sample, center_um, outward, +1.0)
    inward = outward if plus_occupancy > minus_occupancy else -outward

    u_um = patch_axis(half_width_um, spacing_um)
    v_um = patch_axis(half_width_um, spacing_um)
    uu, vv = np.meshgrid(u_um, v_um, indexing="xy")
    plane = (
        center_um[:, None, None]
        + e1[:, None, None] * uu[None, :, :]
        + e2[:, None, None] * vv[None, :, :]
    )

    sampled_signal: list[np.ndarray] = []
    sampled_tissue: list[np.ndarray] = []
    sampled_valid: list[np.ndarray] = []
    volume_shape = np.asarray(sample.orientation.shape, dtype=float)
    for depth_um in DEPTHS_UM:
        xyz = plane + inward[:, None, None] * depth_um
        coordinates = xyz_to_zyx(xyz.reshape(3, -1), sample.pixel_um)
        valid = np.all(
            (coordinates >= 0.0) & (coordinates <= (volume_shape[:, None] - 1.0)),
            axis=0,
        ).reshape(uu.shape)
        orientation_values = ndimage.map_coordinates(
            sample.orientation,
            coordinates,
            order=1,
            mode="constant",
            cval=255,
            prefilter=False,
        ).reshape(uu.shape)
        boundary_values = ndimage.map_coordinates(
            sample.boundary_mask,
            coordinates,
            order=0,
            mode="constant",
            cval=0,
            prefilter=False,
        ).reshape(uu.shape)
        sampled_signal.append(255.0 - orientation_values.astype(np.float32))
        sampled_tissue.append(boundary_values > 0)
        sampled_valid.append(valid)

    raw_signal = np.max(np.stack(sampled_signal, axis=0), axis=0)
    tissue_mask = np.any(np.stack(sampled_tissue, axis=0), axis=0)
    coordinate_valid = np.all(np.stack(sampled_valid, axis=0), axis=0)
    tissue_mask &= coordinate_valid
    raw_signal[~coordinate_valid] = 0.0
    return PatchData(
        sample_id=sample.sample_id,
        roi_id=roi_id,
        surface_index=surface_index,
        center_um=center_um,
        outward_normal=outward,
        inward_normal=inward,
        e1=e1,
        e2=e2,
        u_um=u_um,
        v_um=v_um,
        raw_signal=raw_signal,
        tissue_mask=tissue_mask,
        coordinate_valid=coordinate_valid,
        inward_minus_occupancy=minus_occupancy,
        inward_plus_occupancy=plus_occupancy,
        quick_quality_score=quick_quality_score,
    )


def patch_quality(patch: PatchData) -> tuple[float, dict[str, float]]:
    tissue = patch.tissue_mask
    coverage = float(np.mean(tissue))
    valid_fraction = float(np.mean(patch.coordinate_valid))
    if np.count_nonzero(tissue) < 100:
        contrast = 0.0
        gradient_support = 0.0
    else:
        values = patch.raw_signal[tissue]
        p10, p90 = np.percentile(values, (10.0, 90.0))
        contrast = float((p90 - p10) / 255.0)
        gradient = filters.sobel(patch.raw_signal / 255.0)
        gradient_support = float(np.percentile(gradient[tissue], 80.0))
    inward_margin = abs(patch.inward_minus_occupancy - patch.inward_plus_occupancy)
    score = (
        2.0 * coverage
        + valid_fraction
        + 1.5 * contrast
        + gradient_support
        + 0.25 * inward_margin
    )
    metrics = {
        "coverage": coverage,
        "valid_fraction": valid_fraction,
        "contrast_10_90": contrast,
        "gradient_p80": gradient_support,
        "inward_occupancy_margin": float(inward_margin),
        "score": float(score),
    }
    return float(score), metrics


def select_roi_indices(sample: SampleData) -> tuple[list[int], list[dict[str, Any]]]:
    scored: list[tuple[float, int, dict[str, float]]] = []
    for surface_index in range(sample.xyz_um.shape[1]):
        patch = sample_tangent_patch(
            sample=sample,
            surface_index=surface_index,
            half_width_um=QUICK_HALF_WIDTH_UM,
            spacing_um=QUICK_SPACING_UM,
            quick_quality_score=0.0,
            roi_id="quick",
        )
        score, metrics = patch_quality(patch)
        scored.append((score, surface_index, metrics))

    scored.sort(key=lambda item: (-item[0], item[1]))
    selected: list[int] = []
    separation_used = ROI_MIN_SEPARATION_UM
    for minimum_separation in (ROI_MIN_SEPARATION_UM, 40.0, 30.0):
        selected = []
        for _, surface_index, _ in scored:
            center = sample.xyz_um[:, surface_index]
            if all(
                np.linalg.norm(center - sample.xyz_um[:, existing])
                >= minimum_separation
                for existing in selected
            ):
                selected.append(surface_index)
                if len(selected) == ROI_COUNT:
                    break
        if len(selected) == ROI_COUNT:
            separation_used = minimum_separation
            break
    if len(selected) != ROI_COUNT:
        raise RuntimeError(f"{sample.sample_id}: unable to select {ROI_COUNT} ROIs")

    ranking_records: list[dict[str, Any]] = []
    rank_by_index = {
        surface_index: (rank + 1, score, metrics)
        for rank, (score, surface_index, metrics) in enumerate(scored)
    }
    for selection_order, surface_index in enumerate(selected, start=1):
        rank, score, metrics = rank_by_index[surface_index]
        ranking_records.append(
            {
                "sample_id": sample.sample_id,
                "selection_order": selection_order,
                "surface_index": surface_index,
                "quality_rank": rank,
                "minimum_separation_um": separation_used,
                "quick_quality_score": score,
                **metrics,
            }
        )
    return selected, ranking_records


def robust_unit_interval(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = image[mask]
    if values.size == 0:
        return np.zeros_like(image, dtype=np.float32)
    lower, upper = np.percentile(values, (2.0, 99.0))
    if upper <= lower:
        upper = lower + 1.0
    normalized = np.clip((image.astype(np.float32) - lower) / (upper - lower), 0, 1)
    normalized[~mask] = 0.0
    return normalized


def enhance_membranes(
    raw_signal: np.ndarray, tissue_mask: np.ndarray, ridge_sigma_um: float
) -> np.ndarray:
    normalized = robust_unit_interval(raw_signal, tissue_mask)
    equalized = exposure.equalize_adapthist(
        normalized, kernel_size=32, clip_limit=0.015, nbins=256
    ).astype(np.float32)
    equalized[~tissue_mask] = 0.0
    sigma_px = ridge_sigma_um / PATCH_SPACING_UM
    ridge = filters.sato(
        equalized,
        sigmas=(max(1.0, sigma_px * 0.75), sigma_px, sigma_px * 1.25),
        black_ridges=False,
        mode="reflect",
    ).astype(np.float32)
    ridge = robust_unit_interval(ridge, tissue_mask)
    response = 0.55 * equalized + 0.45 * ridge
    response = filters.gaussian(response, sigma=0.45, preserve_range=True)
    response = robust_unit_interval(response, tissue_mask)
    return response.astype(np.float32)


def axial_angle_degrees(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    norm_a = float(np.linalg.norm(vector_a))
    norm_b = float(np.linalg.norm(vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return float("nan")
    cosine = float(np.clip(abs(np.dot(vector_a / norm_a, vector_b / norm_b)), 0, 1))
    return float(np.degrees(np.arccos(cosine)))


def segment_patch(
    patch: PatchData,
    sample: SampleData,
    config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, float]]:
    tissue = patch.tissue_mask.copy()
    response = enhance_membranes(
        patch.raw_signal, tissue, float(config["ridge_sigma_um"])
    )
    response_values = response[tissue]
    threshold = float(
        np.quantile(response_values, float(config["membrane_quantile"]))
    )
    membrane = tissue & (response >= threshold)
    membrane = morphology.remove_small_objects(membrane, min_size=3)
    membrane = morphology.binary_closing(membrane, morphology.disk(1))
    membrane = morphology.binary_dilation(membrane, morphology.disk(1))
    interior = tissue & ~membrane
    distance_um = ndimage.distance_transform_edt(interior) * PATCH_SPACING_UM
    minimum_distance_px = max(
        2, int(round(float(config["seed_min_distance_um"]) / PATCH_SPACING_UM))
    )
    peak_coordinates = feature.peak_local_max(
        distance_um,
        min_distance=minimum_distance_px,
        threshold_abs=0.8,
        exclude_border=False,
        labels=interior.astype(np.uint8),
    )
    markers = np.zeros(tissue.shape, dtype=np.int32)
    if peak_coordinates.size:
        markers[tuple(peak_coordinates.T)] = np.arange(
            1, peak_coordinates.shape[0] + 1, dtype=np.int32
        )
    if markers.max() == 0:
        labels = np.zeros(tissue.shape, dtype=np.int32)
    else:
        distance_scale = distance_um / max(float(distance_um.max()), 1e-6)
        elevation = response - 0.12 * distance_scale
        labels = segmentation.watershed(elevation, markers=markers, mask=tissue)
        labels = labels.astype(np.int32, copy=False)

    tree = cKDTree(sample.xyz_um.T)
    records: list[dict[str, Any]] = []
    kept_labels: list[int] = []
    response_boundaries = segmentation.find_boundaries(labels, mode="inner")
    boundary_values = response[response_boundaries & tissue]
    interior_values = response[(labels > 0) & ~response_boundaries]
    boundary_support = (
        float(np.mean(boundary_values) - np.mean(interior_values))
        if boundary_values.size and interior_values.size
        else float("nan")
    )

    for region in measure.regionprops(labels):
        candidate_mask = labels == region.label
        expanded = morphology.binary_dilation(candidate_mask, morphology.disk(1))
        touches_tissue_edge = bool(np.any(expanded & ~tissue))
        min_row, min_col, max_row, max_col = region.bbox
        touches_patch_edge = bool(
            min_row == 0
            or min_col == 0
            or max_row == labels.shape[0]
            or max_col == labels.shape[1]
        )
        area_um2 = float(region.area * PATCH_SPACING_UM**2)
        major_um = float(region.major_axis_length * PATCH_SPACING_UM)
        minor_um = float(region.minor_axis_length * PATCH_SPACING_UM)
        aspect_ratio = major_um / minor_um if minor_um > 0 else float("inf")

        coordinates = region.coords.astype(float)
        centered = coordinates - np.mean(coordinates, axis=0, keepdims=True)
        if coordinates.shape[0] >= 3:
            covariance = np.cov(
                np.column_stack((centered[:, 1], centered[:, 0])), rowvar=False
            )
            eigenvalues, eigenvectors = np.linalg.eigh(covariance)
            major_uv = eigenvectors[:, int(np.argmax(eigenvalues))]
        else:
            major_uv = np.array([1.0, 0.0], dtype=float)
        major_xyz = patch.e1 * major_uv[0] + patch.e2 * major_uv[1]

        centroid_row, centroid_col = region.centroid
        centroid_u = float(
            np.interp(centroid_col, np.arange(patch.u_um.size), patch.u_um)
        )
        centroid_v = float(
            np.interp(centroid_row, np.arange(patch.v_um.size), patch.v_um)
        )
        centroid_xyz = (
            patch.center_um + patch.e1 * centroid_u + patch.e2 * centroid_v
        )
        nearest_distance, nearest_index = tree.query(centroid_xyz, k=1)
        author_director = sample.directors[:, int(nearest_index)]
        author_tangent = author_director - np.dot(
            author_director, patch.inward_normal
        ) * patch.inward_normal
        author_uv = np.array(
            [np.dot(author_tangent, patch.e1), np.dot(author_tangent, patch.e2)]
        )
        angle_degrees = axial_angle_degrees(major_uv, author_uv)

        reasons: list[str] = []
        if touches_patch_edge or touches_tissue_edge:
            reasons.append("edge_contact")
        if not (MIN_AREA_UM2 <= area_um2 <= MAX_AREA_UM2):
            reasons.append("area_out_of_range")
        if not np.isfinite(aspect_ratio) or aspect_ratio > MAX_ASPECT_RATIO:
            reasons.append("aspect_out_of_range")
        keep = not reasons
        if keep:
            kept_labels.append(int(region.label))
        records.append(
            {
                "sample_id": sample.sample_id,
                "role": sample.role,
                "roi_id": patch.roi_id,
                "surface_index": patch.surface_index,
                "candidate_label": int(region.label),
                "keep": keep,
                "exclusion_reasons": ";".join(reasons),
                "centroid_u_um": centroid_u,
                "centroid_v_um": centroid_v,
                "centroid_x_um": float(centroid_xyz[0]),
                "centroid_y_um": float(centroid_xyz[1]),
                "centroid_z_um": float(centroid_xyz[2]),
                "area_um2": area_um2,
                "perimeter_um": float(
                    measure.perimeter(candidate_mask, neighborhood=8)
                    * PATCH_SPACING_UM
                ),
                "major_axis_um": major_um,
                "minor_axis_um": minor_um,
                "aspect_ratio": float(aspect_ratio),
                "candidate_axis_u": float(major_uv[0]),
                "candidate_axis_v": float(major_uv[1]),
                "nearest_author_surface_index": int(nearest_index),
                "nearest_author_surface_distance_um": float(nearest_distance),
                "nearest_author_local_order": float(sample.local_order[nearest_index]),
                "candidate_author_axial_angle_deg": angle_degrees,
                "touches_patch_edge": touches_patch_edge,
                "touches_tissue_edge": touches_tissue_edge,
            }
        )

    kept_label_image = np.where(np.isin(labels, kept_labels), labels, 0).astype(
        np.int32
    )
    total_tissue = max(int(np.count_nonzero(tissue)), 1)
    metrics = {
        "seed_count": int(markers.max()),
        "candidate_count": len(records),
        "kept_count": int(sum(bool(record["keep"]) for record in records)),
        "kept_fraction": float(
            sum(bool(record["keep"]) for record in records) / max(len(records), 1)
        ),
        "kept_area_fraction": float(np.count_nonzero(kept_label_image) / total_tissue),
        "boundary_support": boundary_support,
        "membrane_threshold": threshold,
        "tissue_fraction": float(np.mean(tissue)),
    }
    return response, labels, records, metrics


def parameter_grid() -> list[dict[str, Any]]:
    configurations: list[dict[str, Any]] = []
    index = 0
    for ridge_sigma_um in (0.35, 0.55):
        for membrane_quantile in (0.68, 0.75, 0.82):
            for seed_min_distance_um in (3.0, 4.0):
                index += 1
                configurations.append(
                    {
                        "configuration_id": f"cfg{index:02d}",
                        "algorithm_version": ALGORITHM_VERSION,
                        "ridge_sigma_um": ridge_sigma_um,
                        "membrane_quantile": membrane_quantile,
                        "seed_min_distance_um": seed_min_distance_um,
                        "patch_side_um": PATCH_SIDE_UM,
                        "patch_spacing_um": PATCH_SPACING_UM,
                        "depths_um": DEPTHS_UM.tolist(),
                        "minimum_area_um2": MIN_AREA_UM2,
                        "maximum_area_um2": MAX_AREA_UM2,
                        "maximum_aspect_ratio": MAX_ASPECT_RATIO,
                    }
                )
    return configurations


def score_configuration(roi_metrics: list[dict[str, float]]) -> float:
    score = 0.0
    for metrics in roi_metrics:
        kept_count = metrics["kept_count"]
        count_support = min(kept_count / 12.0, 1.0)
        if kept_count > 45:
            count_support -= min((kept_count - 45) / 45.0, 1.0)
        boundary_support = metrics["boundary_support"]
        if not np.isfinite(boundary_support):
            boundary_support = -1.0
        score += (
            1.5 * count_support
            + metrics["kept_fraction"]
            + metrics["kept_area_fraction"]
            + 2.0 * boundary_support
        )
    counts = np.array([entry["kept_count"] for entry in roi_metrics], dtype=float)
    if np.mean(counts) > 0:
        score -= float(np.std(counts) / np.mean(counts))
    return float(score / max(len(roi_metrics), 1))


def records_to_csv(path: Path, records: Iterable[dict[str, Any]]) -> None:
    rows = list(records)
    if not rows:
        raise RuntimeError(f"refusing to write empty table: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_overlay(
    raw_signal: np.ndarray, labels: np.ndarray, records: list[dict[str, Any]]
) -> np.ndarray:
    base = robust_unit_interval(raw_signal, np.ones(raw_signal.shape, dtype=bool))
    rgb = np.dstack((base, base, base))
    kept_ids = [int(row["candidate_label"]) for row in records if row["keep"]]
    excluded_ids = [int(row["candidate_label"]) for row in records if not row["keep"]]
    kept_boundaries = segmentation.find_boundaries(
        np.where(np.isin(labels, kept_ids), labels, 0), mode="outer"
    )
    excluded_boundaries = segmentation.find_boundaries(
        np.where(np.isin(labels, excluded_ids), labels, 0), mode="outer"
    )
    rgb[excluded_boundaries] = np.array([0.90, 0.20, 0.18])
    rgb[kept_boundaries] = np.array([0.10, 0.82, 0.38])
    return rgb


def render_development_preview(
    output_path: Path,
    patches: list[PatchData],
    responses: list[np.ndarray],
    labels: list[np.ndarray],
    candidate_records: list[list[dict[str, Any]]],
    config: dict[str, Any],
) -> None:
    figure, axes = plt.subplots(
        len(patches), 4, figsize=(13.0, 9.3), constrained_layout=True
    )
    extent = (
        patches[0].u_um[0],
        patches[0].u_um[-1],
        patches[0].v_um[-1],
        patches[0].v_um[0],
    )
    for row_index, (patch, response, label_image, records) in enumerate(
        zip(patches, responses, labels, candidate_records, strict=True)
    ):
        raw_limits = np.percentile(
            patch.raw_signal[patch.tissue_mask], (2, 99)
        )
        axes[row_index, 0].imshow(
            patch.raw_signal,
            cmap="gray",
            vmin=raw_limits[0],
            vmax=raw_limits[1],
            extent=extent,
        )
        axes[row_index, 1].imshow(response, cmap="magma", vmin=0, vmax=1, extent=extent)
        axes[row_index, 2].imshow(label_image, cmap="nipy_spectral", extent=extent)
        axes[row_index, 3].imshow(
            make_overlay(patch.raw_signal, label_image, records), extent=extent
        )
        kept_count = sum(bool(record["keep"]) for record in records)
        axes[row_index, 0].set_ylabel(f"{patch.roi_id}\nv (µm)")
        axes[row_index, 3].text(
            0.02,
            0.98,
            f"kept {kept_count} / all {len(records)}",
            transform=axes[row_index, 3].transAxes,
            va="top",
            color="white",
            fontsize=8,
            bbox={"facecolor": "black", "alpha": 0.55, "pad": 2},
        )
    titles = ("raw shallow projection", "membrane response", "all partitions", "candidate audit")
    for axis, title in zip(axes[0], titles, strict=True):
        axis.set_title(title)
    for axis in axes.flat:
        axis.set_xlabel("u (µm)")
    figure.suptitle(
        "F1-Seg-A Fish 4 development only\n"
        f"{config['configuration_id']} frozen from 12 predeclared configurations; "
        "green=retained candidate, red=excluded; no human truth",
        fontsize=13,
        fontweight="bold",
    )
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def save_sample_npz(
    path: Path,
    sample: SampleData,
    patches: list[PatchData],
    responses: list[np.ndarray],
    labels: list[np.ndarray],
    config_hash: str,
) -> None:
    np.savez_compressed(
        path,
        schema_version=np.array(SCHEMA_VERSION),
        sample_id=np.array(sample.sample_id),
        role=np.array(sample.role),
        config_hash=np.array(config_hash),
        surface_xyz_um=sample.xyz_um.astype(np.float32),
        surface_normals=sample.normals.astype(np.float32),
        surface_directors=sample.directors.astype(np.float32),
        surface_local_order=sample.local_order.astype(np.float32),
        roi_surface_indices=np.array([patch.surface_index for patch in patches]),
        roi_centers_um=np.stack([patch.center_um for patch in patches]),
        roi_outward_normals=np.stack([patch.outward_normal for patch in patches]),
        roi_inward_normals=np.stack([patch.inward_normal for patch in patches]),
        roi_e1=np.stack([patch.e1 for patch in patches]),
        roi_e2=np.stack([patch.e2 for patch in patches]),
        u_um=patches[0].u_um,
        v_um=patches[0].v_um,
        raw_signal=np.stack([patch.raw_signal for patch in patches]).astype(np.float32),
        tissue_mask=np.stack([patch.tissue_mask for patch in patches]),
        coordinate_valid=np.stack([patch.coordinate_valid for patch in patches]),
        membrane_response=np.stack(responses).astype(np.float32),
        candidate_labels=np.stack(labels).astype(np.int32),
    )


def load_npz_arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as arrays:
        return {key: arrays[key] for key in arrays.files}


def load_csv_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def render_structure_image(output_path: Path, sample_arrays: dict[str, dict[str, np.ndarray]]) -> None:
    figure = plt.figure(figsize=(14.2, 4.8), constrained_layout=True)
    for panel_index, sample_id in enumerate(("fish3", "fish4", "fish5"), start=1):
        arrays = sample_arrays[sample_id]
        axis = figure.add_subplot(1, 3, panel_index, projection="3d")
        xyz = arrays["surface_xyz_um"]
        order = arrays["surface_local_order"]
        scatter = axis.scatter(
            xyz[0], xyz[1], xyz[2], c=order, cmap="viridis", vmin=0, vmax=1,
            s=7, alpha=0.42, linewidths=0,
        )
        centers = arrays["roi_centers_um"]
        e1 = arrays["roi_e1"]
        e2 = arrays["roi_e2"]
        inward = arrays["roi_inward_normals"]
        axis.scatter(
            centers[:, 0], centers[:, 1], centers[:, 2], s=42, c="#f4a261",
            edgecolors="black", linewidths=0.5, depthshade=False,
        )
        for center, basis_1, basis_2, normal in zip(centers, e1, e2, inward, strict=True):
            for vector, color in ((basis_1, "#2a9d8f"), (basis_2, "#457b9d"), (normal, "#e63946")):
                axis.quiver(*center, *(vector * 9.0), color=color, linewidth=1.1, arrow_length_ratio=0.16)
        axis.set_title(f"{sample_id.upper()} — 3 selected tangent frames")
        axis.set_xlabel("x (µm)")
        axis.set_ylabel("y (µm)")
        axis.set_zlabel("z (µm)")
        axis.view_init(elev=24, azim=-62)
        if panel_index == 3:
            colorbar = figure.colorbar(scatter, ax=axis, fraction=0.035, pad=0.02)
            colorbar.set_label("author local nematic order")
    figure.suptitle(
        "F1-Seg-A measured ventricular surface and local tangent-frame structure\n"
        "orange=center; teal/blue=tangent axes; red=inward normal; frames are sampling geometry, not cells",
        fontsize=13,
        fontweight="bold",
    )
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def render_candidate_audit(
    output_path: Path,
    sample_arrays: dict[str, dict[str, np.ndarray]],
    candidate_records: dict[str, list[dict[str, str]]],
) -> None:
    figure, axes = plt.subplots(9, 4, figsize=(12.4, 24.0), constrained_layout=True)
    row_index = 0
    for sample_id in ("fish3", "fish4", "fish5"):
        arrays = sample_arrays[sample_id]
        sample_rows = candidate_records[sample_id]
        for roi_index in range(ROI_COUNT):
            roi_id = f"roi{roi_index + 1}"
            raw = arrays["raw_signal"][roi_index]
            response = arrays["membrane_response"][roi_index]
            labels = arrays["candidate_labels"][roi_index]
            rows = [row for row in sample_rows if row["roi_id"] == roi_id]
            mask = arrays["tissue_mask"][roi_index].astype(bool)
            raw_limits = np.percentile(raw[mask], (2, 99))
            extent = (
                float(arrays["u_um"][0]), float(arrays["u_um"][-1]),
                float(arrays["v_um"][-1]), float(arrays["v_um"][0]),
            )
            axes[row_index, 0].imshow(raw, cmap="gray", vmin=raw_limits[0], vmax=raw_limits[1], extent=extent)
            axes[row_index, 1].imshow(response, cmap="magma", vmin=0, vmax=1, extent=extent)
            axes[row_index, 2].imshow(labels, cmap="nipy_spectral", extent=extent)
            normalized_rows: list[dict[str, Any]] = []
            for row in rows:
                normalized_rows.append({**row, "candidate_label": int(row["candidate_label"]), "keep": row["keep"].lower() == "true"})
            axes[row_index, 3].imshow(make_overlay(raw, labels, normalized_rows), extent=extent)
            kept_count = sum(row["keep"].lower() == "true" for row in rows)
            axes[row_index, 0].set_ylabel(f"{sample_id} {roi_id}\nv (µm)")
            axes[row_index, 3].text(
                0.02, 0.97, f"kept {kept_count}/{len(rows)}", transform=axes[row_index, 3].transAxes,
                va="top", color="white", fontsize=7,
                bbox={"facecolor": "black", "alpha": 0.55, "pad": 1.5},
            )
            row_index += 1
    for axis, title in zip(
        axes[0], ("raw shallow projection", "membrane response", "all partitions", "candidate audit"), strict=True
    ):
        axis.set_title(title)
    for axis in axes.flat:
        axis.set_xlabel("u (µm)")
    figure.suptitle(
        "F1-Seg-A surface-cell candidate audit — 72 hpf zebrafish\n"
        "green=retained engineering candidate; red=excluded edge/size/aspect candidate; no human instance truth",
        fontsize=13,
        fontweight="bold",
    )
    figure.savefig(output_path, dpi=135)
    plt.close(figure)


def render_summary_image(
    output_path: Path,
    sample_arrays: dict[str, dict[str, np.ndarray]],
    candidate_records: dict[str, list[dict[str, str]]],
) -> None:
    figure, axes = plt.subplots(3, 4, figsize=(14.2, 10.2), constrained_layout=True)
    for row_index, sample_id in enumerate(("fish3", "fish4", "fish5")):
        arrays = sample_arrays[sample_id]
        sample_rows = candidate_records[sample_id]
        for roi_index in range(ROI_COUNT):
            labels = arrays["candidate_labels"][roi_index]
            raw = arrays["raw_signal"][roi_index]
            roi_id = f"roi{roi_index + 1}"
            rows = [row for row in sample_rows if row["roi_id"] == roi_id]
            normalized_rows = [
                {**row, "candidate_label": int(row["candidate_label"]), "keep": row["keep"].lower() == "true"}
                for row in rows
            ]
            axes[row_index, roi_index].imshow(make_overlay(raw, labels, normalized_rows))
            kept_count = sum(bool(row["keep"]) for row in normalized_rows)
            axes[row_index, roi_index].set_title(f"{sample_id} {roi_id}: {kept_count} kept")
            axes[row_index, roi_index].set_axis_off()
        kept = [row for row in sample_rows if row["keep"].lower() == "true"]
        area = np.array([float(row["area_um2"]) for row in kept])
        aspect = np.array([float(row["aspect_ratio"]) for row in kept])
        angle = np.array([float(row["candidate_author_axial_angle_deg"]) for row in kept])
        scatter = axes[row_index, 3].scatter(
            area, aspect, c=angle, cmap="plasma_r", vmin=0, vmax=90,
            s=20, alpha=0.78, edgecolors="none",
        )
        axes[row_index, 3].axvline(MIN_AREA_UM2, color="0.55", linestyle="--", linewidth=0.8)
        axes[row_index, 3].axvline(MAX_AREA_UM2, color="0.55", linestyle="--", linewidth=0.8)
        axes[row_index, 3].axhline(MAX_ASPECT_RATIO, color="0.55", linestyle="--", linewidth=0.8)
        axes[row_index, 3].set_xlabel("candidate area (µm²)")
        axes[row_index, 3].set_ylabel("candidate aspect ratio")
        axes[row_index, 3].set_title(f"{sample_id}: morphology candidates")
        if row_index == 2:
            colorbar = figure.colorbar(scatter, ax=axes[row_index, 3], fraction=0.046, pad=0.04)
            colorbar.set_label("angle to nearest author director (deg)")
    figure.suptitle(
        "F1-Seg-A frozen-config candidate result across development and holdout fish\n"
        "Fish 4 selected parameters; Fish 3/5 were not used for tuning; morphology remains unvalidated",
        fontsize=13,
        fontweight="bold",
    )
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def process_sample(
    sample: SampleData,
    config: dict[str, Any],
) -> tuple[
    list[PatchData],
    list[np.ndarray],
    list[np.ndarray],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    selected_indices, ranking_records = select_roi_indices(sample)
    patches: list[PatchData] = []
    responses: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    all_candidate_records: list[dict[str, Any]] = []
    roi_records: list[dict[str, Any]] = []
    score_lookup = {int(row["surface_index"]): float(row["quick_quality_score"]) for row in ranking_records}
    for roi_number, surface_index in enumerate(selected_indices, start=1):
        roi_id = f"roi{roi_number}"
        patch = sample_tangent_patch(
            sample,
            surface_index=surface_index,
            half_width_um=PATCH_SIDE_UM / 2.0,
            spacing_um=PATCH_SPACING_UM,
            quick_quality_score=score_lookup[surface_index],
            roi_id=roi_id,
        )
        response, label_image, candidate_rows, metrics = segment_patch(
            patch, sample, config
        )
        patches.append(patch)
        responses.append(response)
        labels.append(label_image)
        all_candidate_records.extend(candidate_rows)
        orthogonality_error = max(
            abs(float(np.dot(patch.e1, patch.e2))),
            abs(float(np.dot(patch.e1, patch.inward_normal))),
            abs(float(np.dot(patch.e2, patch.inward_normal))),
            abs(float(np.linalg.norm(patch.e1) - 1.0)),
            abs(float(np.linalg.norm(patch.e2) - 1.0)),
            abs(float(np.linalg.norm(patch.inward_normal) - 1.0)),
        )
        roi_records.append(
            {
                "sample_id": sample.sample_id,
                "role": sample.role,
                "roi_id": roi_id,
                "surface_index": surface_index,
                "center_x_um": float(patch.center_um[0]),
                "center_y_um": float(patch.center_um[1]),
                "center_z_um": float(patch.center_um[2]),
                "quick_quality_score": patch.quick_quality_score,
                "coordinate_valid_fraction": float(np.mean(patch.coordinate_valid)),
                "tissue_coverage_fraction": float(np.mean(patch.tissue_mask)),
                "minus_normal_full_mask_occupancy": patch.inward_minus_occupancy,
                "plus_normal_full_mask_occupancy": patch.inward_plus_occupancy,
                "selected_inward_sign": (
                    "plus_outward_normal"
                    if np.dot(patch.inward_normal, patch.outward_normal) > 0
                    else "minus_outward_normal"
                ),
                "orthonormality_max_error": orthogonality_error,
                **metrics,
            }
        )
    return patches, responses, labels, all_candidate_records, roi_records


def run_development(archive_path: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    frozen_config_path = output / "frozen_config.json"
    if frozen_config_path.exists():
        raise RuntimeError("development phase already exists; refusing to overwrite")
    sample = load_sample(archive_path, "fish4")
    selected_indices, ranking_records = select_roi_indices(sample)
    score_lookup = {int(row["surface_index"]): float(row["quick_quality_score"]) for row in ranking_records}
    patches = [
        sample_tangent_patch(
            sample,
            surface_index=index,
            half_width_um=PATCH_SIDE_UM / 2.0,
            spacing_um=PATCH_SPACING_UM,
            quick_quality_score=score_lookup[index],
            roi_id=f"roi{position}",
        )
        for position, index in enumerate(selected_indices, start=1)
    ]

    search_rows: list[dict[str, Any]] = []
    evaluated: list[tuple[float, dict[str, Any]]] = []
    for config in parameter_grid():
        metrics_for_config: list[dict[str, float]] = []
        for patch in patches:
            _, _, _, metrics = segment_patch(patch, sample, config)
            metrics_for_config.append(metrics)
            search_rows.append(
                {
                    "configuration_id": config["configuration_id"],
                    "roi_id": patch.roi_id,
                    **metrics,
                }
            )
        objective = score_configuration(metrics_for_config)
        evaluated.append((objective, config))
        for row in search_rows[-len(patches) :]:
            row["configuration_objective"] = objective
    evaluated.sort(key=lambda item: (-item[0], item[1]["configuration_id"]))
    best_objective, best_config = evaluated[0]
    frozen_payload = {
        "schema_version": SCHEMA_VERSION,
        "phase": "development_frozen_configuration",
        "development_sample": "fish4",
        "holdout_samples": ["fish3", "fish5"],
        "configuration_count_evaluated": len(evaluated),
        "selection_objective": (
            "mean candidate-count support + retained fraction + retained-area fraction "
            "+ membrane-boundary support, with cross-ROI count-CV penalty; no human truth"
        ),
        "selected_objective": best_objective,
        "configuration": best_config,
        "scientific_status": "engineering_candidate_only",
    }
    frozen_payload["configuration_sha256"] = sha256_json(best_config)
    write_json(frozen_config_path, frozen_payload)
    records_to_csv(output / "development_parameter_search.csv", search_rows)
    records_to_csv(output / "fish4_roi_selection.csv", ranking_records)

    responses: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    all_candidates: list[dict[str, Any]] = []
    roi_rows: list[dict[str, Any]] = []
    for patch in patches:
        response, label_image, candidate_rows, metrics = segment_patch(
            patch, sample, best_config
        )
        responses.append(response)
        labels.append(label_image)
        all_candidates.extend(candidate_rows)
        orthogonality_error = max(
            abs(float(np.dot(patch.e1, patch.e2))),
            abs(float(np.dot(patch.e1, patch.inward_normal))),
            abs(float(np.dot(patch.e2, patch.inward_normal))),
        )
        roi_rows.append(
            {
                "sample_id": sample.sample_id,
                "role": sample.role,
                "roi_id": patch.roi_id,
                "surface_index": patch.surface_index,
                "center_x_um": float(patch.center_um[0]),
                "center_y_um": float(patch.center_um[1]),
                "center_z_um": float(patch.center_um[2]),
                "quick_quality_score": patch.quick_quality_score,
                "coordinate_valid_fraction": float(np.mean(patch.coordinate_valid)),
                "tissue_coverage_fraction": float(np.mean(patch.tissue_mask)),
                "minus_normal_full_mask_occupancy": patch.inward_minus_occupancy,
                "plus_normal_full_mask_occupancy": patch.inward_plus_occupancy,
                "selected_inward_sign": (
                    "plus_outward_normal"
                    if np.dot(patch.inward_normal, patch.outward_normal) > 0
                    else "minus_outward_normal"
                ),
                "orthonormality_max_error": orthogonality_error,
                **metrics,
            }
        )
    config_hash = str(frozen_payload["configuration_sha256"])
    for row in all_candidates:
        row["configuration_sha256"] = config_hash
    for row in roi_rows:
        row["configuration_sha256"] = config_hash
    records_to_csv(output / "fish4_candidates.csv", all_candidates)
    records_to_csv(output / "fish4_roi_quality.csv", roi_rows)
    save_sample_npz(
        output / "fish4_candidate_arrays.npz",
        sample,
        patches,
        responses,
        labels,
        config_hash,
    )
    render_development_preview(
        output / "fish4_development_preview.png",
        patches,
        responses,
        labels,
        [
            [row for row in all_candidates if row["roi_id"] == patch.roi_id]
            for patch in patches
        ],
        best_config,
    )
    development_summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "development_complete_configuration_frozen",
        "selected_configuration_sha256": config_hash,
        "selected_configuration_id": best_config["configuration_id"],
        "configuration_count_evaluated": len(evaluated),
        "selected_surface_indices": selected_indices,
        "candidate_count": len(all_candidates),
        "kept_candidate_count": sum(bool(row["keep"]) for row in all_candidates),
        "next_phase": "holdout may run once after visual review; no retuning from holdout",
    }
    write_json(output / "development_execution.json", development_summary)
    print(json.dumps(development_summary, ensure_ascii=False, indent=2))


def gate_summary(
    output: Path,
    frozen: dict[str, Any],
    sample_arrays: dict[str, dict[str, np.ndarray]],
    candidates_by_sample: dict[str, list[dict[str, str]]],
    roi_by_sample: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    config_hash = str(frozen["configuration_sha256"])
    g0_checks: dict[str, bool] = {}
    g1_checks: dict[str, bool] = {}
    per_fish: dict[str, Any] = {}
    area_medians: dict[str, float] = {}
    aspect_medians: dict[str, float] = {}
    for sample_id in ("fish3", "fish4", "fish5"):
        arrays = sample_arrays[sample_id]
        candidates = candidates_by_sample[sample_id]
        rois = roi_by_sample[sample_id]
        kept = [row for row in candidates if row["keep"].lower() == "true"]
        areas = np.array([float(row["area_um2"]) for row in kept], dtype=float)
        aspects = np.array([float(row["aspect_ratio"]) for row in kept], dtype=float)
        hashes = {row["configuration_sha256"] for row in candidates}
        g0_checks[f"{sample_id}_three_rois"] = len(rois) == ROI_COUNT
        g0_checks[f"{sample_id}_finite_coordinates"] = bool(
            np.all(np.isfinite(arrays["roi_centers_um"]))
        )
        g0_checks[f"{sample_id}_orthonormal"] = all(
            float(row["orthonormality_max_error"]) < 1e-6 for row in rois
        )
        g1_checks[f"{sample_id}_configuration_hash"] = hashes == {config_hash}
        g1_checks[f"{sample_id}_at_least_15_kept"] = len(kept) >= 15
        g1_checks[f"{sample_id}_finite_bounded_morphology"] = bool(
            len(kept)
            and np.all(np.isfinite(areas))
            and np.all(np.isfinite(aspects))
            and np.all((areas >= MIN_AREA_UM2) & (areas <= MAX_AREA_UM2))
            and np.all((aspects > 0) & (aspects <= MAX_ASPECT_RATIO))
        )
        area_medians[sample_id] = float(np.median(areas)) if areas.size else float("nan")
        aspect_medians[sample_id] = float(np.median(aspects)) if aspects.size else float("nan")
        per_fish[sample_id] = {
            "role": SAMPLES[sample_id]["role"],
            "roi_count": len(rois),
            "all_candidate_count": len(candidates),
            "kept_candidate_count": len(kept),
            "median_area_um2": area_medians[sample_id],
            "median_aspect_ratio": aspect_medians[sample_id],
        }

    finite_area = [value for value in area_medians.values() if np.isfinite(value) and value > 0]
    finite_aspect = [value for value in aspect_medians.values() if np.isfinite(value) and value > 0]
    area_ratio = max(finite_area) / min(finite_area) if len(finite_area) == 3 else float("inf")
    aspect_ratio = max(finite_aspect) / min(finite_aspect) if len(finite_aspect) == 3 else float("inf")
    g1_checks["cross_fish_area_median_ratio_at_most_2"] = area_ratio <= 2.0
    g1_checks["cross_fish_aspect_median_ratio_at_most_2"] = aspect_ratio <= 2.0
    required_outputs = (
        "surface_tangent_structure.png",
        "candidate_segmentation_audit.png",
        "candidate_summary.png",
        "all_candidates.csv",
        "all_roi_quality.csv",
        "frozen_config.json",
    )
    g1_checks["required_outputs_present"] = all((output / name).is_file() for name in required_outputs)
    g0_status = "passed" if all(g0_checks.values()) else "failed"
    g1_status = "passed" if all(g1_checks.values()) else "failed"
    if g0_status != "passed":
        overall = "failed_surface_extraction"
    elif g1_status != "passed":
        overall = "failed_engineering_candidate_gate"
    else:
        overall = "blocked_human_validation"
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "F1-Seg-A",
        "overall_status": overall,
        "scientific_solver_runs": 0,
        "gpu_runs": 0,
        "automatic_retries": 0,
        "development_sample": "fish4",
        "holdout_samples": ["fish3", "fish5"],
        "configuration_sha256": config_hash,
        "gates": {
            "G0_surface_extraction": {"status": g0_status, "checks": g0_checks},
            "G1_engineering_candidates": {"status": g1_status, "checks": g1_checks},
            "G2_independent_human_holdout": {
                "status": "not_run",
                "reason": "no independent per-cell instance labels were supplied",
            },
        },
        "cross_fish": {
            "area_median_max_min_ratio": area_ratio,
            "aspect_median_max_min_ratio": aspect_ratio,
        },
        "per_fish": per_fish,
        "scientific_boundaries": [
            "Candidate partitions are not validated cell instances.",
            "Author surface points are sampling points, not cell centers.",
            "Agreement with the nearest author nematic director is a consistency readout, not ground truth.",
            "This stage does not validate FEM, DCM, contraction, growth, or ECM feedback.",
        ],
    }


def write_readme(output: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# F1-Seg-A surface-cell candidate package",
        "",
        f"- Overall status: `{summary['overall_status']}`",
        f"- G0 surface extraction: `{summary['gates']['G0_surface_extraction']['status']}`",
        f"- G1 engineering candidates: `{summary['gates']['G1_engineering_candidates']['status']}`",
        "- G2 independent human holdout: `not_run`",
        "- Solver/GPU runs: `0 / 0`",
        "",
        "Fish 4 alone selected one configuration from 12 predeclared combinations. Fish 3 and Fish 5 were then processed once with the same configuration hash. Green contours in the audit figures are retained engineering candidates; red contours are explicit edge/size/aspect exclusions.",
        "",
        "This package does not establish cell identity or biological segmentation accuracy. Independent frozen ROI annotation is required before morphology can be used as FEM/DCM geometry evidence.",
        "",
        "## Main outputs",
        "",
        "- `surface_tangent_structure.png`: measured surface samples and selected tangent frames.",
        "- `candidate_segmentation_audit.png`: raw, enhanced, partition, and inclusion/exclusion panels for all 9 ROIs.",
        "- `candidate_summary.png`: cross-fish candidate overview and morphology scatter.",
        "- `all_candidates.csv`: every partition with exclusion flags and candidate measurements.",
        "- `all_roi_quality.csv`: extraction and gate diagnostics.",
        "- `run_summary.json`: machine-readable gate verdict.",
        "",
    ]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


def run_holdout(archive_path: Path, output: Path) -> None:
    frozen_path = output / "frozen_config.json"
    if not frozen_path.is_file():
        raise RuntimeError("missing frozen Fish 4 configuration")
    holdout_execution_path = output / "holdout_execution.json"
    if holdout_execution_path.exists():
        raise RuntimeError("holdout phase already completed; refusing to rerun")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    config = frozen["configuration"]
    config_hash = sha256_json(config)
    if config_hash != frozen["configuration_sha256"]:
        raise RuntimeError("frozen configuration hash mismatch")

    for sample_id in ("fish3", "fish5"):
        sample = load_sample(archive_path, sample_id)
        patches, responses, labels, candidates, roi_rows = process_sample(sample, config)
        for row in candidates:
            row["configuration_sha256"] = config_hash
        for row in roi_rows:
            row["configuration_sha256"] = config_hash
        records_to_csv(output / f"{sample_id}_candidates.csv", candidates)
        records_to_csv(output / f"{sample_id}_roi_quality.csv", roi_rows)
        save_sample_npz(
            output / f"{sample_id}_candidate_arrays.npz",
            sample,
            patches,
            responses,
            labels,
            config_hash,
        )

    sample_arrays = {
        sample_id: load_npz_arrays(output / f"{sample_id}_candidate_arrays.npz")
        for sample_id in ("fish3", "fish4", "fish5")
    }
    candidates_by_sample = {
        sample_id: load_csv_records(output / f"{sample_id}_candidates.csv")
        for sample_id in ("fish3", "fish4", "fish5")
    }
    roi_by_sample = {
        sample_id: load_csv_records(output / f"{sample_id}_roi_quality.csv")
        for sample_id in ("fish3", "fish4", "fish5")
    }
    all_candidates = [
        row
        for sample_id in ("fish3", "fish4", "fish5")
        for row in candidates_by_sample[sample_id]
    ]
    all_rois = [
        row
        for sample_id in ("fish3", "fish4", "fish5")
        for row in roi_by_sample[sample_id]
    ]
    records_to_csv(output / "all_candidates.csv", all_candidates)
    records_to_csv(output / "all_roi_quality.csv", all_rois)
    render_structure_image(output / "surface_tangent_structure.png", sample_arrays)
    render_candidate_audit(
        output / "candidate_segmentation_audit.png",
        sample_arrays,
        candidates_by_sample,
    )
    render_summary_image(
        output / "candidate_summary.png", sample_arrays, candidates_by_sample
    )
    summary = gate_summary(
        output, frozen, sample_arrays, candidates_by_sample, roi_by_sample
    )
    write_json(output / "run_summary.json", summary)
    write_readme(output, summary)

    result_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    execution = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed_once",
        "holdout_samples": ["fish3", "fish5"],
        "configuration_sha256": config_hash,
        "result_bytes": result_bytes,
        "result_cap_bytes": RESULT_CAP_BYTES,
        "within_result_cap": result_bytes <= RESULT_CAP_BYTES,
        "overall_status": summary["overall_status"],
    }
    write_json(holdout_execution_path, execution)
    final_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    if final_bytes > RESULT_CAP_BYTES:
        raise RuntimeError(
            f"result package exceeds 64 MiB cap: {final_bytes} bytes"
        )
    print(json.dumps({**execution, "final_result_bytes": final_bytes}, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    archive = args.archive.resolve()
    output = args.output.resolve()
    if not archive.is_file():
        raise FileNotFoundError(archive)
    if args.phase == "development":
        run_development(archive, output)
    else:
        run_holdout(archive, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
