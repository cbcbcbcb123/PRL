"""Read-only qualification preview for Zenodo record 15509350.

The script never extracts archive members and never executes upstream code.  It
reads one processed zebrafish sample directly from a ZIP archive, audits member
paths, records the physical scale embedded in the MATLAB/TIFF data, and writes a
small JSON summary plus a PNG preview into the PRL evidence package.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

import h5py
import matplotlib.pyplot as plt
import numpy as np
import tifffile


REQUIRED_MEMBERS = (
    "SurfacePoints.mat",
    "Analysis_Coarse_Grained_Nematic.mat",
    "Analysis_Surface_Marker_X.mat",
    "Orientation_Ch.tif",
    "Marker_X.tif",
    "Mask_Boundary.tif",
    "Mask_Full.tif",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--qualification-role",
        choices=("format_example", "primary_candidate"),
        required=True,
    )
    return parser.parse_args()


def audit_archive(archive: zipfile.ZipFile) -> dict[str, object]:
    unsafe_paths: list[str] = []
    symbolic_links: list[str] = []
    for member in archive.infolist():
        member_path = PurePosixPath(member.filename.replace("\\", "/"))
        first_part = member_path.parts[0] if member_path.parts else ""
        if member_path.is_absolute() or ".." in member_path.parts or ":" in first_part:
            unsafe_paths.append(member.filename)
        unix_mode = member.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            symbolic_links.append(member.filename)
    return {
        "member_count": len(archive.infolist()),
        "compressed_bytes": sum(item.compress_size for item in archive.infolist()),
        "uncompressed_bytes": sum(item.file_size for item in archive.infolist()),
        "unsafe_paths": unsafe_paths,
        "symbolic_links": symbolic_links,
        "status": "passed" if not unsafe_paths and not symbolic_links else "failed",
    }


def read_hdf5_member(
    archive: zipfile.ZipFile, member_name: str
) -> tuple[io.BytesIO, h5py.File]:
    memory_file = io.BytesIO(archive.read(member_name))
    return memory_file, h5py.File(memory_file, "r")


def read_tiff_member(
    archive: zipfile.ZipFile, member_name: str
) -> tuple[np.ndarray, dict[str, object]]:
    with tifffile.TiffFile(io.BytesIO(archive.read(member_name))) as image_file:
        image = image_file.asarray()
        imagej_metadata = image_file.imagej_metadata or {}
        metadata = {
            "shape": list(image.shape),
            "dtype": str(image.dtype),
            "axes": image_file.series[0].axes,
            "page_count": len(image_file.pages),
            "imagej_unit": imagej_metadata.get("unit"),
            "first_label": (imagej_metadata.get("Labels") or [None])[0],
            "imagej_info": imagej_metadata.get("Info", ""),
        }
    return image, metadata


def inspect_tiff_member(
    archive: zipfile.ZipFile, member_name: str
) -> dict[str, object]:
    with tifffile.TiffFile(io.BytesIO(archive.read(member_name))) as image_file:
        imagej_metadata = image_file.imagej_metadata or {}
        return {
            "shape": list(image_file.series[0].shape),
            "dtype": str(image_file.series[0].dtype),
            "axes": image_file.series[0].axes,
            "page_count": len(image_file.pages),
            "imagej_unit": imagej_metadata.get("unit"),
            "first_label": (imagej_metadata.get("Labels") or [None])[0],
            "imagej_info": imagej_metadata.get("Info", ""),
        }


def metadata_value(info: str, label: str) -> float | None:
    match = re.search(rf"{re.escape(label)}\s*=\s*([0-9.Ee+-]+)", info)
    return float(match.group(1)) if match else None


def metadata_text(info: str, label: str) -> str | None:
    match = re.search(rf"{re.escape(label)}\s*=\s*([^\r\n]+)", info)
    return match.group(1).strip() if match else None


def robust_limits(image: np.ndarray) -> tuple[float, float]:
    positive = image[image > 0]
    if positive.size == 0:
        return 0.0, 1.0
    lower, upper = np.percentile(positive, (2.0, 99.5))
    if upper <= lower:
        upper = lower + 1.0
    return float(lower), float(upper)


def main() -> int:
    args = parse_args()
    prefix = args.prefix.replace("\\", "/").rstrip("/") + "/"
    args.output.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(args.archive) as archive:
        archive_audit = audit_archive(archive)
        present_members = {item.filename for item in archive.infolist()}
        missing_members = [
            name for name in REQUIRED_MEMBERS if prefix + name not in present_members
        ]
        if archive_audit["status"] != "passed" or missing_members:
            raise RuntimeError(
                f"archive qualification failed: audit={archive_audit}, "
                f"missing={missing_members}"
            )

        points_buffer, points_file = read_hdf5_member(
            archive, prefix + "SurfacePoints.mat"
        )
        try:
            surface_xyz_um = points_file["SurfacePoints/xyz"][()]
            surface_normals = points_file["SurfacePoints/xyzNormal"][()]
            voxel_size_um = points_file["SurfacePoints/Pixel"][()].ravel()
            grid_distance_um = float(
                points_file["SurfacePoints/GridDistance"][()].ravel()[0]
            )
        finally:
            points_file.close()
            points_buffer.close()

        nematic_buffer, nematic_file = read_hdf5_member(
            archive, prefix + "Analysis_Coarse_Grained_Nematic.mat"
        )
        try:
            directors = nematic_file[
                "CoarseGrainedNematic/Nematic_Director"
            ][()]
            local_order = nematic_file["CoarseGrainedNematic/Local_Order"][()].ravel()
            coarse_radius_um = float(
                nematic_file[
                    "CoarseGrainedNematic/Coarse_Graining_radius"
                ][()].ravel()[0]
            )
        finally:
            nematic_file.close()
            nematic_buffer.close()

        orientation, orientation_metadata = read_tiff_member(
            archive, prefix + "Orientation_Ch.tif"
        )
        boundary, boundary_metadata = read_tiff_member(
            archive, prefix + "Mask_Boundary.tif"
        )
        marker_metadata = inspect_tiff_member(archive, prefix + "Marker_X.tif")

    if orientation.shape != boundary.shape or orientation.ndim != 3:
        raise RuntimeError(
            f"incompatible TIFF arrays: orientation={orientation.shape}, "
            f"boundary={boundary.shape}"
        )

    boundary_binary = boundary > 0
    boundary_projection = boundary_binary.max(axis=0)
    occupied_y, occupied_x = np.nonzero(boundary_projection)
    if occupied_x.size == 0:
        raise RuntimeError("boundary mask contains no positive voxels")
    margin = 20
    x_start = max(0, int(occupied_x.min()) - margin)
    x_stop = min(boundary.shape[2], int(occupied_x.max()) + margin + 1)
    y_start = max(0, int(occupied_y.min()) - margin)
    y_stop = min(boundary.shape[1], int(occupied_y.max()) + margin + 1)
    crop = np.s_[y_start:y_stop, x_start:x_stop]

    inverted_signal = 255.0 - orientation.astype(np.float32)
    signal_projection = inverted_signal.max(axis=0)
    boundary_counts = boundary_binary.sum(axis=(1, 2))
    representative_z = int(np.argmax(boundary_counts))
    projection_limits = robust_limits(signal_projection[crop])
    slice_limits = robust_limits(inverted_signal[representative_z][crop])

    figure, axes = plt.subplots(2, 2, figsize=(12.8, 10.2), constrained_layout=True)
    axes[0, 0].imshow(
        signal_projection[crop], cmap="gray", vmin=projection_limits[0], vmax=projection_limits[1]
    )
    axes[0, 0].set_title("A  Membrane-channel inverse maximum projection")
    axes[0, 1].imshow(
        inverted_signal[representative_z][crop],
        cmap="gray",
        vmin=slice_limits[0],
        vmax=slice_limits[1],
    )
    axes[0, 1].set_title(f"B  Representative optical plane (z={representative_z})")
    axes[1, 0].imshow(boundary_projection[crop], cmap="gray", vmin=0, vmax=1)
    axes[1, 0].set_title("C  Processed tissue-region mask projection")
    for image_axis in axes.flat[:3]:
        image_axis.set_axis_off()

    step = max(1, surface_xyz_um.shape[1] // 180)
    selected = np.arange(0, surface_xyz_um.shape[1], step)
    scatter = axes[1, 1].scatter(
        surface_xyz_um[0],
        surface_xyz_um[1],
        c=local_order,
        cmap="viridis",
        vmin=0,
        vmax=1,
        s=12,
        alpha=0.8,
        linewidths=0,
    )
    axes[1, 1].quiver(
        surface_xyz_um[0, selected],
        surface_xyz_um[1, selected],
        directors[0, selected],
        directors[1, selected],
        color="#b2182b",
        angles="xy",
        scale_units="xy",
        scale=0.12,
        width=0.003,
        headwidth=0,
        headlength=0,
        headaxislength=0,
        alpha=0.9,
    )
    axes[1, 1].set_aspect("equal", adjustable="box")
    axes[1, 1].invert_yaxis()
    axes[1, 1].set_xlabel("x (µm)")
    axes[1, 1].set_ylabel("y (µm)")
    axes[1, 1].set_title("D  Surface samples and measured nematic directors")
    colorbar = figure.colorbar(scatter, ax=axes[1, 1], fraction=0.046, pad=0.04)
    colorbar.set_label("local nematic order")

    figure.suptitle(
        f"Real zebrafish ventricle data qualification — {args.stage}, {args.sample_id}\n"
        f"role: {args.qualification_role}; source: Zenodo 15509350; not a model result",
        fontsize=14,
        fontweight="bold",
    )
    preview_path = args.output / "real_data_structure_preview.png"
    figure.savefig(preview_path, dpi=180)
    plt.close(figure)

    boundary_info_text = str(boundary_metadata["imagej_info"])
    marker_info_text = str(marker_metadata["imagej_info"])
    scale_labels = [f"Scaling|Distance|Value #{axis_number}" for axis_number in (1, 2, 3)]
    if all(metadata_value(boundary_info_text, label) is not None for label in scale_labels):
        scale_info_text = boundary_info_text
        scale_metadata_source = "Mask_Boundary.tif ImageJ metadata"
    else:
        scale_info_text = marker_info_text
        scale_metadata_source = "Marker_X.tif ImageJ metadata"
    tiff_scale_m = [
        metadata_value(scale_info_text, label) for label in scale_labels
    ]
    tiff_scale_um = [
        value * 1e6 if value is not None else None for value in tiff_scale_m
    ]
    summary = {
        "schema_version": "prl.f1r_data_qualification_preview.v1",
        "status": "passed",
        "scope": "read-only format and morphology preview; no segmentation or solver run",
        "source": {
            "zenodo_record": "15509350",
            "doi": "10.5281/zenodo.15509350",
            "archive": str(args.archive.resolve()),
            "archive_prefix": prefix,
            "stage": args.stage,
            "sample_id": args.sample_id,
            "qualification_role": args.qualification_role,
        },
        "archive_audit": archive_audit,
        "required_members": list(REQUIRED_MEMBERS),
        "measurements": {
            "voxel_size_um_from_surface_points": voxel_size_um.tolist(),
            "voxel_size_um_from_tiff_metadata": tiff_scale_um,
            "voxel_size_tiff_metadata_source": scale_metadata_source,
            "voxel_scale_sources_agree": bool(
                all(value is not None for value in tiff_scale_um)
                and np.allclose(voxel_size_um, tiff_scale_um, rtol=0, atol=1e-6)
            ),
            "grid_distance_um": grid_distance_um,
            "coarse_graining_radius_um": coarse_radius_um,
            "surface_point_count": int(surface_xyz_um.shape[1]),
            "surface_xyz_um_min": surface_xyz_um.min(axis=1).tolist(),
            "surface_xyz_um_max": surface_xyz_um.max(axis=1).tolist(),
            "normal_norm_range": [
                float(np.linalg.norm(surface_normals, axis=0).min()),
                float(np.linalg.norm(surface_normals, axis=0).max()),
            ],
            "director_norm_range": [
                float(np.linalg.norm(directors, axis=0).min()),
                float(np.linalg.norm(directors, axis=0).max()),
            ],
            "local_order_range": [float(local_order.min()), float(local_order.max())],
            "orientation_tiff": {
                key: value
                for key, value in orientation_metadata.items()
                if key != "imagej_info"
            },
            "boundary_tiff": {
                key: value
                for key, value in boundary_metadata.items()
                if key != "imagej_info"
            },
            "marker_tiff": {
                key: value
                for key, value in marker_metadata.items()
                if key != "imagej_info"
            },
            "source_series_name": metadata_text(boundary_info_text, "Series 0 Name")
            or metadata_text(marker_info_text, "Series 0 Name"),
            "representative_z_index": representative_z,
            "boundary_positive_voxels": int(boundary_binary.sum()),
        },
        "outputs": {"preview": preview_path.name},
        "scientific_boundaries": [
            "This preview does not establish per-cell instance segmentation.",
            "This preview does not establish contraction kinematics or mechanical validation.",
            (
                "A format example at 120 hpf cannot substitute for the frozen 72 hpf primary gate."
                if args.qualification_role == "format_example"
                else "The 72 hpf primary preview qualifies processed input for re-segmentation only."
            ),
            "Marker_X is channel 2/3 of a source series named BFP-CAAX H2B-mNG; its biological identity must not be relabeled as F-actin without resolving this upstream metadata conflict.",
        ],
    }
    (args.output / "preview_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
