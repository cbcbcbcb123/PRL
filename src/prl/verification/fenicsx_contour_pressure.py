"""Independent four-state contour qualification; no production FEM imports."""
import hashlib
import json
from pathlib import Path

import numpy as np

from .fenicsx_contour import geometry_audit, SOURCE_SHA
from .fenicsx_ring import load_arrays, pressure_basis, state_audit
from .fenicsx_pressure import diagnostic_state, same_displacement_mesh, saved_iterates_audit, volume_projection

GEOMETRY_HASHES = {
    'M0': '157265c350367a95f36c40c5951117272ceeccac9f273ec65e5000eb81627f65',
    'M1': '90afab96f7294480282e9b9e095b970e28ce79b1dbb580ddfe793655a37b3db2',
}


def scope_checks(config, qualified):
    return {
        'exact_four_state_scope': config['objects'] == ['contour'] and config['meshes'] == [{'name':'M0'}, {'name':'M1'}]
            and config['passive_loads'] == [0., .02] and config['maximum_equilibrium_solves'] == 4,
        'same_qualified_physics_solver': all(config[k] == qualified[k] for k in
            ['mu','kappa','radii','quadrature_degree','pressure_space','solver','active_peak']),
        'no_active_no_ring': config['geometry_kind'] == 'image_polygon' and config['active_peak'] == 0.,
        'same_resources': config['resources'] == {'seconds':1200,'threads':1,'gpu':0,'automatic_retries':0},
        'retain_actual_iterates': config.get('retain_solver_iterates') is True,
    }


def contour_state_audit(mesh, state, metadata, config):
    report = diagnostic_state(mesh, state, metadata, config)
    solver = metadata.get('linear_solver', {})
    keys = ['ksp_reason','pc_failed_reason','mumps_infog_1','mumps_infog_2','mumps_icntl_14']
    if metadata['iterations'] == 0:
        report['factorization_status'] = 'not_run'
        report['checks']['zero_updates_no_factor'] = solver.get('status') == 'not_run' and all(k in solver and solver[k] is None for k in keys)
    else:
        reason = solver.get('ksp_reason')
        report['checks']['actual_MUMPS_factor'] = (isinstance(reason, int) and reason > 0
            and solver.get('status') == 'passed' and solver.get('pc_failed_reason') == 0
            and solver.get('mumps_infog_1') == 0 and solver.get('mumps_icntl_14') == 100)
        report['factorization_status'] = 'passed' if report['checks']['actual_MUMPS_factor'] else 'failed'
    if float(state['load']) == 0.:
        report['checks']['zero_stress'] = bool(np.max(np.abs(state['stress'])) <= 2e-7)
    report['status'] = 'passed' if all(report['checks'].values()) else 'failed'
    return report


def completion_scope_checks(config, qualified):
    unchanged = [key for key in qualified if key not in ['schema_version','passive_loads','maximum_equilibrium_solves','scope']]
    return {
        'exact_six_remaining': config.get('passive_loads') == [0.,.02,.04,.06,.08]
            and config.get('reused_loads') == [0.,.02] and config.get('new_loads') == [.04,.06,.08]
            and config.get('maximum_equilibrium_solves') == 6,
        'qualified_scope_unchanged': all(config.get(key) == qualified[key] for key in unchanged),
        'two_contour_meshes_no_active': config.get('meshes') == [{'name':'M0'},{'name':'M1'}]
            and config.get('objects') == ['contour'] and config.get('geometry_kind') == 'image_polygon'
            and config.get('active_peak') == 0. and config.get('pressure_space') == 'DG2',
        'single_cpu_zero_gpu_no_retries': config.get('resources') == {'seconds':1200,'threads':1,'gpu':0,'automatic_retries':0},
    }


def same_mixed_mesh(actual, retained):
    """Exact DOF identity is required before reusing a mixed vector, not just geometry."""
    required = {'coordinates','cells','layers','pressure_coordinates','pressure_cells','inner_edges',
        'fixed','qpoints','qweights','mixed_u_map','mixed_p_map','pressure_space'}
    return set(actual) == set(retained) and required <= set(actual) and all(
        np.array_equal(actual[key],retained[key]) for key in actual)


def response_comparison(coarse, fine):
    absolute = abs(coarse-fine); relative = absolute/max(abs(coarse),abs(fine),1e-15)
    return {'M0_cavity_change':coarse,'M1_cavity_change':fine,'absolute':absolute,'relative':relative,
        'status':'passed' if absolute <= .002 and relative <= .05 else 'failed'}


