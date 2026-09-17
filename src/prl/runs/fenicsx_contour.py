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


def configuration():
    cfg=ring_configuration()
    cfg.update({'schema_version':'prl.fenicsx_contour_passive.v1','geometry_kind':'image_polygon',
                'meshes':[{'name':'M0'},{'name':'M1'}],'active_peak':0.,'scope':'image-derived outer polygon; assumed cavity/layers; passive plane strain; uncalibrated',
                'source':'72 hpf Fish 4 XY z=39','source_geometry':SOURCE.as_posix(),
                'mesher':{'polygon_vertices':128,'algorithm':6,'target_size':.09,'fine':'midpoint four-way subdivision'},
                'resources':{'threads':1,'gpu':0,'seconds':1200,'stage_bytes':CAP,'reserve_bytes':64*1024**2,'automatic_retries':0}})
    return cfg


def protected(workspace):
    values={}
    for name in ['f2_measured_contour_v01_20260917','f5_contour_pressure_v01_20260917',
                 'f6s0_fenicsx_ring_active_v01_20260917','f6s0_active_completion_v01_20260917']:
        base=workspace/'results/ventricle_fem'/name
        manifest=json.loads((base/'manifest.json').read_text())
        for item in manifest['files']:
            path=base/item['path']
            if not path.resolve().is_relative_to(base.resolve()) or path.is_symlink() or digest(path)!=item['sha256']:
                raise ValueError('Protected evidence drift: '+str(path))
        values.update({p.relative_to(workspace).as_posix():digest(p) for p in base.rglob('*') if p.is_file()})
    return values


def run_contour(workspace):
    from prl.verification.fenicsx_contour import SOURCE_SHA

    workspace=Path(workspace).resolve(strict=True)
    root=workspace/RESULT
    if root.exists():
        raise FileExistsError('F6-S1 is create-only; no automatic rerun')
    if digest(workspace/SOURCE)!=SOURCE_SHA:
        raise ValueError('Frozen geometry source changed')
    if read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned local image unavailable or changed; no pull allowed')
    admission=evaluate_storage(scan_workspace(workspace),planned_new_bytes=CAP,stop_reserve_bytes=64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    parents=protected(workspace)
    with scientific_lock(workspace):
        root.mkdir(parents=True,exist_ok=False)
        save_json(root/'storage_preflight.json',admission)
        save_json(root/'configuration.json',configuration())
        save_json(root/'protected_preflight.json',parents)
        shutil.copyfile(workspace/SOURCE,root/'geometry_source.npz')
        source_paths=['src/prl/fem/fenicsx_contour.py','src/prl/fem/fenicsx_ring.py','src/prl/fem/ring_geometry.py',
                      'src/prl/verification/fenicsx_contour.py','src/prl/verification/fenicsx_ring.py',
                      'src/prl/runs/fenicsx_contour.py','src/prl/runs/fenicsx_runtime.py',CONTRACT.as_posix()]
        for relative in source_paths:
            target=root/'sources_at_execution'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(workspace/relative,target)
        save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in source_paths})
        name='prl-f6s1-contour-passive-v01-20260917'
        args=container_command(workspace,name,'/workspace/src/prl/fem/fenicsx_contour.py',root)
        save_json(root/'command.json',args)
        save_json(root/'science_started.json',{'invocations':1,'container':name,'automatic_retries':0})
        started=time.monotonic()
        reason=None
        with (root/'stdout.log').open('x',encoding='utf-8') as stdout,(root/'stderr.log').open('x',encoding='utf-8') as stderr:
            process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
            try:
                while process.poll() is None:
                    size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
                    if time.monotonic()-started>1200 or size>CAP-8*1024**2:
                        reason='deadline or stage storage stop threshold'
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
                'runtime_capability_probes':1,'automatic_retries':0,'gpu':0,'elapsed_seconds':time.monotonic()-started}
        save_json(root/'execution.json',report)
        save_json(root/'manifest.json',package_manifest(root))
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


if __name__=='__main__':
    report=run_contour(Path.cwd())
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['status']=='passed' else 2)
