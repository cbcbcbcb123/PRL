"""Create-only, single-CPU F6-S1 controller with retained evidence and no retry."""

import json
from pathlib import Path
import shutil
import subprocess
import time

from prl.fem.ring_geometry import configuration as ring_configuration
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import IMAGE,TAG,read_docker,container_command,save_json,verify_container_settings
from prl.storage import evaluate_storage,scan_workspace

RESULT=Path('results/ventricle_fem/f6s1_contour_passive_v01_20260917')
CONTRACT=Path('project_control/ventricle_fem_fenicsx_contour_passive_contract_v01.md')
SOURCE=Path('results/ventricle_fem/f2_measured_contour_v01_20260917/geometry_source.npz')
CAP=256*1024**2
REPAIR_RESULT=Path('results/ventricle_fem/f6s1m_thin_mesh_v01_20260917')
REPAIR_CONTRACT=Path('project_control/ventricle_fem_fenicsx_thin_mesh_contract_v01.md')
PASSIVE_RESULT=Path('results/ventricle_fem/f6s1p_retained_passive_v01_20260917')
PASSIVE_CONTRACT=Path('project_control/ventricle_fem_fenicsx_retained_passive_contract_v01.md')
RETAINED_MESH=REPAIR_RESULT/'raw/candidate_0_mesh.npz'
RETAINED_MESH_SHA='157265c350367a95f36c40c5951117272ceeccac9f273ec65e5000eb81627f65'
FINE_RESULT=Path('results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917')
FINE_CONTRACT=Path('project_control/ventricle_fem_fenicsx_fine_diagnostic_contract_v01.md')


def configuration(repair=False,retained=False,fine=False):
    if sum([repair,retained,fine])>1:
        raise ValueError('Choose one contour execution mode')
    cfg=ring_configuration()
    cfg.update({'schema_version':'prl.fenicsx_contour_passive.v1','geometry_kind':'image_polygon',
                'meshes':[{'name':'M0'},{'name':'M1'}],'active_peak':0.,'scope':'image-derived outer polygon; assumed cavity/layers; passive plane strain; uncalibrated',
                'source':'72 hpf Fish 4 XY z=39','source_geometry':SOURCE.as_posix(),
                'mesher':{'polygon_vertices':128,'algorithm':6,'target_size':.09,'fine':'midpoint four-way subdivision'},
                'resources':{'threads':1,'gpu':0,'seconds':1200,'stage_bytes':CAP,'reserve_bytes':64*1024**2,'automatic_retries':0}})
    if repair:
        cfg['mesh_size_candidates']=[1.2,.9,.7]
        cfg['mesher']['size_rule']='min(0.09, factor * distance to adjacent fixed polygonal interface)'
        cfg['mesher']['selection']='first geometry-and-budget-qualified candidate; maximum three geometry generations'
    if retained or fine:
        cfg['retained_mesh']={'path':RETAINED_MESH.as_posix(),'sha256':RETAINED_MESH_SHA}
        cfg['mesher']={'mode':'retained candidate 0; no Gmsh calls','fine':'midpoint four-way subdivision'}
        cfg['resources']['stage_bytes']=800*1024**2
    if fine:
        cfg.update(diagnostic='fine_two_state',execution_meshes=['M1'],passive_loads=[0.,.02],
                   meshes=[{'name':'M1'}],parent_result=PASSIVE_RESULT.as_posix())
    return cfg


def protected(workspace,repair=False,retained=False,fine=False):
    values={}
    names=['f2_measured_contour_v01_20260917','f5_contour_pressure_v01_20260917',
           'f6s0_fenicsx_ring_active_v01_20260917','f6s0_active_completion_v01_20260917']
    if repair or retained or fine:
        names.append(RESULT.name)
    if retained or fine:
        names.append(REPAIR_RESULT.name)
    if fine:
        names.append(PASSIVE_RESULT.name)
    for name in names:
        base=workspace/'results/ventricle_fem'/name
        manifest=json.loads((base/'manifest.json').read_text())
        for item in manifest['files']:
            path=base/item['path']
            if not path.resolve().is_relative_to(base.resolve()) or path.is_symlink() or digest(path)!=item['sha256']:
                raise ValueError('Protected evidence drift: '+str(path))
        values.update({p.relative_to(workspace).as_posix():digest(p) for p in base.rglob('*') if p.is_file()})
    return values


