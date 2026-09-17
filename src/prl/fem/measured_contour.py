"""Image-derived outer contour and explicitly constructed inner FEM layers."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import zipfile

import numpy as np
from scipy import ndimage
from scipy.optimize import linprog
from scipy.spatial import cKDTree
from skimage.draw import polygon2mask
from skimage.measure import find_contours
import tifffile

from prl.fem.active_ellipse import MeshLevel, assemble_model


ARCHIVE = Path(r"E:\Data\PRL\public\zenodo\15509350\Data.zip")
MEMBER = "Data/Zebrafish/Fish_72hpf_4_Fig4-5/Mask_Full.tif"
VOXEL_UM = np.array([0.2071606, 0.2071606, 1.0])
LEVELS = {"G0": MeshLevel("G0", 96, (2, 2, 4)),
          "G1": MeshLevel("G1", 192, (4, 4, 8))}
RADIAL = np.array([1.00, 1.05, 1.10, 1.35]) / 1.35


def area(p: np.ndarray) -> float:
    return float(np.sum(p[:, 0] * np.roll(p[:, 1], -1)
                        - p[:, 1] * np.roll(p[:, 0], -1)) / 2)


def periodic_resample(points: np.ndarray, count: int) -> np.ndarray:
    closed = np.vstack([points, points[0]])
    arclength = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    query = np.arange(count) * arclength[-1] / count
    return np.column_stack([np.interp(query, arclength, closed[:, j]) for j in (0, 1)])


def boundary_diagnostics(arrays: dict, boundary: np.ndarray) -> dict:
    """Report mesh polygon fidelity separately from image-contour smoothing."""
    mask = arrays["slice_mask"]
    raster = polygon2mask(mask.shape, boundary[:, ::-1] / VOXEL_UM[0])
    perimeter = np.linalg.norm(np.roll(boundary, -1, axis=0)-boundary, axis=1).sum()
    dense = periodic_resample(boundary, int(np.ceil(perimeter / 0.10)))
    raw = arrays["raw_contour_um"]
    return {
        "outer_boundary_nodes": len(boundary),
        "source_mask_iou": float((raster & mask).sum()/(raster | mask).sum()),
        "sampled_hausdorff_to_raw_um": float(max(cKDTree(raw).query(dense)[0].max(),
                                                 cKDTree(dense).query(raw)[0].max())),
        "distance_sampling_max_step_um": 0.10,
        "polygon_area_um2": area(boundary),
        "relative_area_difference_to_smooth": area(boundary)/area(arrays["smooth_contour_um"])-1,
    }


def extract_geometry(archive: Path = ARCHIVE) -> tuple[dict, dict]:
    with zipfile.ZipFile(archive) as container:
        member_bytes = container.read(MEMBER)
    source_sha = hashlib.sha256(member_bytes).hexdigest()
    volume = tifffile.imread(io.BytesIO(member_bytes), maxworkers=1) > 0
    counts = volume.sum(axis=(1, 2))
    index = int(counts.argmax())
    source_slice = volume[index].copy()
    components, count = ndimage.label(source_slice)
    sizes = np.bincount(components.ravel()); sizes[0] = 0
    largest = components == sizes.argmax()
    filled = ndimage.binary_fill_holes(largest)
    contour = max(find_contours(filled.astype(float), 0.5), key=len)
    if not np.allclose(contour[0], contour[-1]):
        raise ValueError("selected image contour is not closed; no synthetic closure allowed")
    raw = contour[:-1, ::-1] * VOXEL_UM[:2]
    if area(raw) < 0:
        raw = raw[::-1]
    perimeter = np.linalg.norm(np.roll(raw, -1, axis=0) - raw, axis=1).sum()
    sample_count = int(np.ceil(perimeter / 0.25))
    smooth = ndimage.gaussian_filter1d(
        periodic_resample(raw, sample_count), 1.0 / (perimeter / sample_count),
        axis=0, mode="wrap")
    edges = np.roll(smooth, -1, axis=0) - smooth
    edges /= np.linalg.norm(edges, axis=1)[:, None]
    # The kernel is the intersection of inward edge half-planes, not the convex hull.
    kernel = linprog(
        [0, 0, -1], A_ub=np.c_[edges[:, 1], -edges[:, 0], np.ones(len(edges))],
        b_ub=edges[:, 1] * smooth[:, 0] - edges[:, 0] * smooth[:, 1],
        bounds=[(None, None)] * 3, method="highs", options={"threads": 1})
    if not kernel.success or kernel.x[2] <= 0:
        raise ValueError("outer contour has no positive-margin homothetic kernel")
    center = kernel.x[:2]
    raster = polygon2mask(filled.shape, smooth[:, ::-1] / VOXEL_UM[0])
    iou = float((raster & filled).sum() / (raster | filled).sum())
    hausdorff = float(max(cKDTree(raw).query(smooth)[0].max(),
                          cKDTree(smooth).query(raw)[0].max()))
    scale = float(np.sqrt(area(smooth) / np.pi) / 1.35)
    arrays = {"raw_contour_um": raw, "smooth_contour_um": smooth,
              "slice_mask": filled, "source_slice_mask": source_slice,
              "voxel_um": VOXEL_UM, "slice_z_index": np.asarray(index),
              "center_um": center, "length_scale_um": np.asarray(scale)}
    report = {
        "status": "passed" if iou >= .98 and hausdorff <= 2 else "failed",
        "source": {"archive": str(archive), "member": MEMBER, "member_sha256": source_sha},
        "source_shape_zyx": list(volume.shape), "voxel_um": VOXEL_UM.tolist(),
        "slice_z_index": index, "slice_selection": "maximum occupied XY slice; not projection",
        "components": int(count), "discarded_component_pixels": int(source_slice.sum()-largest.sum()),
        "filled_hole_pixels": int(filled.sum()-largest.sum()),
        "source_mask_iou": iou, "contour_hausdorff_um": hausdorff,
        "smoothing_sigma_arclength_um": 1.0, "smooth_outer_area_um2": area(smooth),
        "center_um": center.tolist(), "center_rule": "maximum margin of inward half-plane intersection",
        "kernel_margin_um": float(kernel.x[2]), "length_scale_um": scale,
        "internal_geometry": "assumed homothetic cavity/layers, not measured anatomy",
        "radial_boundary_fractions": RADIAL.tolist(),
    }
    return arrays, report


def make_model(arrays: dict, level_label: str):
    level = LEVELS[level_label]
    boundary = periodic_resample(arrays["smooth_contour_um"], level.ntheta)
    norm_boundary = (boundary - arrays["center_um"]) / float(arrays["length_scale_um"])
    radii = [RADIAL[0]]; layer_intervals = []
    for layer, count in enumerate(level.radial_intervals):
        radii.extend(np.linspace(RADIAL[layer], RADIAL[layer+1], count+1)[1:])
        layer_intervals.extend([layer] * count)
    coordinates = np.concatenate([radius * norm_boundary for radius in radii])
    cells=[]; layers=[]; tangents=[]
    for radial_index, layer in enumerate(layer_intervals):
        for angular in range(level.ntheta):
            following = (angular + 1) % level.ntheta
            a=radial_index*level.ntheta+angular
            b=radial_index*level.ntheta+following
            c=(radial_index+1)*level.ntheta+angular
            d=(radial_index+1)*level.ntheta+following
            cells.extend(((a,c,d),(a,d,b))); layers.extend((layer,layer))
            tangent = boundary[following]-boundary[angular]
            tangent = tangent/np.linalg.norm(tangent) if layer==2 else np.zeros(2)
            tangents.extend((tangent,tangent))
    cells=np.asarray(cells,dtype=np.int64); layers=np.asarray(layers,dtype=np.int64)
    tangents=np.asarray(tangents)
    eigenstrain=-np.c_[tangents[:,0]**2,tangents[:,1]**2,2*tangents[:,0]*tangents[:,1]]
    model=assemble_model(level, coordinates, cells, layers,
                         np.arange(level.ntheta,dtype=np.int64),
                         np.arange((len(radii)-1)*level.ntheta,len(radii)*level.ntheta,dtype=np.int64),
                         eigenstrain)
    return model, tangents
