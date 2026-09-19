"""Offline v03 evidence: guarded paths, same-mesh interpolation and unchanged gates."""
import json
from pathlib import Path
import numpy as np
from prl.runs.mixed_cube_delivery import analyze
from prl.verification.positive_j import audit_paths,path_minimum
from prl.verification.mixed_cube import exact_fields,error_metrics
from prl.verification.ventricle_3d import load_arrays,kinematics,extra_points


def inspect_rejected(root,case):
    """Read the final rejected direction without rerunning the production guard."""
    root=Path(root); folder=root/'iterates'/case
    failure=json.loads((folder/'guard_failure.json').read_text())
    saved=load_arrays(folder/f'candidate_{failure["sequence"]:03d}.npz')
    data=load_arrays(root/'raw'/f'{case}_mesh.npz')
    points=np.concatenate((data['qpoints'],extra_points()))
    current=saved['current_mixed']; direction=saved['direction_mixed']
    u=current[data['mixed_u_map']].reshape(-1,3)
    step=direction[data['mixed_u_map']].reshape(-1,3)
    base=kinematics(data,u,points)[0]; increment=kinematics(data,u-step,points)[0]-base
    config=json.loads((root/'configuration.json').read_text())
    trials=[]
    for halves in range(config['trial_guard']['max_halvings']+1):
        scale=2.**(-halves); minimum,error=path_minimum(base,scale*increment)
        trials.append({'scale':scale,'independent_path_minimum_J':minimum,'fit_error':error})
    last=load_arrays(sorted(folder.glob('iterate_*.npz'))[-1])
    return {'case':case,'sequence':failure['sequence'],'last_valid_minimum_J':float(np.linalg.det(base).min()),
        'candidate_base_equals_last_accepted':bool(np.array_equal(current,last['mixed_state'])),
        'last_valid_maximum_nodal_displacement':float(np.linalg.norm(u,axis=1).max()),
        'trials':trials,'negative_even_at_smallest_allowed_scale':trials[-1]['independent_path_minimum_J']<0,
        'scope':'rejected candidate, never an accepted state or equilibrium'}


def analyze_guarded(root,previous):
    root=Path(root); previous=Path(previous)
    report,arrays,readback=analyze(root)
    paths=audit_paths(root)
    if paths['status']!='passed':
        raise ValueError('Independent guarded-path audit did not pass')
    precision=[]
    for row in report['cases']:
        if row['kind']!='mms' or 'metrics' not in row:
            continue
        name=row['name']; data=load_arrays(root/'raw'/f'{name}_mesh.npz')
        interpolated={'u':exact_fields(data['coordinates'],'mms',row['kappa'])['u'],
            'pressure':exact_fields(data['pressure_coordinates'],'mms',row['kappa'])['pressure']}
        metrics,_=error_metrics(data,interpolated,row)
        entry={'case':name,'n':row['n'],'kappa':row['kappa'],'finite_element':row['metrics'],
            'interpolated_exact_field':metrics,'equilibrium':row['equilibrium'],
            'scope':'nodal interpolation is not an equilibrium or a best-approximation lower bound'}
        old=previous/'raw'/f'{name}_audit.json'
        if old.exists():
            original=json.loads(old.read_text())['metrics']
            entry['v02_metrics']=original
            entry['v02_metric_maximum_delta']=max(abs(value-original[key]) for key,value in row['metrics'].items()
                if value is not None and key in original and original[key] is not None)
        precision.append(entry)
    report.update(path_audit_status=paths['status'],path_candidates=len(paths['candidates']),
        accepted_steps_checked=paths['accepted_steps_checked'],
        reduced_candidates=sum(row['scale']<1 for row in paths['candidates']),precision=precision,
        scope='trial-path safety and unchanged field qualification; not ventricle or biology')
    if report['failed_case'] and (root/'iterates'/report['failed_case']/'guard_failure.json').exists():
        report['rejected_candidate']=inspect_rejected(root,report['failed_case'])
    return report,arrays,readback,paths


def deliver(workspace,root,previous):
    """Create offline deliverables only; no native/Docker/solver invocation."""
    import importlib.util
    import os
    import shutil
    import sys
    from prl.runs.fenicsx_runtime import save_json
    from prl.runs.fenicsx_ring import digest
    workspace=Path(workspace); root=Path(root)
    if (root/'delivery_analysis.json').exists() or (root/'manifest.json').exists():
        raise FileExistsError('Create-only offline delivery')
    report,arrays,readback,paths=analyze_guarded(root,previous)
    save_json(root/'delivery_analysis.json',report)
    save_json(root/'delivery_readback.json',readback)
    save_json(root/'path_readback.json',paths)
    np.savez_compressed(root/'delivery_arrays.npz',**arrays)
    references=json.loads((root/'protected_inputs.json').read_text())
    sources=json.loads((root/'source_hashes.json').read_text())
    if not all(digest(path)==value for path,value in references['files'].items()):
        raise ValueError('Protected evidence drift')
    if not all(digest(root/'sources_at_execution'/name)==value for name,value in sources.items()):
        raise ValueError('Execution snapshot drift')
    target=root/'delivery_sources'; target.mkdir(exist_ok=False)
    copies={'analysis.py':Path(__file__),'base_analysis.py':workspace/'src/prl/runs/mixed_cube_delivery.py',
        'render.py':workspace/'src/prl/rendering/mixed_cube.py',
        'path_verifier.py':workspace/'src/prl/verification/positive_j.py',
        'style.py':Path('C:/Users/chenb/.codex/skills/cb-plot-unified-style/assets/cb_plot_unified_style.py')}
    for name,path in copies.items():
        shutil.copy2(path,target/name)
    save_json(root/'delivery_source_hashes.json',{name:digest(path) for name,path in copies.items()})
    os.environ['MPLCONFIGDIR']=str(root/'.plot_cache')
    specification=importlib.util.spec_from_file_location('guard_style',target/'style.py')
    style=importlib.util.module_from_spec(specification); sys.modules[specification.name]=style
    specification.loader.exec_module(style)
    from prl.rendering.mixed_cube import draw_batch
    figure=draw_batch(root,style)
    save_json(root/'delivery_integrity.json',{'status':'passed','protected_files':len(references['files']),
        'preexisting_dirty_files':references['preexisting_dirty_files'],'execution_source_snapshots':len(sources),
        'equilibria_verified':report['completed_equilibria'],'accepted_states_verified':sum(len(x) for x in report['iterate_diagnostics'].values()),
        'accepted_paths_verified':paths['accepted_steps_checked'],'rejected_direction_verified':bool(report.get('rejected_candidate')),
        'additional_solves':0,'GPU':0,'automatic_retries':0})
    print(json.dumps({'delivery':'passed','science':report['status'],'path_audit':paths['status'],
        'rejected':report.get('rejected_candidate'),'precision':report['precision'],'figure':figure},indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path); parser.add_argument('previous',type=Path)
    parser.add_argument('--workspace',type=Path,default=Path.cwd())
    args=parser.parse_args(); deliver(args.workspace,args.root,args.previous)
