"""Read-only science analysis of a stopped batch; writes new delivery files only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
from prl.runs.fenicsx_runtime import save_json
from prl.runs.fenicsx_ring import digest
from prl.verification.ventricle_3d import load_arrays,kinematics,extra_points
from prl.verification.mixed_cube import verify


def describe_iterate(data,state):
    """Keep production and extra sampling separate; nonpositive J is evidence."""
    if not np.array_equal(state['mixed_state'][data['mixed_u_map']],state['u'].ravel()):
        raise ValueError('Saved iterate displacement mapping drift')
    if not np.array_equal(state['mixed_state'][data['mixed_p_map']],state['pressure']):
        raise ValueError('Saved iterate pressure mapping drift')
    report={'maximum_nodal_displacement':float(np.linalg.norm(state['u'],axis=1).max())}
    arrays={}
    for label,points in [('production',data['qpoints']),('extra',extra_points())]:
        _,J,_,_,bary,vertices=kinematics(data,state['u'],points)
        if not np.isfinite(J).all():
            raise ValueError('Nonfinite persisted-state kinematics')
        cell,point=np.unravel_index(np.argmin(J),J.shape)
        report[label]={'minimum_J':float(J.min()),'maximum_J':float(J.max()),
            'nonpositive_points':int((J<=0).sum()),'cells_with_nonpositive_J':int(np.any(J<=0,axis=1).sum()),
            'peak_cell_id':int(cell),'peak_reference_xyz':(bary[point]@vertices[cell]).tolist()}
        arrays[label+'_cell_minimum_J']=J.min(axis=1)
    report['valid_at_sampled_points']=min(report['production']['minimum_J'],report['extra']['minimum_J'])>0
    return report,arrays


def analyze(root):
    root=Path(root)
    config=json.loads((root/'configuration.json').read_text())
    summary=json.loads((root/'summary.json').read_text())
    controls=config['schema']=='prl.mixed_cube_controls.v1'
    failure=json.loads((root/'failure.json').read_text()) if (root/'failure.json').exists() else None
    readback=verify(root)
    if readback['status']!='passed':
        raise ValueError('Completed-state independent readback failed')
    rows=[]; iterates={}; derived={}
    for case in config['cases']:
        name=case['name']; result=summary['cases'].get(name)
        row={**case,'equilibrium':'not_run','qualification':'not_run'}
        if result:
            group=('isochoric' if case['kind']=='isochoric_mms' else str(int(case['kappa'])))
            qualification=(summary['convergence']['groups'][group]['status']
                if case['kind'] in {'mms','isochoric_mms'} else result['status'])
            row.update(equilibrium=result['status'],metrics=result['metrics'],
                DOF=result['cost']['mixed_dofs'],tetrahedra=result['cost']['tetrahedra'],
                solver_seconds=result['cost']['elapsed_seconds'],iterations=result['cost']['iterations'],
                qualification=qualification)
        elif failure and failure['case']==name:
            row.update(equilibrium='failed',reason='safety-stop; no valid terminal equilibrium')
        mesh_path=root/'raw'/f'{name}_mesh.npz'
        if mesh_path.exists():
            data=load_arrays(mesh_path)
            states=[]
            history=json.loads((root/'iterates'/name/'history.json').read_text()) if (root/'iterates'/name/'history.json').exists() else []
            for entry in history:
                index=entry['iteration']; path=root/'iterates'/name/f'iterate_{index:03d}.npz'
                saved=load_arrays(path); detail,arrays=describe_iterate(data,saved)
                minimum=min(detail['production']['minimum_J'],detail['extra']['minimum_J'])
                if abs(minimum-entry['minimum_sampled_J'])>1e-11:
                    raise ValueError('Monitor versus independent Jacobian drift')
                states.append({**entry,**detail})
                if failure and failure['case']==name:
                    derived.update({f'{name}_{index}_{key}':value for key,value in arrays.items()})
            iterates[name]=states
        rows.append(row)
    limits=['Sampled positive J is not proof of global injectivity.',
        'kappa-dependent manufactured loads are not a fixed-load locking test.',
        'Ordinary equilibrium/weak residual pass does not establish field accuracy.']
    if controls:
        limits += ['Zero exact pressure has no defined relative pressure error or order.',
            'The controls change the exact displacement field too; they are not a pressure-only matched causal test.',
            'Original eight-case and ventricular failures remain unchanged.']
    elif failure:
        limits.append('The interrupted case is not a qualified equilibrium; unattempted cases remain not_run.')
    report={'status':summary['status'],'scope':('four-control defined gates' if controls else 'benchmark qualification')+', not ventricular or biological validation',
        'cases':rows,'convergence':summary['convergence'],'completed_equilibria':len(summary['cases']),
        'SNES_calls':summary['attempted_solves'],'container_invocations':1,'automatic_retries':0,
        'failed_case':failure['case'] if failure else None,'iterate_diagnostics':iterates,
        'completed_state_readback':readback['status'],'original_ventricular_gate':'failed_unchanged',
        'native_interface_retest':'passed' if all(row['equilibrium']=='passed' for row in rows[:2]) else 'unknown',
        'limits':limits}
    return report,derived,readback


def deliver(workspace,root):
    workspace=Path(workspace); root=Path(root)
    if (root/'delivery_analysis.json').exists() or (root/'manifest.json').exists():
        raise FileExistsError('Create-only delivery; no overwrite or scientific replay')
    report,arrays,readback=analyze(root)
    save_json(root/'delivery_analysis.json',report)
    save_json(root/'delivery_readback.json',readback)
    np.savez_compressed(root/'delivery_arrays.npz',**arrays)
    refs=json.loads((root/'protected_inputs.json').read_text())
    assert all(digest(path)==value for path,value in refs['files'].items())
    sources=json.loads((root/'source_hashes.json').read_text())
    assert all(digest(root/'sources_at_execution'/name)==value for name,value in sources.items())
    target=root/'delivery_sources'; target.mkdir(exist_ok=False)
    copies={'analysis.py':Path(__file__),'render.py':workspace/'src/prl/rendering/mixed_cube.py',
        'style.py':Path('C:/Users/chenb/.codex/skills/cb-plot-unified-style/assets/cb_plot_unified_style.py')}
    for name,path in copies.items():
        shutil.copy2(path,target/name)
    save_json(root/'delivery_source_hashes.json',{name:digest(path) for name,path in copies.items()})
    os.environ['MPLCONFIGDIR']=str(root/'.plot_cache')
    specification=importlib.util.spec_from_file_location('batch_style',target/'style.py')
    style=importlib.util.module_from_spec(specification); sys.modules[specification.name]=style
    specification.loader.exec_module(style)
    from prl.rendering.mixed_cube import draw_batch
    outputs=draw_batch(root,style)
    command=[sys.executable,'-B','-X','utf8',
        'C:/Users/chenb/.codex/skills/cb-plot-unified-style/scripts/validate_cb_plot_style.py',outputs['manifest']]
    checked=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=30)
    save_json(root/'publication_style_check.json',{'status':'passed' if checked.returncode==0 else 'failed',
        'command':command,'stdout':checked.stdout,'stderr':checked.stderr,'exit_code':checked.returncode,
        'scope':'publication 600dpi check; accepted exploratory figure is 160dpi, not publication final'})
    save_json(root/'delivery_protection.json',{'status':'passed','protected_files':len(refs['files']),
        'preexisting_dirty_files':refs['preexisting_dirty_files'],'original_source_snapshots':len(sources),
        'completed_states_independently_verified':len(readback['cases']),
        'monitored_iterates_independently_verified':sum(len(x) for x in report['iterate_diagnostics'].values()),
        'additional_FEM_solves':0,'GPU':0,'automatic_retries':0})
    print(json.dumps({'scope':'offline delivery','status':'passed','science':report['status'],
        'equilibria':report['completed_equilibria'],'attempted_SNES':report['SNES_calls'],'figure':outputs},indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path); parser.add_argument('--workspace',type=Path,default=Path.cwd())
    args=parser.parse_args(); deliver(args.workspace,args.root)
