#!/usr/bin/env python3
"""Read-only reanalysis of PRL_FEM_Expert_Review_20260918_v01.

Usage:
  python -B prl_independent_audit.py --root /path/to/unpacked/package \
      --zip /path/to/PRL_FEM_Expert_Review_20260918_v01.zip \
      --output /path/outside/package/audit.json

Requires Python >= 3.10 and NumPy. Imports the supplied NumPy verification
modules. Does NOT run FEM, Gmsh, notebooks, or the complete regression suite.
The candidate is rechecked from its saved NPZ, not independently parsed from MSH.
A scientifically failed saved state is an expected result, not a script error.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import zipfile
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def compare_nested(a, b, path=''):
    """Compare a saved numeric report with float tolerance; preserve exact verdicts."""
    mismatches, max_abs = [], 0.0
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() | b.keys()):
            p = path + '/' + key
            if key not in a or key not in b:
                mismatches.append(p + ': missing key')
            else:
                bad, delta = compare_nested(a[key], b[key], p)
                mismatches.extend(bad)
                max_abs = max(max_abs, delta)
    elif isinstance(a, (float, int)) and not isinstance(a, bool) and isinstance(b, (float, int)):
        max_abs = abs(float(a) - float(b))
        if not np.isclose(a, b, rtol=1e-12, atol=1e-12):
            mismatches.append(path + ': numeric mismatch')
    elif a != b:
        mismatches.append(path + ': exact-value mismatch')
    return mismatches, max_abs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--zip', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    if not (root / 'review_check.py').is_file():
        raise ValueError('--root must contain the original review_check.py and MANIFEST.json')
    if output.is_relative_to(root):
        raise ValueError('Output must be outside the original package to preserve its manifest')
    if output.exists():
        raise FileExistsError('Refusing to overwrite existing audit: ' + str(output))
    sys.path.insert(0, str(root / 'PRL/src'))
    spec = importlib.util.spec_from_file_location('review_check', root / 'review_check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from prl.verification.ventricle_3d import load_arrays, state_audit, kinematics, extra_points
    from prl.verification.mesh_equivalence import compare
    out = {
        'scope': 'saved-evidence reanalysis using supplied independent NumPy verifier plus additional diagnostics; no independent FEM solve',
        'not_run': ['FEniCSx production solves', 'Gmsh', 'MSH parser', 'notebooks', 'complete regression suite'],
        'environment': {'python': platform.python_version(), 'numpy': np.__version__},
        'integrity': module.check_integrity(root), 'states': {}, 'source_sha256': {}
    }
    if args.zip:
        archive = args.zip.resolve()
        out['zip_sha256'] = digest(archive)
        with zipfile.ZipFile(archive) as z:
            out['zip_crc_bad_member'] = z.testzip()
            total = sum(i.file_size for i in z.infolist())
            figures = sum(i.file_size for i in z.infolist() if '/figures/' in i.filename)
            out['archive_sizes'] = {'zip_bytes': archive.stat().st_size,
                'entries': len(z.infolist()), 'uncompressed_bytes': total,
                'figure_directory_bytes': figures,
                'figure_directory_fraction': figures / total,
                'caution': 'Storage ratio, not labor-time ratio; figures include reproducibility data.'}
    first = root / 'PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918'
    cfg = json.loads((first / 'configuration.json').read_text(encoding='utf-8'))
    tracked = [root / 'review_check.py', root / 'PRL/src/prl/verification/ventricle_3d.py',
               root / 'PRL/src/prl/verification/mesh_equivalence.py', first / 'configuration.json']
    for name, folder in [('M0', 'retained'), ('M1', 'raw')]:
        mesh_file = first / folder / f'{name}_mesh.npz'
        state_file = first / folder / f'{name}_state_pressure_1.npz'
        meta_file = first / folder / f'{name}_state_pressure_1.json'
        tracked += [mesh_file, state_file, meta_file]
        data = load_arrays(mesh_file)
        state = load_arrays(state_file)
        meta = json.loads(meta_file.read_text(encoding='utf-8'))
        audit = state_audit(data, state, meta, cfg)
        if audit['status'] != 'failed' or audit['failed_checks'] != ['local_volume']:
            raise ValueError(f'Unexpected original verdict for {name}: {audit}')
        F, J, _, det, bary, vertices = kinematics(data, state['u'], data['qpoints'])
        weights = det[:, None] * data['qweights']
        volume = weights.sum()
        pressure_dofs = state['pressure'].reshape(-1)
        pressure = np.einsum('qa,ca->cq', bary, pressure_dofs[data['pressure_cells']])
        defect = J - 1 - pressure / cfg['kappa']
        extra = extra_points()
        _, Je, _, _, be, _ = kinematics(data, state['u'], extra)
        pe = np.einsum('qa,ca->cq', be, pressure_dofs[data['pressure_cells']])
        re = Je - 1 - pe / cfg['kappa']
        def rms(x):
            return float(np.sqrt(np.sum(weights * x * x) / volume))
        near = np.any(np.abs(vertices[:, :, 2]) < 1e-12, axis=1)
        max_by_cell = np.maximum(abs(J - 1).max(axis=1), abs(Je - 1).max(axis=1))
        bad = max_by_cell > .01
        peak = np.unravel_index(abs(Je - 1).argmax(), Je.shape)
        Eiso = float(np.sum(weights * (cfg['mu'] / 2 * (
            np.sum(F * F, axis=(-1, -2)) * J**(-2 / 3) - 3))))
        Eproj = float(np.sum(weights * pressure**2 / (2 * cfg['kappa'])))
        Efull = float(np.sum(weights * cfg['kappa'] / 2 * (J - 1)**2))
        Edefect = float(np.sum(weights * cfg['kappa'] / 2 * defect**2))
        diag = {'quadrature_points_per_cell': len(data['qpoints']),
            'extra_points_per_cell': len(extra), 'solid_reference_volume': float(volume),
            'max_abs_pressure_coefficient': float(abs(pressure_dofs).max()),
            'max_abs_p_over_kappa_at_q_and_extra': float(max(abs(pressure).max(), abs(pe).max()) / cfg['kappa']),
            'rms_J_minus_one': rms(J - 1), 'rms_p_over_kappa': rms(pressure / cfg['kappa']),
            'rms_projection_defect': rms(defect),
            'max_abs_projection_defect': float(max(abs(defect).max(), abs(re).max())),
            'weighted_mean_J_minus_one': float(np.sum(weights * (J - 1)) / volume),
            'weighted_mean_defect': float(np.sum(weights * defect) / volume),
            'l2_projection_cross_term': float(np.sum(weights * defect * pressure / cfg['kappa'])),
            'bad_cells': int(bad.sum()), 'bad_cells_near_base': int((bad & near).sum()),
            'bad_cells_by_layer': {str(k): int((bad & (data['layers'] == k)).sum()) for k in [1, 2, 3]},
            'fraction_solid_volume_in_bad_cells': float(weights[bad].sum() / volume),
            'bad_volume_caution': 'Volume of cells containing a violating sample, not exact volume of the violating subset.',
            'away_from_base_max_abs_J_minus_one': float(max_by_cell[~near].max()),
            'base_region_caution': 'Vertex-based adjacency; physical width changes with mesh.',
            'at_peak_extra_point': {'cell': int(peak[0]), 'point': int(peak[1]),
                'J_minus_one': float(Je[peak] - 1), 'p_over_kappa': float(pe[peak] / cfg['kappa']),
                'projection_defect': float(re[peak]), 'layer': int(data['layers'][peak[0]]),
                'reference_point': (be[peak[1]] @ vertices[peak[0]]).tolist()},
            'volumetric_energy_diagnostic': {'isochoric_energy': Eiso,
                'projected_volumetric_energy': Eproj, 'pointwise_penalty_energy': Efull,
                'projection_defect_penalty': Edefect, 'orthogonal_split_error': Efull - Eproj - Edefect,
                'caution': 'Diagnostic decomposition, not continuum solution error or proof of instability.'},
            'solver_elapsed_seconds_from_original_metadata': meta.get('elapsed_seconds'),
            'original_snes_iterations': meta.get('iterations')}
        out['states'][name] = {'original_scope_audit': audit, 'additional_diagnostics': diag}
    candidate = root / 'PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918'
    ref_file = candidate / 'input/M1_geometry.npz'
    cand_file = candidate / 'offline/candidate_geometry.npz'
    saved_file = candidate / 'offline/mesh_comparison.json'
    tracked += [ref_file, cand_file, saved_file]
    report, _ = compare(load_arrays(ref_file), load_arrays(cand_file))
    saved = json.loads(saved_file.read_text(encoding='utf-8'))
    mismatches, max_error = compare_nested(report, saved)
    out['candidate_offline_reaudit'] = {'scope': 'saved NPZ only; no MSH parser or new mesh/FEM run',
        'report_matches_within_tolerance': not mismatches, 'comparison_rtol': 1e-12,
        'comparison_atol': 1e-12, 'max_abs_numeric_difference': max_error,
        'mismatches': mismatches, 'report': report}
    for path in tracked:
        out['source_sha256'][path.relative_to(root).as_posix()] = digest(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(out, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'output': str(output), 'integrity': out['integrity'],
        'M0_status': out['states']['M0']['original_scope_audit']['status'],
        'M1_status': out['states']['M1']['original_scope_audit']['status'],
        'candidate_report_matches': not mismatches}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, ImportError, zipfile.BadZipFile) as error:
        print(f'Audit failed: {error}', file=sys.stderr)
        raise SystemExit(1)