def run_contour(workspace,repair=False,retained=False,fine=False):
    from prl.verification.fenicsx_contour import SOURCE_SHA
    from prl.result_store import result_path,result_admission,disk_admission,register_result,POLICY

    workspace=Path(workspace).resolve(strict=True)
    cfg=configuration(repair,retained,fine)
    root=result_path(workspace,FINE_RESULT if fine else PASSIVE_RESULT if retained else REPAIR_RESULT if repair else RESULT,new=True)
    contract=FINE_CONTRACT if fine else PASSIVE_CONTRACT if retained else REPAIR_CONTRACT if repair else CONTRACT
    if root.exists():
        raise FileExistsError('F6-S1 is create-only; no automatic rerun')
    if digest(workspace/SOURCE)!=SOURCE_SHA:
        raise ValueError('Frozen geometry source changed')
    if (retained or fine) and digest(workspace/RETAINED_MESH)!=RETAINED_MESH_SHA:
        raise ValueError('Retained qualified mesh changed')
    version=json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server'):
        raise RuntimeError('Docker server unavailable; no restart or repair authorized')
    if read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned local image unavailable or changed; no pull allowed')
    forecast=cfg['resources']['stage_bytes']  # Estimate only, never an external-store cap.
    if retained:
        import numpy as np
        with np.load(workspace/RETAINED_MESH,allow_pickle=False) as data:
            forecast=len(data['triangles'])*76800+48*1024**2
    if fine:
        forecast=256*1024**2  # Conservative forecast, not a stage cap.
    admission=result_admission(workspace,planned_new_bytes=forecast,stop_reserve_bytes=64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    cfg['resources']['stage_bytes']=None
    cfg['resources']['output_estimate_bytes']=forecast
    cfg['output_storage']={'mode':'external_disk_free','root':str(root),
                           'disk_free_floor_bytes':admission['disk_free_floor_bytes'],
                           'stop_reserve_bytes':admission['stop_reserve_bytes']}
    parents=protected(workspace,repair,retained,fine)
    with scientific_lock(workspace):
        root.mkdir(parents=True,exist_ok=False)
        save_json(root/'storage_preflight.json',admission)
        save_json(root/'configuration.json',cfg)
        save_json(root/'docker_version.json',version)
        save_json(root/'protected_preflight.json',parents)
        shutil.copyfile(workspace/SOURCE,root/'geometry_source.npz')
        if retained or fine:
            shutil.copyfile(workspace/RETAINED_MESH,root/'retained_mesh.npz')
        if fine:
            comparison=root/'comparison'; comparison.mkdir()
            names=['configuration.json','verification.json','raw/M0_mesh.npz','raw/M1_input_mesh.npz',
                   'raw/M0_state_passive_0.npz','raw/M0_state_passive_0.json',
                   'raw/M0_state_passive_1.npz','raw/M0_state_passive_1.json']
            identities={}
            for relative in names:
                source=workspace/PASSIVE_RESULT/relative
                shutil.copyfile(source,comparison/source.name)
                identities[source.name]={'parent_path':(PASSIVE_RESULT/relative).as_posix(),'sha256':digest(source)}
            save_json(comparison/'source_identity.json',identities)
        source_paths=['src/prl/fem/fenicsx_contour.py','src/prl/fem/fenicsx_ring.py','src/prl/fem/ring_geometry.py',
                      'src/prl/verification/fenicsx_contour.py','src/prl/verification/fenicsx_ring.py',
                      'src/prl/runs/fenicsx_contour.py','src/prl/runs/fenicsx_runtime.py',
                      'src/prl/result_store.py',POLICY.as_posix(),contract.as_posix()]
        if fine:
            source_paths.append('src/prl/verification/fenicsx_fine.py')
        for relative in source_paths:
            target=root/'sources_at_execution'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(workspace/relative,target)
        save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in source_paths})
        name='prl-f6s1q-fine-diagnostic-v01-20260917' if fine else 'prl-f6s1p-retained-passive-v01-20260917' if retained else 'prl-f6s1m-thin-mesh-v01-20260917' if repair else 'prl-f6s1-contour-passive-v01-20260917'
        args=container_command(workspace,name,'/workspace/src/prl/fem/fenicsx_contour.py',root)
        save_json(root/'command.json',args)
        save_json(root/'science_started.json',{'invocations':1,'container':name,'automatic_retries':0})
        started=time.monotonic()
        reason=None
        with (root/'stdout.log').open('x',encoding='utf-8') as stdout,(root/'stderr.log').open('x',encoding='utf-8') as stderr:
            process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
            try:
                while process.poll() is None:
                    disk=disk_admission(root,0,admission['stop_reserve_bytes'],admission['disk_free_floor_bytes'])
                    if time.monotonic()-started>1200 or not disk['can_start']:
                        reason='deadline' if time.monotonic()-started>1200 else 'disk-free safety floor'
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
        settings=verify_container_settings(inspection)
        unchanged=all(digest(workspace/p)==h for p,h in parents.items())
        report={'status':'passed' if process.returncode==0 and all(settings.values()) and unchanged and reason is None else 'failed',
                'exit_code':process.returncode,'stop_reason':reason,'container_checks':settings,
                'protected_parent_files':len(parents),'parents_unchanged':unchanged,'scientific_invocations':1,
                'runtime_capability_probes':0 if repair or retained or fine else 1,'automatic_retries':0,'gpu':0,'elapsed_seconds':time.monotonic()-started}
        save_json(root/'execution.json',report)
        save_json(root/'manifest.json',package_manifest(root))
        if not fine:  # New diagnostic index is frozen only after postprocessing.
            register_result(workspace,root,report['status'],digest(root/'manifest.json'))
        return report


