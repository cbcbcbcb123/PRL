"""Bounded FEM-only trial on an image-derived zebrafish section outer contour."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from prl.fem.active_ellipse import MATERIALS, solve_model_cycle
from prl.fem.measured_contour import ARCHIVE, LEVELS, boundary_diagnostics, extract_geometry, make_model
from prl.runs.fem_active_ellipse import _level_summary, _manifest, _sha256, _write_json, _write_metrics
from prl.storage import evaluate_storage, scan_workspace

RESULT=Path("results/ventricle_fem/f2_measured_contour_v01_20260917")
CONTRACT=Path("project_control/ventricle_fem_measured_contour_contract_v01.md")
CAP=128*1024**2
RESERVE=64*1024**2


def check_budget(root: Path):
    total=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if total>CAP:
        raise RuntimeError(f"stage storage cap exceeded: {total}>{CAP}")
    return total


def worker(workspace: Path) -> dict:
    root=workspace/RESULT
    pre=evaluate_storage(scan_workspace(workspace),planned_new_bytes=CAP,stop_reserve_bytes=RESERVE)
    if not pre['can_start']:
        return {'status':'blocked','reason':'storage admission','storage':pre}
    if not (workspace/CONTRACT).is_file():raise FileNotFoundError(CONTRACT)
    root.mkdir(parents=True,exist_ok=False)
    _write_json(root/'storage_preflight.json',pre)
    config={
        'schema_version':'prl.fem_measured_contour.configuration.v1',
        'model':'2-D plane-strain P1, image-derived outer contour; constructed internal anatomy',
        'materials':{name:{'young':v[0],'poisson':v[1]} for name,v in MATERIALS.items()},
        'geometry':{'source_archive':str(ARCHIVE),'internal_boundaries':'assumed homothetic F0 proportions'},
        'active_strain':{'peak':.03,'waveform':'0.015*(1-cos(2*pi*phase))',
                         'layer':'myocardium','direction':'local constructed layer tangent'},
        'boundaries':{'inner':'traction-free, no lumen pressure','outer':'traction-free',
                      'gauge':'three exact rigid-motion constraints; no clamps'},
        'phase_count':41,'units':'geometry in um, solver x/L; stresses relative to uncalibrated E_ref',
        'runtime':{'python':sys.version,'libraries':{name:version(name) for name in ('numpy','scipy','scikit-image','tifffile','matplotlib','Pillow')}},
        'levels':{key:{'ntheta':level.ntheta,'radial_intervals':list(level.radial_intervals)} for key,level in LEVELS.items()},
        'resources':{'threads':1,'gpu':0,'dcm_calls':0,'timeout_s':600,'max_bytes':CAP,'stop_reserve_bytes':RESERVE,'automatic_retries':0},
        'thresholds':{'source_mask_iou_min':.98,'contour_hausdorff_um_max':2.,'maximum_strain':.05,
                      'minimum_contraction':-.005,'mesh_cavity_drift_max':.002,'residual_max':1e-10}}
    _write_json(root/'preregistration.json',config)
    started=time.perf_counter()
    try:
        arrays,geometry=extract_geometry()
        np.savez_compressed(root/'geometry_source.npz',**arrays)
        _write_json(root/'geometry.json',geometry)
        if geometry['status']!='passed':raise RuntimeError('outer contour source-fidelity gate failed')
        config['geometry'].update({key:geometry[key] for key in ('center_um','length_scale_um','slice_z_index','radial_boundary_fractions')})
        _write_json(root/'configuration.json',config)
        sources=[CONTRACT,Path('src/prl/fem/active_ellipse.py'),Path('src/prl/fem/measured_contour.py'),
                 Path('src/prl/runs/fem_measured_contour.py'),Path('src/prl/verification/fem_measured_contour.py'),
                 Path('src/prl/rendering/fem_measured_contour.py'),Path('src/prl/runs/fem_active_ellipse.py'),
                 Path('src/prl/rendering/cb_plot_unified_style.py')]
        _write_json(root/'source_hashes.json',{p.as_posix():_sha256(workspace/p) for p in sources})
        (root/'raw').mkdir()
        level_summaries={}
        for label in ('G0','G1'):
            model,tangents=make_model(arrays,label)
            physical_outer=model.coordinates[model.outer_nodes]*arrays['length_scale_um']+arrays['center_um']
            geometry.setdefault('mesh_discretization',{})[label]=boundary_diagnostics(arrays,physical_outer)
            _write_json(root/'geometry.json',geometry)
            values=solve_model_cycle(model,phase_count=41)
            # Full saved trajectories include the active tensor for independent inspection.
            state={key:values[key] for key in ('phases','activation','displacements','strains','stresses',
                   'equivalent_stress','pressure','lumen_area','outer_area','lumen_fraction_change',
                   'outer_fraction_change','stored_energy','minimum_triangle_area')}
            state.update({key:getattr(model,key) for key in ('coordinates','cells','cell_layers','areas','inner_nodes','outer_nodes','active_strain_unit')})
            state['active_tangents']=tangents
            np.savez_compressed(root/'raw'/f'{label}.npz',**state)
            level_summaries[label]=_level_summary(values)
            _write_metrics(root/f'metrics_{label}.csv',values)
            _write_json(root/'progress.json',{'status':'running','completed_level':label,'elapsed_s':time.perf_counter()-started})
            check_budget(root)
        summary={'status':'unknown','scope':'real outer-contour FEM engineering pilot; internal anatomy assumed',
                 'levels':level_summaries,'official_stage_invocations':1,'dcm_calls':0,'gpu':0,
                 'maximum_backward_residual':max(v['maximum_backward_residual'] for v in level_summaries.values()),
                 'maximum_constraint_residual':max(v['maximum_constraint_residual'] for v in level_summaries.values()),
                 'mesh_peak_lumen_change_absolute_difference':abs(level_summaries['G1']['peak_lumen_fraction_change']-level_summaries['G0']['peak_lumen_fraction_change']),
                 'biological_validation':'not_run','real_cell_segmentation_required':False}
        _write_json(root/'summary.json',summary)
        from prl.verification.fem_measured_contour import verify_fem_measured_contour
        verification=verify_fem_measured_contour(root,save=True)
        summary['status']=verification['status']; _write_json(root/'summary.json',summary)
        from prl.rendering.fem_measured_contour import render_fem_measured_contour
        rendering=render_fem_measured_contour(root)
        post=evaluate_storage(scan_workspace(workspace),planned_new_bytes=0,stop_reserve_bytes=RESERVE)
        _write_json(root/'storage_postflight.json',post)
        execution={'status':summary['status'] if rendering['status']=='passed' and post['can_start'] else 'failed',
                   'elapsed_s':time.perf_counter()-started,'result_bytes_before_manifest':check_budget(root),
                   'result':str(root),'engineering':summary['status'],'rendering':rendering['status'],
                   'biological_validation':'not_run','automatic_retries':0,'gpu':0,'dcm_calls':0}
        _write_json(root/'execution.json',execution)
        _write_json(root/'progress.json',execution)
        _write_json(root/'manifest.json',_manifest(root))
        check_budget(root)
        return execution
    except Exception as exc:
        _write_json(root/'failure.json',{'status':'failed','reason':repr(exc),'elapsed_s':time.perf_counter()-started,
                    'retained_states':'all previously saved NPZ remain untouched','automatic_retries':0})
        raise


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--workspace',type=Path,default=Path.cwd()); parser.add_argument('--worker',action='store_true')
    args=parser.parse_args(); workspace=args.workspace.resolve()
    if args.worker:
        payload=worker(workspace); print(json.dumps(payload,indent=2)); return 0 if payload['status']=='passed' else 1
    env=os.environ.copy()
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[key]='1'
    env['PYTHONDONTWRITEBYTECODE']='1'; env['MPLCONFIGDIR']=str(workspace/RESULT/'runtime_cache')
    # The bounded result package owns its small font cache; no external writes.
    env['PYTHONPATH']=str(workspace/'src')
    command=[sys.executable,'-B','-X','utf8','-m','prl.runs.fem_measured_contour','--workspace',str(workspace),'--worker']
    try:
        return subprocess.run(command,cwd=workspace,env=env,timeout=600,check=False).returncode
    except subprocess.TimeoutExpired:
        root=workspace/RESULT
        if root.is_dir():_write_json(root/'timeout.json',{'status':'failed','reason':'600 s wall-time cap','automatic_retries':0})
        return 1


if __name__=='__main__':raise SystemExit(main())
