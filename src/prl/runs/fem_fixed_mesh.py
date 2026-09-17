"""F3-A: isolate FEM resolution error on one frozen polygon and active field."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from prl.fem.active_ellipse import MeshLevel, assemble_model, solve_model_cycle
from prl.fem.refinement import geometric_quality, refine_model
from prl.runs.fem_active_ellipse import _level_summary, _manifest, _sha256, _write_json, _write_metrics
from prl.storage import evaluate_storage, scan_workspace

RESULT=Path('results/ventricle_fem/f3a_fixed_mesh_v01_20260917')
SOURCE=Path('results/ventricle_fem/f2_measured_contour_v01_20260917')
CONTRACT=Path('project_control/ventricle_fem_fixed_mesh_contract_v01.md')
CAP=128*1024**2
RESERVE=64*1024**2


def budget(root):
    size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if size>CAP: raise RuntimeError('fixed-mesh stage output exceeds 128 MiB')
    return size


def worker(workspace: Path):
    root=workspace/RESULT
    pre=evaluate_storage(scan_workspace(workspace),planned_new_bytes=CAP,stop_reserve_bytes=RESERVE)
    if not pre['can_start']:return {'status':'blocked','reason':'storage admission','storage':pre}
    if not (workspace/CONTRACT).is_file():raise FileNotFoundError(CONTRACT)
    root.mkdir(parents=True,exist_ok=False)
    _write_json(root/'storage_preflight.json',pre)
    original=json.loads((workspace/SOURCE/'configuration.json').read_text(encoding='utf-8'))
    config={
        'schema_version':'prl.fem_fixed_mesh_configuration.v1',
        'source_path':(SOURCE/'raw/G1.npz').as_posix(),
        'source_sha256':_sha256(workspace/SOURCE/'raw/G1.npz'),
        'materials':original['materials'],'geometry':original['geometry'],
        'phase_count':5,'phases':[0,.25,.5,.75,1],
        'active_strain':original['active_strain'],'boundaries':original['boundaries'],
        'gauge':'original L0 nodes only; zero weights on new nodes',
        'mesh':'uniform four-child midpoint refinement; exact parent tensor and material inheritance',
        'levels':{'L0':6144,'L1':24576,'L2':98304},
        'thresholds':{'recompute':1e-10,'maximum_strain':.05,'cavity_difference_absolute':.002,'cavity_difference_relative':.05},
        'resources':{'threads':1,'gpu':0,'dcm_calls':0,'timeout_s':900,'max_bytes':CAP,'stop_reserve_bytes':RESERVE,'automatic_retries':0},
        'source_provenance':'synthetic F0 materials and activation; measured outer contour only; no physiological time'}
    _write_json(root/'configuration.json',config)
    source_manifest=json.loads((workspace/SOURCE/'manifest.json').read_text(encoding='utf-8'))
    frozen_raw=next(item for item in source_manifest['files'] if item['path']=='raw/G1.npz')
    if frozen_raw['sha256']!=config['source_sha256']:
        _write_json(root/'failure.json',{'status':'failed','reason':'F2 frozen raw-source manifest mismatch','automatic_retries':0})
        raise RuntimeError('F2 raw-source manifest mismatch')
    source_paths=[CONTRACT,Path('src/prl/fem/active_ellipse.py'),Path('src/prl/fem/refinement.py'),
                  Path('src/prl/runs/fem_fixed_mesh.py'),Path('src/prl/verification/fem_fixed_mesh.py'),
                  Path('src/prl/rendering/fem_fixed_mesh.py'),Path('src/prl/runs/fem_active_ellipse.py'),
                  Path('src/prl/rendering/fem_measured_contour.py'),Path('src/prl/rendering/cb_plot_unified_style.py'),
                  Path('src/prl/storage.py')]
    _write_json(root/'source_hashes.json',{p.as_posix():_sha256(workspace/p) for p in source_paths})
    started=time.perf_counter()
    try:
        with np.load(workspace/SOURCE/'raw/G1.npz',allow_pickle=False) as file:
            source={k:file[k] for k in file.files}
        model=assemble_model(MeshLevel('L0',192,(4,4,8)),source['coordinates'],source['cells'],source['cell_layers'],
                             source['inner_nodes'],source['outer_nodes'],source['active_strain_unit'])
        ancestors=np.arange(len(model.cells),dtype=np.int64)
        (root/'raw').mkdir()
        summaries={}
        for index,label in enumerate(('L0','L1','L2')):
            if index:
                model,parents=refine_model(model,label)
                ancestors=ancestors[parents]
            else:parents=np.arange(len(model.cells),dtype=np.int64)
            print(f'{label}: {len(model.cells)} triangles; solving five prescribed phases',flush=True)
            values=solve_model_cycle(model,phase_count=5)
            state={k:values[k] for k in ('phases','activation','displacements','strains','stresses','equivalent_stress',
                   'pressure','lumen_area','outer_area','lumen_fraction_change','outer_fraction_change','stored_energy','minimum_triangle_area')}
            state.update({k:getattr(model,k) for k in ('coordinates','cells','cell_layers','areas','inner_nodes','outer_nodes','active_strain_unit')})
            state.update(source_cells=ancestors,parent_cells=parents,active_tangents=source['active_tangents'][ancestors])
            np.savez_compressed(root/'raw'/f'{label}.npz',**state)
            summary=_level_summary(values)
            summary['geometry_quality']=geometric_quality(model)
            summary['peak_cavity_x_span']=summary.pop('peak_inner_long_span')
            summary['peak_cavity_y_span']=summary.pop('peak_inner_short_span')
            if index==0:
                summary['f2_replay_errors']={k:float(np.max(np.abs(values[k]-source[k][[0,10,20,30,40]])))
                                            for k in ('displacements','strains','stresses','lumen_area','outer_area')}
                if max(summary['f2_replay_errors'].values())>1e-10:raise RuntimeError('F2 fixed-source replay mismatch')
            summaries[label]=summary
            _write_json(root/'summary.json',{'status':'unknown','levels':summaries})
            _write_metrics(root/f'metrics_{label}.csv',values)
            _write_json(root/'progress.json',{'status':'running','completed_level':label,'elapsed_s':time.perf_counter()-started})
            budget(root)
        from prl.verification.fem_fixed_mesh import verify_fem_fixed_mesh
        verification=verify_fem_fixed_mesh(root,save=True)
        if _sha256(workspace/SOURCE/'raw/G1.npz')!=config['source_sha256']:
            raise RuntimeError('source changed during the stage')
        _write_json(root/'summary.json',{'status':verification['status'],'levels':summaries,'biological_validation':'not_run'})
        from prl.rendering.fem_fixed_mesh import render_fem_fixed_mesh
        rendering=render_fem_fixed_mesh(root)
        post=evaluate_storage(scan_workspace(workspace),planned_new_bytes=0,stop_reserve_bytes=RESERVE)
        _write_json(root/'storage_postflight.json',post)
        execution={'status':verification['status'] if rendering['status']=='passed' and post['can_start'] else 'failed',
                   'rendering':rendering['status'],'elapsed_s':time.perf_counter()-started,'stage_bytes_before_manifest':budget(root),
                   'scientific_invocations':1,'automatic_retries':0,'gpu':0,'dcm_calls':0,'biological_validation':'not_run'}
        _write_json(root/'execution.json',execution); _write_json(root/'progress.json',execution)
        manifest=_manifest(root); manifest['schema_version']='prl.fem_fixed_mesh_manifest.v1'
        _write_json(root/'manifest.json',manifest); budget(root)
        return execution
    except Exception as exc:
        _write_json(root/'failure.json',{'status':'failed','reason':repr(exc),'elapsed_s':time.perf_counter()-started,
                                      'retained_states':'all written states preserved','automatic_retries':0})
        raise


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--workspace',type=Path,default=Path.cwd());parser.add_argument('--worker',action='store_true')
    args=parser.parse_args(); workspace=args.workspace.resolve()
    if args.worker:
        report=worker(workspace); print(json.dumps(report,indent=2));return 0 if report['status']=='passed' else 1
    env=os.environ.copy()
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[key]='1'
    env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']=str(workspace/'src');env['MPLCONFIGDIR']=str(workspace/RESULT/'runtime_cache')
    try:return subprocess.run([sys.executable,'-B','-X','utf8','-m','prl.runs.fem_fixed_mesh','--workspace',str(workspace),'--worker'],
                              cwd=workspace,env=env,timeout=900,check=False).returncode
    except subprocess.TimeoutExpired:
        if (workspace/RESULT).is_dir():_write_json(workspace/RESULT/'timeout.json',{'status':'failed','reason':'900 second wall cap','automatic_retries':0})
        return 1


if __name__=='__main__':raise SystemExit(main())