def verify_contour_passive(root):
    root = Path(root)
    config = json.loads((root/'configuration.json').read_text())
    qualified = json.loads((root/'prerequisite/configuration.json').read_text())
    parent = json.loads((root/'prerequisite/post_verification.json').read_text())
    checks = completion_scope_checks(config,qualified)
    checks['parent_qualified'] = parent['status'] == 'passed' and all(parent['checks'].values())
    checks['source_identity'] = hashlib.sha256((root/'geometry_source.npz').read_bytes()).hexdigest() == SOURCE_SHA
    identities = json.loads((root/'input_identities.json').read_text())
    checks['input_copies'] = all(hashlib.sha256((root/path).read_bytes()).hexdigest() == item['sha256']
        for path,item in identities.items())
    source = load_arrays(root/'geometry_source.npz')
    cases, geometry, iterates, comparisons = {}, {}, {}, {}
    for name in ['M0','M1']:
        cases[name],iterates[name] = {},{}
        geompath = root/'input'/f'{name}_input_mesh.npz'
        checks[name+'_input_hash'] = hashlib.sha256(geompath.read_bytes()).hexdigest() == GEOMETRY_HASHES[name]
        geometry[name] = geometry_audit(load_arrays(geompath),source)
        checks[name+'_geometry'] = geometry[name]['status'] == 'passed'
        retained = load_arrays(root/'retained'/f'{name}_mesh.npz')
        newpath = root/'raw'/f'{name}_mesh.npz'
        mesh = load_arrays(newpath) if newpath.exists() else retained
        pressure_basis(mesh)
        checks[name+'_exact_restart_map'] = same_mixed_mesh(mesh,retained)
        tangentpath = root/('raw' if newpath.exists() else 'retained')/f'{name}_tangent.json'
        tangent = json.loads(tangentpath.read_text()) if tangentpath.exists() else {}
        checks[name+'_tangent'] = all(tangent.get(k,np.inf) <= v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        previous = None
        for index,load in enumerate([0.,.02,.04,.06,.08]):
            reused = index < 2; label = f'passive_{index}'
            path = root/('retained' if reused else 'raw')/f'{name}_state_{label}.npz'
            if not path.exists():
                continue
            state = load_arrays(path); meta = json.loads(path.with_suffix('.json').read_text())
            report = contour_state_audit(mesh,state,meta,config)
            cases[name][label] = report
            checks[f'{name}_{label}_load'] = float(state['load']) == load and float(state['activation']) == 0.
            expected = np.zeros_like(state['mixed_state']) if index == 0 else previous
            checks[f'{name}_{label}_chain'] = expected is not None and np.array_equal(state['initial_mixed'],expected)
            checks[f'{name}_{label}_state'] = report['status'] == 'passed'
            if not reused:
                iteration = saved_iterates_audit(root/'iterates'/f'{name}_{label}',mesh,state,meta,config)
                iterates[name][label] = iteration
                checks[f'{name}_{label}_iterates'] = iteration['status'] == 'passed'
            previous = state['mixed_state']
        checks[name+'_five_states'] = len(cases[name]) == 5
    for index in range(5):
        label = f'passive_{index}'
        if all(label in cases[name] for name in ['M0','M1']):
            comparisons[label] = response_comparison(*[cases[name][label]['cavity_area_change'] for name in ['M0','M1']])
            checks[label+'_mesh_response'] = comparisons[label]['status'] == 'passed'
    allowed = {f'{name}_state_passive_{i}.npz' for name in ['M0','M1'] for i in [2,3,4]}
    checks['no_extra_or_recomputed_states'] = {p.name for p in (root/'raw').glob('*_state_*.npz')} <= allowed
    checks['no_ring_or_microprobe'] = not any((root/name).exists() for name in ['ring','native_probe','runtime_zero_newton'])
    # Ring's detailed progress can be the last native-crash write; keep counters separately.
    progresspath = root/'continuation_ledger.json'
    progress = json.loads(progresspath.read_text()) if progresspath.exists() else {}
    checks['bounded_attempts'] = 0 <= progress.get('attempted_states',0) <= 6
    accepted = sum(record['status']=='passed' for rows in cases.values() for label,record in rows.items() if int(label.split('_')[-1]) >= 2)
    checks['six_new_states_accepted'] = accepted == 6 and progress.get('accepted_states') == 6
    checks['all_mesh_responses'] = len(comparisons) == 5 and all(item['status']=='passed' for item in comparisons.values())
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
        'failed_checks':[k for k,v in checks.items() if not v],'cases':cases,'geometry':geometry,'iterates':iterates,
        'comparison':comparisons,'accepted_new_equilibria':accepted,'reused_equilibria':4,
        'attempted_equilibria':progress.get('attempted_states',0),'controller_accepted_states':progress.get('accepted_states',0),
        'scope':'two original contour meshes, passive only; not hotspot/asymptotic convergence or biological validation',
        'active_contraction':'not_run','three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run','biological_validation':'not_run'}