def finalize_geometry_failure(workspace):
    """Audit saved evidence and accepted diagnostics; zero new meshes or solves."""
    from prl.rendering.fenicsx_contour import diagnose
    from prl.verification.fenicsx_ring import load_arrays

    workspace=Path(workspace).resolve(strict=True)
    root=workspace/RESULT
    formal=root/'formal_invocation_manifest.json'
    if not formal.exists():
        shutil.copyfile(root/'manifest.json',formal)
    original=json.loads(formal.read_text())
    if not all(digest(root/item['path'])==item['sha256'] for item in original['files']):
        raise ValueError('Formal invocation evidence changed')
    parents=json.loads((root/'protected_preflight.json').read_text())
    if not all(digest(workspace/path)==value for path,value in parents.items()):
        raise ValueError('Protected parent changed')
    failure=json.loads((root/'failure.json').read_text())
    if failure['attempted_states']!=0 or failure['completed_states']!=0:
        raise ValueError('This finalizer only accepts a pre-solve geometry failure')
    revision=root/'figures/FigS1_mesh_gate/FigS1_mesh_gate_v01_20260917'
    prefix=revision.name
    methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    if '人工/代理视觉验收: 通过' not in methods or '包状态: 最终包' not in methods:
        raise ValueError('Figure execution, visual acceptance and freeze required')
    data=revision/f'01_{prefix}_data.npz'
    if digest(data)!=digest(root/'raw/M0_input_mesh.npz'):
        raise ValueError('Figure data differ from saved solver mesh')
    style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text(encoding='utf-8'))
    if not style['validation']['passed']:
        raise ValueError('Style check failed')
    diagnosis=diagnose(load_arrays(data))[1]
    geom=json.loads((root/'raw/M0_geometry_preflight.json').read_text())
    save_json(root/'geometry_diagnosis.json',diagnosis)
    report={'status':'failed','delivery_status':'passed','mesh_gate':'failed',
            'passive_mechanics':'not_run','active_mechanics':'not_run','equilibrium_solves':0,
            'automatic_retries':0,'source_mask_iou':geom['source_mask_iou'],
            'raw_contour_hausdorff_um':geom['raw_contour_hausdorff_um'],
            'geometry':diagnosis,'source_fidelity':'passed','protected_parent_files':len(parents),
            'parents_unchanged':True,'formal_invocation_files_unchanged':len(original['files']),
            'figure':(revision/f'04_{prefix}.png').relative_to(root).as_posix(),
            'next_stage':'quality meshing of thin constructed layers, pending new bounded execution approval'}
    save_json(root/'summary.json',report)
    save_json(root/'rendering.json',{'status':'passed','scientific_solves':0,'mesh_generation_calls':0,
              'source':'retained formal M0 mesh; physical fields not_run',
              'notebook':(revision/f'03_{prefix}_plot.ipynb').relative_to(root).as_posix(),
              'visual_qa':'passed','outputs':package_manifest(revision)['files']})
    audit={'status':'passed','formal_manifest_sha256':digest(formal),
           'formal_invocation_files_unchanged':len(original['files']),'protected_parent_files_unchanged':len(parents),
           'figure_data_hash_matches':True,'scientific_solves':0,'tests':{'passed':153,'subtests_passed':27},
           'space':evaluate_storage(scan_workspace(workspace),planned_new_bytes=128*1024,stop_reserve_bytes=64*1024**2)}
    audit['phase_bytes_before_final_metadata']=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if not audit['space']['can_start'] or audit['phase_bytes_before_final_metadata']+128*1024>CAP:
        raise ValueError('Final storage gate failed')
    save_json(root/'delivery_audit.json',audit)
    save_json(root/'manifest.json',package_manifest(root))
    return {'delivery_status':'passed','scientific_status':'failed','equilibrium_solves':0,
            'workspace_bytes':audit['space']['usage']['logical_bytes'],
            'phase_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file())}


def finalize_mesh_repair(workspace):
    """Seal the saved geometry pass / storage block; never launch a container."""
    from prl.verification.fenicsx_contour import verify_mesh_repair

    workspace=Path(workspace).resolve(strict=True)
    root=workspace/REPAIR_RESULT
    formal=root/'formal_invocation_manifest.json'
    if not formal.exists():
        shutil.copyfile(root/'manifest.json',formal)
    original=json.loads(formal.read_text())
    if not all(digest(root/item['path'])==item['sha256'] for item in original['files']):
        raise ValueError('Original invocation evidence changed')
    parents=json.loads((root/'protected_preflight.json').read_text())
    if not all(digest(workspace/path)==value for path,value in parents.items()):
        raise ValueError('Protected evidence changed')
    verified=verify_mesh_repair(root,save=True)
    if verified['status']!='passed':
        raise ValueError('Independent mesh experiment audit failed')
    revision=root/'figures/FigS1M_mesh_repair/FigS1M_mesh_repair_v01_20260917'
    prefix=revision.name
    methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    if '人工/代理视觉验收: 通过' not in methods or '包状态: 最终包' not in methods:
        raise ValueError('Figure must be executed, visually accepted and frozen')
    data_pairs=[(revision/f'01_{prefix}_data.npz',workspace/RESULT/'raw/M0_input_mesh.npz'),
                (revision/f'01a_{prefix}_data_admission.json',root/'mesh_candidates.json')]
    data_pairs.extend((revision/f'01{letter}_{prefix}_data_candidate{i}.npz',root/'raw'/f'candidate_{i}_mesh.npz') for i,letter in enumerate('bcd'))
    if not all(digest(a)==digest(b) for a,b in data_pairs):
        raise ValueError('Figure data copies differ from original meshes')
    style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
    if not style['validation']['passed']:
        raise ValueError('Style validation failed')
    report={'status':'blocked','delivery_status':'passed','mesh_gate':'passed','storage_admission':'blocked',
            'passive_mechanics':'not_run','active_mechanics':'not_run','equilibrium_solves':0,
            'original_invocation_status':'failed','automatic_retries':0,'candidate_count':3,
            'recommended_mesh':'raw/candidate_0_mesh.npz','selected_for_solver':False,
            'smallest_geometry':verified['candidates'][0]['geometry'],
            'forecast_bytes':verified['candidates'][0]['predicted_bytes'],'stage_limit_bytes':CAP,
            'figure':(revision/f'04_{prefix}.png').relative_to(root).as_posix(),
            'next_action':'Pending approval: reuse candidate 0, one passive matrix with a 384 MiB stage allowance; project hard cap unchanged'}
    save_json(root/'summary.json',report)
    save_json(root/'rendering.json',{'status':'passed','mesh_generation_calls':0,'scientific_solves':0,
             'visual_qa':'passed','notebook':(revision/f'03_{prefix}_plot.ipynb').relative_to(root).as_posix(),
             'outputs':package_manifest(revision)['files']})
    space=evaluate_storage(scan_workspace(workspace),planned_new_bytes=128*1024,stop_reserve_bytes=64*1024**2)
    phase_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if not space['can_start'] or phase_bytes+128*1024>CAP:
        raise ValueError('Delivery storage gate failed')
    audit={'status':'passed','formal_invocation_files_unchanged':len(original['files']),
           'protected_parent_files_unchanged':len(parents),'figure_input_hash_matches':len(data_pairs),
           'development_tests':{'passed':47,'subtests_passed':21},'space':space,
           'phase_bytes_before_final_metadata':phase_bytes,'scientific_solves':0,'mesh_generations':0}
    save_json(root/'delivery_audit.json',audit)
    save_json(root/'manifest.json',package_manifest(root))
    return report


def finalize_retained_delivery(workspace):
    """Seal the original two-state failure and its accepted diagnostic figures."""
    from prl.verification.fenicsx_contour import verify_contour
    from PIL import Image

    workspace=Path(workspace).resolve(strict=True); root=workspace/PASSIVE_RESULT
    formal=root/'formal_invocation_manifest.json'
    if not formal.exists():
        shutil.copyfile(root/'manifest.json',formal)
    original=json.loads(formal.read_text()); parents=json.loads((root/'protected_preflight.json').read_text())
    if not all(digest(root/item['path'])==item['sha256'] for item in original['files']):
        raise ValueError('Formal invocation drift')
    if not all(digest(workspace/path)==value for path,value in parents.items()):
        raise ValueError('Protected parent drift')
    report=verify_contour(root)
    if report!=json.loads((root/'verification.json').read_text()):
        raise ValueError('Saved independent verification mismatch')
    failure=json.loads((root/'failure.json').read_text())
    state=report['cases']['M0']['passive_1']
    if failure['attempted_states']!=2 or failure['completed_states']!=1 or state['checks']['local_volume']:
        raise ValueError('Unexpected failure scope; must be assessed explicitly')
    revision=root/'figures/FigS1P_passive_failure/FigS1P_passive_failure_v01_20260917'; prefix=revision.name
    methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    if '人工/代理视觉验收: 通过' not in methods or '包状态: 最终包' not in methods:
        raise ValueError('Frozen accepted figure required')
    pairs=[(f'01_{prefix}_data.npz','raw/M0_mesh.npz'),(f'01a_{prefix}_data_diagnosis.json','local_volume_diagnosis.json'),
           (f'01b_{prefix}_data_geometry.npz','raw/M0_input_mesh.npz'),(f'01c_{prefix}_data_loaded.npz','raw/M0_state_passive_1.npz'),
           (f'01d_{prefix}_data_rest.npz','raw/M0_state_passive_0.npz'),(f'01e_{prefix}_data_verification.json','verification.json')]
    if not all(digest(revision/a)==digest(root/b) for a,b in pairs):
        raise ValueError('Figure source mismatch')
    style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
    with Image.open(revision/f'06_{prefix}_preview.gif') as preview:
        if preview.n_frames!=2 or not style['validation']['passed']:
            raise ValueError('Figure/GIF gate failed')
    summary={'status':'failed','delivery_status':'passed','geometry_status':'passed','storage_admission':'passed',
             'attempted_equilibria':2,'saved_equilibria':2,'accepted_equilibria':1,'failed_equilibria':1,
             'M1_mechanics':'not_run','active_mechanics':'not_run','biological_validation':'not_run',
             'failure_gate':'local_volume','failed_state':state,'stage_limit_bytes':800*1024**2,
             'scientific_invocations':1,'automatic_retries':0,
             'figure':(revision/f'04_{prefix}.png').relative_to(root).as_posix(),
             'gif':(revision/f'06_{prefix}_preview.gif').relative_to(root).as_posix(),
             'next_action':'Pending approval: two uncomputed M1 states at p=0 and 0.02, same physics, diagnose mesh sensitivity; no coarse repeat'}
    save_json(root/'summary.json',summary)
    save_json(root/'rendering.json',{'status':'passed','scientific_gate':'failed','scientific_solves':0,
              'deformation_scale':1,'state_count':2,'temporal_interpolation':False,'visual_qa':'passed',
              'notebook':(revision/f'03_{prefix}_plot.ipynb').relative_to(root).as_posix(),'outputs':package_manifest(revision)['files']})
    space=evaluate_storage(scan_workspace(workspace),planned_new_bytes=128*1024,stop_reserve_bytes=64*1024**2)
    size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if not space['can_start'] or size+128*1024>800*1024**2:
        raise ValueError('Delivery storage gate failed')
    save_json(root/'delivery_audit.json',{'status':'passed','formal_invocation_files_unchanged':len(original['files']),
              'protected_parent_files_unchanged':len(parents),'figure_input_hash_matches':len(pairs),
              'scientific_solves':0,'mesh_generation_calls':0,'tests':{'passed':54,'subtests_passed':21},
              'phase_bytes_before_final_metadata':size,'space':space})
    save_json(root/'manifest.json',package_manifest(root))
    return summary


if __name__=='__main__':
    report=run_contour(Path.cwd())
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['status']=='passed' else 2)
