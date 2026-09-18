"""Portable, read-only checks. Never starts a mesher, FEM solver, or Notebook."""
import argparse
import ast
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ('href', 'src') and value)


def check_integrity(root, require_manifest=True):
    root = Path(root).resolve()
    checked = 0
    if require_manifest:
        expected = read_json(root / 'MANIFEST.json')['files']
        wanted = {item['path'] for item in expected} | {'MANIFEST.json'}
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if actual != wanted:
            raise ValueError({'missing': sorted(wanted - actual), 'unexpected': sorted(actual - wanted)})
        for entry in expected:
            path = (root / entry['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError('Invalid manifest path: ' + entry['path'])
            if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
                raise ValueError('Manifest mismatch: ' + entry['path'])
        checked = len(expected)
    provenance = read_json(root / 'PROVENANCE.json')
    for entry in provenance['copied_files']:
        if digest(root / entry['destination']) != entry['source_sha256']:
            raise ValueError('Copy identity mismatch: ' + entry['destination'])
    python_files = list((root / 'PRL' / 'src').rglob('*.py'))
    for path in python_files:
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    links = LocalLinks()
    links.feed((root / '00_评审入口.html').read_text(encoding='utf-8'))
    for link in links.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            raise ValueError('Review portal must be entirely local: ' + link)
        if not parsed.path:
            continue
        path = (root / unquote(parsed.path)).resolve()
        if not path.is_relative_to(root) or not path.exists():
            raise ValueError('Broken/escaping review portal link: ' + link)
    for stage in provenance['stages']:
        folder = root / stage['destination']
        selection = read_json(folder / 'SELECTION.json')
        entries = read_json(folder / 'SOURCE_MANIFEST.json')['files']
        selected = {item['original_path'] for item in selection['selected']}
        omitted = {item['path'] for item in selection['omitted']}
        if selected & omitted or selected | omitted != {item['path'] for item in entries}:
            raise ValueError('Incomplete source selection ledger: ' + stage['name'])
        for entry in selection['selected']:
            if digest(folder / entry['package_path']) != entry['sha256']:
                raise ValueError('Source selection identity mismatch: ' + entry['original_path'])
        for entry in selection['omitted']:
            if 'identical_copy_in_package' in entry:
                if digest(root / entry['identical_copy_in_package']) != entry['sha256']:
                    raise ValueError('Deduplicated evidence mismatch: ' + entry['path'])
    return {'status': 'passed', 'manifest_files_checked': checked,
            'copied_source_files_checked': len(provenance['copied_files']),
            'core_python_syntax_checked': len(python_files), 'portal_links_checked': len(links.links),
            'scientific_status_changed': False, 'notebook_execution': 'not_run'}


def check_numerics(root):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / 'PRL' / 'src'))
    import numpy as np
    from prl.verification.ventricle_3d import load_arrays, state_audit
    from prl.verification.saved_gmsh import load_saved
    from prl.verification.mesh_equivalence import compare

    evidence = root / 'PRL-results' / 'ventricle_fem'
    first = evidence / 'f6s2d1_3d_fine_pressure_v01_20260918'
    config = read_json(first / 'configuration.json')
    results = {}
    for name, folder in [('M0', 'retained'), ('M1', 'raw')]:
        data = load_arrays(first / folder / (name + '_mesh.npz'))
        state = load_arrays(first / folder / (name + '_state_pressure_1.npz'))
        metadata = read_json(first / folder / (name + '_state_pressure_1.json'))
        result = state_audit(data, state, metadata, config)
        if result['status'] != 'failed' or result['failed_checks'] != ['local_volume']:
            raise ValueError('Unexpected pressure verdict: ' + name + ' ' + str(result))
        original = read_json(first / 'summary.json')['pressure_states'][name]
        for key in ['max_abs_J_minus_one', 'cavity_volume', 'max_displacement']:
            if not np.isclose(result[key], original[key], rtol=1e-11, atol=1e-12):
                raise ValueError('Pressure evidence drift: ' + name + ' ' + key)
        results[name] = {key: result[key] for key in ['status', 'failed_checks',
            'max_abs_J_minus_one', 'volume_change', 'max_displacement', 'independent_free_force']}
    candidate_root = evidence / 'f6s2d2b_unstructured_v01_20260918'
    reference = load_arrays(candidate_root / 'input' / 'M1_geometry.npz')
    candidate = load_saved(candidate_root / 'candidate.msh', reference)
    result, _ = compare(reference, candidate)
    original = read_json(candidate_root / 'offline' / 'mesh_comparison.json')
    if result['status'] != 'failed' or result['failed_checks'] != ['global_q05_improves_5percent']:
        raise ValueError('Unexpected candidate quality verdict')
    if result['checks'] != original['checks']:
        raise ValueError('Candidate topology or quality checks drifted')
    for region in ['all', 'thin_clamp']:
        for metric in ['min', 'p05', 'median']:
            actual = result['candidate']['regions'][region]['q_radius'][metric]
            saved = original['candidate']['regions'][region]['q_radius'][metric]
            if not np.isclose(actual, saved, rtol=1e-11, atol=1e-12):
                raise ValueError('Candidate shape distribution drifted')
    results['candidate'] = {'status': result['status'], 'failed_checks': result['failed_checks'],
        'same_surfaces': result['checks']['identical_surface_coordinates_and_adjacency'],
        'tetrahedra': result['candidate']['tetrahedra'],
        'q05': result['candidate']['regions']['all']['q_radius']['p05'],
        'scientific_pressure_gate': 'not_run'}
    return {'evidence_reproduction': 'passed', 'scientific_pass': False, 'results': results,
            'new_FEM_solves': 0, 'new_mesher_calls': 0, 'notebook_execution': 'not_run'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--numerics', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    report = {'integrity': check_integrity(root)}
    if args.numerics:
        report['numerics'] = check_numerics(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
