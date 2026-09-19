"""Read back derived arrays, preserve hashes, and publish a small review excerpt."""
import json
from pathlib import Path
import shutil
import numpy as np
from prl.result_store import register_result, result_path
from prl.runs.mixed_cube_load_diagnosis import STAGE, digest, save
from prl.verification.ventricle_3d import load_arrays

workspace = Path.cwd()
root = result_path(workspace, STAGE)
if (root / 'manifest.json').exists():
    raise FileExistsError('Frozen output exists')
review = workspace / 'docs/review' / root.name
if any((review / name).exists() for name in ['diagnostic.png', 'summary.json', 'source_manifest.json']):
    raise FileExistsError('Create-only expert excerpt already exists')
visual = json.loads((root / 'visual_review.json').read_text())
assert visual['status'] == 'passed'
source_map = json.loads((root / 'sources.json').read_text())
assert all(digest(path) == expected for path, expected in source_map['protected_sha256'].items())
summary = json.loads((root / 'summary.json').read_text())
arrays = load_arrays(root / 'derived.npz')
checks = {}
for row in summary['rows']:
    key = row['name']
    mesh = load_arrays(Path(source_map['source']) / 'raw' / (key + '_mesh.npz'))
    free = ~mesh['fixed'].astype(bool)
    pressure = arrays[key + '_exact_pressure_force'][free]
    remainder = arrays[key + '_unrepresented_pressure_force'][free]
    iso = arrays[key + '_exact_iso_force'][free]
    difference = arrays[key + '_production_load_error'][free]
    certificate = row['pressure_certificate']
    checks[key] = all([
        np.isclose(np.linalg.norm(pressure), certificate['pressure_force_norm'], rtol=1e-13, atol=1e-15),
        np.isclose(np.linalg.norm(remainder), certificate['unrepresented_force_norm'], rtol=1e-13, atol=1e-15),
        np.isclose(np.sum(pressure * remainder), certificate['pressure_virtual_work'], rtol=1e-12, atol=1e-18),
        np.isclose(np.linalg.norm(remainder) / np.linalg.norm(iso), row['leakage_to_iso_force_norm_ratio'], rtol=1e-13),
        np.isclose(np.linalg.norm(difference), row['production_load_difference'], rtol=1e-13, atol=1e-18)])
assert all(checks.values())
save(root / 'readback.json', {'status': 'passed', 'checks': checks,
     'scope': 'independent arithmetic readback of stored force vectors, not a second mechanical solve',
     'protected_files_verified': len(source_map['protected_sha256'])})
shutil.copy2(Path(__file__), root / 'source_code/freeze.py')
entries = [{'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}
           for path in sorted(root.rglob('*')) if path.is_file()]
save(root / 'manifest.json', {'status': 'passed', 'scope': 'offline diagnosis evidence; original numerical qualification failed',
                             'files': entries})
manifest_hash = digest(root / 'manifest.json')
register_result(workspace, root, 'passed', manifest_hash)
for name in ['diagnostic.png', 'summary.json']:
    shutil.copy2(root / name, review / name)
save(review / 'source_manifest.json', {'status': 'passed', 'source_package': str(root),
     'source_manifest_sha256': manifest_hash, 'original_v03_manifest_sha256': summary['source_manifest_sha256'],
     'files': [{'path': name, 'bytes': (root / name).stat().st_size, 'sha256': digest(root / name)}
               for name in ['diagnostic.png', 'summary.json']],
     'raw_data_uploaded': False, 'new_equilibrium_solves': 0, 'scientific_qualification': 'failed'})
print(json.dumps({'status': 'passed', 'manifest_sha256': manifest_hash,
     'package_files': len(entries) + 1, 'package_bytes': sum(entry['bytes'] for entry in entries) + (root / 'manifest.json').stat().st_size,
     'preview_sha256': digest(review / 'diagnostic.png'), 'preview_bytes': (review / 'diagnostic.png').stat().st_size}))