def verify_contour_pressure(root):
    root = Path(root)
    config = json.loads((root/'configuration.json').read_text())
    qualified = json.loads((root/'prerequisite/configuration.json').read_text())
    prerequisite = json.loads((root/'prerequisite/post_verification.json').read_text())
    checks = scope_checks(config, qualified)
    checks['two_mesh_ring_prerequisite'] = prerequisite['status'] == 'passed' and all(prerequisite['checks'].values())
    checks['source_identity'] = hashlib.sha256((root/'geometry_source.npz').read_bytes()).hexdigest() == SOURCE_SHA
    source = load_arrays(root/'geometry_source.npz')
    cases, geometry, iterates, controls = {}, {}, {}, {}
    for name in ['M0','M1']:
        cases[name], iterates[name] = {}, {}
        geompath = root/'input'/f'{name}_input_mesh.npz'
        checks[name+'_input_hash'] = hashlib.sha256(geompath.read_bytes()).hexdigest() == GEOMETRY_HASHES[name]
        geometry[name] = geometry_audit(load_arrays(geompath), source)
        checks[name+'_geometry'] = geometry[name]['status'] == 'passed'
        oldroot = root/'comparison'/name
        oldmesh = load_arrays(oldroot/'mesh.npz'); oldstate = load_arrays(oldroot/'state.npz')
        old = state_audit(oldmesh, oldstate, json.loads((oldroot/'state.json').read_text()), json.loads((oldroot/'configuration.json').read_text()))
        controls[name] = {'audit':old, 'volume':volume_projection(oldmesh, oldstate, config['kappa'])}
        meshpath = root/'raw'/f'{name}_mesh.npz'
        if not meshpath.exists():
            checks[name+'_two_states'] = False
            continue
        mesh = load_arrays(meshpath)
        checks[name+'_same_displacement_mesh'] = same_displacement_mesh(mesh, oldmesh)
        pressure_basis(mesh)  # Fails closed for wrong basis coordinates/shared DG DOFs.
        positions = mesh['coordinates'][mesh['cells']]
        mids = np.stack(((positions[:,1]+positions[:,2])/2,(positions[:,0]+positions[:,2])/2,(positions[:,0]+positions[:,1])/2), axis=1)
        checks[name+'_P2_mapping'] = bool(np.max(np.abs(positions[:,3:]-mids)) < 1e-12 and abs(mesh['qweights'].sum()-.5) < 1e-13)
        tangentpath = root/'raw'/f'{name}_tangent.json'
        tangent = json.loads(tangentpath.read_text()) if tangentpath.exists() else {}
        checks[name+'_tangent'] = all(tangent.get(k,np.inf) <= v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        previous = None
        for index, load in enumerate([0., .02]):
            label = f'passive_{index}'; path = root/'raw'/f'{name}_state_{label}.npz'
            if not path.exists():
                continue
            state = load_arrays(path); meta = json.loads(path.with_suffix('.json').read_text())
            report = contour_state_audit(mesh, state, meta, config)
            cases[name][label] = report
            iteration = saved_iterates_audit(root/'iterates'/f'{name}_{label}', mesh, state, meta, config)
            iterates[name][label] = iteration
            expected = np.zeros_like(state['mixed_state']) if previous is None else previous
            checks[f'{name}_{label}_load'] = float(state['load']) == load and float(state['activation']) == 0.
            checks[f'{name}_{label}_chain'] = np.array_equal(state['initial_mixed'], expected)
            checks[f'{name}_{label}_state'] = report['status'] == 'passed'
            checks[f'{name}_{label}_iterates'] = iteration['status'] == 'passed'
            previous = state['mixed_state']
            if index == 1:
                report['area_difference_to_failed_CG1'] = report['cavity_area_change'] - old['cavity_area_change']
        checks[name+'_two_states'] = len(cases[name]) == 2
    allowed = {f'{name}_state_passive_{i}.npz' for name in ['M0','M1'] for i in [0,1]}
    checks['no_extra_states'] = {p.name for p in (root/'raw').glob('*_state_*.npz')} <= allowed
    checks['no_ring_or_microprobe'] = not any((root/name).exists() for name in ['ring','native_probe','runtime_zero_newton'])
    comparison = {}
    if all('passive_1' in cases[name] for name in ['M0','M1']):
        a,b = [cases[name]['passive_1']['cavity_area_change'] for name in ['M0','M1']]
        comparison = {'M0_cavity_change':a,'M1_cavity_change':b,'absolute':abs(a-b),'relative':abs(a-b)/max(abs(a),abs(b),1e-15)}
    checks['mesh_response'] = bool(comparison) and comparison['absolute'] <= .002 and comparison['relative'] <= .05
    progress_path = root/'progress.json'
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    checks['bounded_attempts'] = progress.get('attempted_states',0) <= 4
    accepted = sum(record['status']=='passed' for records in cases.values() for record in records.values())
    checks['all_four_accepted'] = accepted == 4 and progress.get('accepted_states') == 4
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
        'failed_checks':[k for k,v in checks.items() if not v], 'cases':cases,'geometry':geometry,
        'iterates':iterates,'retained_failed_CG1':controls,'comparison':comparison,
        'accepted_equilibria':accepted,'attempted_equilibria':progress.get('attempted_states',0),
        'scope':'two contour meshes at zero and first pressure only; not full passive qualification or asymptotic convergence',
        'active_contraction':'not_run','three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run','biological_validation':'not_run'}
