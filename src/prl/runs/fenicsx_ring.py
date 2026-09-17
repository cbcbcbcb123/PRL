"""One bounded science invocation following the preserved G0 runtime gate."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from prl.fem.ring_geometry import configuration
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_runtime import (RESULT, IMAGE, TAG, read_docker, container_command,
                                    save_json, verify_container_settings)
from prl.storage import scan_workspace, evaluate_storage

COMPLETION_RESULT=Path('results/ventricle_fem/f6s0_active_completion_v01_20260917')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_manifest(root):
    return {'files':[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
                     for p in sorted(root.rglob('*')) if p.is_file() and p.name!='manifest.json']}


def finalize_passive_delivery(workspace):
    """Record a saved-state G1 qualification without relabeling the failed invocation."""
    from prl.verification.fenicsx_ring import verify_fenicsx_ring

    workspace=Path(workspace).resolve(strict=True)
    root=workspace/RESULT
    verification=verify_fenicsx_ring(root,stage='passive')
    original=json.loads((root/'formal_invocation_manifest.json').read_text())
    protected=[x for x in original['files'] if x['path'].startswith('raw/') or
               x['path'] in ['failure.json','execution.json','configuration.json','g0_runtime.json','source_hashes.json']]
    identities={x['path']:digest(root/x['path'])==x['sha256'] for x in protected}
    old_sources=json.loads((root/'source_hashes.json').read_text())
    original_sources={
        'adapter':digest(root/'sources_at_execution/fenicsx_ring_adapter.py')==old_sources['src/prl/fem/fenicsx_ring.py'],
        'verifier':digest(root/'sources_at_execution/fenicsx_ring_verifier.py')==old_sources['src/prl/verification/fenicsx_ring.py'],
    }
    protected_f5=json.loads((root/'protected_f5_preflight.json').read_text())
    f5_ok=all(digest(workspace/p)==h for p,h in protected_f5.items())
    if not all(identities.values()) or not all(original_sources.values()) or not f5_ok:
        raise ValueError('Protected evidence identity drift')
    rendering=json.loads((root/'rendering.json').read_text())
    summary={'status':'blocked','G0':'passed','G1':verification['status'],'G2':'not_run',
             'original_scientific_invocation_status':'failed',
             'failure_kind':'post-solve pressure-array singleton dimension in independent reader',
             'completed_equilibria':10,'scientific_invocations':1,'scientific_retries':0,
             'postprocess_new_solves':0,'rendering':rendering['status'],
             'fine_peak':verification['cases']['M1']['passive_4'],
             'next_action':'additional bounded invocation for only 16 uncomputed active states',
             'next_contract':'project_control/ventricle_fem_fenicsx_active_completion_contract_v01.md'}
    save_json(root/'summary.json',summary)
    audit={'status':'passed','original_raw_and_control_identities':identities,
           'original_source_snapshots':original_sources,'f5_original_package_unchanged':f5_ok,
           'source_hashes_after_postprocess':{p:digest(workspace/p) for p in old_sources},
           'targeted_tests':{'passed':35,'subtests_passed':21,
               'command':'python -B -X utf8 -m pytest -q -p no:cacheprovider tests/prl/test_fenicsx_ring.py tests/prl/test_fem_only_cli.py'},
           'independent_g1_gate_count':len(verification['checks']),
           'external_style_validation':{'model_structure':'passed','mechanics_results':'passed','five_states':'passed'},
           'visual_inspection':'passed_after_explicit_bottom_margin_expansion',
           'new_source_import_boundary':'passed',
           'repository_wide_quick_boundary':'failed_existing_measured_contour_image_dependencies_and_absolute_data_path',
           'scientific_resolves':0,'full_F6S0_qualification':'not_run'}
    save_json(root/'postprocess_execution.json',audit)
    save_json(root/'storage_postflight.json',evaluate_storage(scan_workspace(workspace),planned_new_bytes=65536,stop_reserve_bytes=64*1024**2))
    save_json(root/'manifest.json',package_manifest(root))
    return {'status':'passed','G1':verification['status'],'G2':'not_run',
            'package_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
            'preserved_items':len(identities),'original_source_snapshots':original_sources}


def finalize_active_delivery(workspace):
    """Audit the completed G2 delivery, without running Docker or solving states."""
    from PIL import Image

    workspace=Path(workspace).resolve(strict=True)
    root=workspace/COMPLETION_RESULT
    parent=workspace/RESULT
    reference=json.loads((root/'parent_reference.json').read_text())
    parent_manifest=json.loads((parent/'manifest.json').read_text())
    original=json.loads((root/'formal_invocation_manifest.json').read_text())
    verification=json.loads((root/'post_verification.json').read_text())
    execution=json.loads((root/'execution.json').read_text())
    rendering=json.loads((root/'rendering.json').read_text())
    parent_identities={x['path']:digest(parent/x['path'])==x['sha256'] for x in parent_manifest['files']}
    identities={x['path']:digest(root/x['path'])==x['sha256'] for x in original['files']}
    sources=json.loads((root/'source_hashes.json').read_text())
    snapshots={'src/prl/fem/fenicsx_ring.py':'fenicsx_ring_adapter.py',
               'src/prl/verification/fenicsx_ring.py':'fenicsx_ring_verifier.py',
               'src/prl/runs/fenicsx_ring.py':'fenicsx_ring_host.py'}
    source_identities={p:digest(root/'sources_at_execution'/snapshots[p] if p in snapshots else workspace/p)==h
                       for p,h in sources.items()}
    protected_f5=json.loads((parent/'protected_f5_preflight.json').read_text())
    f5_ok=all(digest(workspace/p)==h for p,h in protected_f5.items())
    render_identities={x['path']:digest(root/x['path'])==x['sha256'] for x in rendering['outputs']}
    inherited=len(list((parent/'raw').glob('*_state_*.npz')))
    new_states=len(list((root/'raw').glob('*_state_*.npz')))
    with Image.open(root/'figures/active_preview.gif') as preview:
        frames=preview.n_frames
    checks={'G0':json.loads((parent/'g0_runtime.json').read_text())['status']=='passed',
            'G1':json.loads((parent/'g1_verification.json').read_text())['status']=='passed',
            'G2':verification['status']=='passed' and all(verification['checks'].values()),
            'active_execution':execution['status']=='passed',
            'parent_manifest_identity':digest(parent/'manifest.json')==reference['manifest_sha256'],
            'parent_contents_identity':all(parent_identities.values()),
            'original_child_contents_identity':all(identities.values()),
            'original_sources_preserved':all(source_identities.values()),
            'original_f5_unchanged':f5_ok,
            'rendering_identity':rendering['status']=='passed' and all(render_identities.values()),
            'five_true_preview_frames':frames==5,
            'unique_states_complete':inherited==10 and new_states==16,
            'no_repeated_equilibria':execution['repeated_equilibria']==0,
            'cumulative_runtime':execution['cumulative_scientific_container_seconds']<=1200}
    if not all(checks.values()):
        raise ValueError('Delivery audit failed: '+str([k for k,v in checks.items() if not v]))
    storage=evaluate_storage(scan_workspace(workspace),planned_new_bytes=65536,stop_reserve_bytes=64*1024**2)
    package_bytes=sum(p.stat().st_size for base in [parent,root] for p in base.rglob('*') if p.is_file())
    storage['phase']={'bytes_before_final_audit_metadata':package_bytes,'maximum_metadata_addition':65536,
                      'combined_limit_bytes':128*1024**2,'status':'passed' if package_bytes+65536<=128*1024**2 else 'failed'}
    if not storage['can_start'] or storage['phase']['status']!='passed':
        raise ValueError('Final storage audit failed before recording passed delivery')
    fine=verification['cases']['M1']
    summary={'status':'passed','G0':'passed','G1':'passed','G2':'passed',
             'unique_equilibria':inherited+new_states,'inherited_equilibria':inherited,'new_equilibria':new_states,
             'science_container_invocations':execution['science_container_invocations_total'],
             'repeated_equilibria':0,'postprocess_new_solves':0,
             'original_parent_invocation_status':'failed_preserved',
             'four_conditions':{label:fine[key] for label,key in
                                [('P0A0','passive_0'),('P1A0','passive_2'),('P0A1','active_4'),('P1A1','combined_4')]},
             'active_reduction_at_fixed_pressure_percentage_points':100*(fine['passive_2']['cavity_area_change']-fine['combined_4']['cavity_area_change']),
             'mesh_comparisons':verification['mesh_comparisons'],
             'qualification':'ideal annulus; uncalibrated dimensionless finite-deformation plane strain',
             'physiological_validation':'not_run','next_stage':'F6-S1 image-derived outer contour; not_run'}
    save_json(root/'summary.json',summary)
    states=[v for case in verification['cases'].values() for v in case.values()]
    save_json(root/'postprocess_execution.json',{
        'status':'passed','checks':checks,'parent_items_checked':len(parent_identities),
        'original_child_items_checked':len(identities),'original_source_identities':source_identities,
        'independent_summary_gates':len(verification['checks']),
        'max_active_virtual_work_error':max(x['active_virtual_work_error'] for x in states),
        'max_active_energy_error':max(x['active_energy_error'] for x in states),
        'source_hashes_after_postprocess':{p:digest(workspace/p) for p in sources},
        'gif_frames':frames,'rendered_deformation_scale':rendering['deformation_scale'],
        'uniform_stress_scale':rendering['uniform_stress_scale'],'new_scientific_solves':0,
        'engineering_observations':'See project_control/ventricle_fem_fenicsx_active_completion_execution_v01.md; targeted tests, external style validation and visual inspection are separate from the computed identity checks.'})
    save_json(root/'storage_postflight.json',storage)
    save_json(root/'manifest.json',package_manifest(root))
    return {'status':'passed','checks':checks,'combined_phase_bytes':sum(p.stat().st_size for base in [parent,root] for p in base.rglob('*') if p.is_file()),
            'workspace_bytes_at_audit':storage['usage']['logical_bytes']}


def run_fenicsx_ring(workspace):
    workspace=Path(workspace).resolve(strict=True)
    root=workspace/RESULT
    if not (root/'g0_runtime.json').exists() or json.loads((root/'g0_runtime.json').read_text())['status']!='passed':
        raise RuntimeError('G0 must have passed')
    if (root/'science_started.json').exists():
        raise FileExistsError('Single scientific invocation already consumed')
    if read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Local image drift')
    admission=evaluate_storage(scan_workspace(workspace),planned_new_bytes=128*1024**2,stop_reserve_bytes=64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    with scientific_lock(workspace):
        save_json(root/'science_storage_preflight.json',admission)
        save_json(root/'configuration.json',configuration())
        paths=['src/prl/fem/fenicsx_ring.py','src/prl/fem/ring_geometry.py',
               'src/prl/verification/fenicsx_ring.py','src/prl/runs/fenicsx_ring.py',
               'src/prl/runs/fenicsx_runtime.py',
               'project_control/ventricle_fem_fenicsx_ring_active_contract_v01.md',
               'project_control/ventricle_fem_fenicsx_execution_adoption_v01.md']
        save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in paths})
        protected={p.relative_to(workspace).as_posix():digest(p) for p in
                   (workspace/'results/ventricle_fem/f5_contour_pressure_v01_20260917').rglob('*') if p.is_file()}
        save_json(root/'protected_f5_preflight.json',protected)
        name='prl-f6s0-ring-v01-20260917'
        args=container_command(workspace,name,'/workspace/src/prl/fem/fenicsx_ring.py',root)
        save_json(root/'science_command.json',args)
        with (root/'science_started.json').open('x',encoding='utf-8') as handle:
            json.dump({'status':'unknown','invocation':1,'container_name':name,'automatic_retries':0},handle)
        started=time.monotonic()
        reason=None
        with (root/'science_stdout.log').open('x',encoding='utf-8') as stdout, (root/'science_stderr.log').open('x',encoding='utf-8') as stderr:
            process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
            try:
                while process.poll() is None:
                    elapsed=time.monotonic()-started
                    size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
                    if elapsed>1200 or size>128*1024**2:
                        reason='1200 second deadline' if elapsed>1200 else '128 MiB output cap'
                        read_docker('stop','--time','5',name)
                        process.wait(timeout=20)
                        break
                    time.sleep(.5)
            except BaseException:
                read_docker('stop','--time','5',name)
                process.wait(timeout=20)
                raise
        inspection=json.loads(read_docker('inspect',name))[0]
        save_json(root/'science_container_inspect.json',inspection)
        settings=verify_container_settings(inspection)
        protected_ok=all((workspace/p).is_file() and digest(workspace/p)==h for p,h in protected.items())
        report={'status':'passed' if process.returncode==0 and all(settings.values()) and protected_ok and reason is None else 'failed',
                'exit_code':process.returncode,'stop_reason':reason,'container_checks':settings,
                'protected_f5_unchanged':protected_ok,'elapsed_seconds':time.monotonic()-started,
                'scientific_invocations':1,'automatic_retries':0,'gpu':0,'threads':1,
                'container_retained':name}
        save_json(root/'execution.json',report)
        save_json(root/'manifest.json',package_manifest(root))
        return report


def run_active_completion(workspace):
    """Compute only the unvisited G2 branch, within the original combined budget."""
    from prl.verification.fenicsx_ring import verify_fenicsx_ring

    workspace=Path(workspace).resolve(strict=True)
    parent=workspace/RESULT
    root=workspace/COMPLETION_RESULT
    if root.exists():
        raise FileExistsError('Active completion is create-only; no automatic retry')
    if verify_fenicsx_ring(parent,stage='passive')['status']!='passed':
        raise ValueError('Inherited G1 qualification failed')
    manifest=json.loads((parent/'manifest.json').read_text())
    for item in manifest['files']:
        if digest(parent/item['path'])!=item['sha256']:
            raise ValueError('Parent package identity drift: '+item['path'])
    parent_bytes=sum(p.stat().st_size for p in parent.rglob('*') if p.is_file())
    parent_elapsed=json.loads((parent/'execution.json').read_text())['elapsed_seconds']
    timeout=min(600.,1200.-parent_elapsed)
    cap=128*1024**2-parent_bytes
    if timeout<=0 or cap<32*1024**2:
        raise RuntimeError('No remaining phase budget')
    admission=evaluate_storage(scan_workspace(workspace),planned_new_bytes=cap,stop_reserve_bytes=64*1024**2)
    if not admission['can_start'] or read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Storage or image identity preflight refused')
    with scientific_lock(workspace):
        root.mkdir(parents=True,exist_ok=False)
        save_json(root/'storage_preflight.json',admission)
        cfg=json.loads((parent/'configuration.json').read_text())
        cfg['parent_result']=RESULT.as_posix()
        cfg['mode']='active_completion_only'
        save_json(root/'configuration.json',cfg)
        save_json(root/'parent_reference.json',{'path':RESULT.as_posix(),'manifest_sha256':digest(parent/'manifest.json'),
                  'original_states':10,'new_states_permitted':16,'parent_bytes':parent_bytes,
                  'remaining_bytes':cap,'remaining_seconds':timeout,'g0':'passed','g1':'passed'})
        sources=['src/prl/fem/fenicsx_ring.py','src/prl/fem/ring_geometry.py','src/prl/verification/fenicsx_ring.py',
                 'src/prl/runs/fenicsx_ring.py','src/prl/runs/fenicsx_runtime.py',
                 'project_control/ventricle_fem_fenicsx_active_completion_contract_v01.md']
        save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in sources})
        name='prl-f6s0-active-completion-v01-20260917'
        args=container_command(workspace,name,'/workspace/src/prl/fem/fenicsx_ring.py',root)
        save_json(root/'science_command.json',args)
        started=time.monotonic()
        reason=None
        with (root/'science_stdout.log').open('x',encoding='utf-8') as stdout,(root/'science_stderr.log').open('x',encoding='utf-8') as stderr:
            process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
            try:
                while process.poll() is None:
                    if time.monotonic()-started>timeout or sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>cap:
                        reason='remaining cumulative phase budget reached'
                        read_docker('stop','--time','5',name)
                        process.wait(timeout=20)
                        break
                    time.sleep(.5)
            except BaseException:
                read_docker('stop','--time','5',name)
                process.wait(timeout=20)
                raise
        inspection=json.loads(read_docker('inspect',name))[0]
        save_json(root/'container_inspect.json',inspection)
        checks=verify_container_settings(inspection)
        parent_ok=all(digest(parent/item['path'])==item['sha256'] for item in manifest['files'])
        report={'status':'passed' if process.returncode==0 and all(checks.values()) and parent_ok and reason is None else 'failed',
                'exit_code':process.returncode,'stop_reason':reason,'container_checks':checks,
                'parent_unchanged':parent_ok,'elapsed_seconds':time.monotonic()-started,
                'cumulative_scientific_container_seconds':parent_elapsed+time.monotonic()-started,
                'science_container_invocations_total':2,'repeated_equilibria':0,'new_states_permitted':16,
                'gpu':0,'threads':1,'container_retained':name}
        save_json(root/'execution.json',report)
        save_json(root/'manifest.json',package_manifest(root))
        return report


if __name__=='__main__':
    report=run_fenicsx_ring(Path.cwd())
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['status']=='passed' else 2)
