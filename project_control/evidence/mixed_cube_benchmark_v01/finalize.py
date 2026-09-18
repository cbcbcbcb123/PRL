"""Preserve and inspect the stopped v01 batch; never invokes a container or solver."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
from prl.runs.mixed_cube import RESULT,SOURCES,protection
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json,IMAGE
from prl.result_store import result_path
from prl.verification.ventricle_3d import load_arrays,mapping_checks,kinematics,extra_points
from prl.verification.mixed_cube import exact_fields,convergence


def main():
    workspace=Path(__file__).resolve().parents[3]
    root=result_path(workspace,RESULT)
    if (root/'delivery_interpretation.json').exists() or (root/'manifest.json').exists():
        raise FileExistsError('Create-only failure interpretation; never overwrite a frozen delivery')
    summary=json.loads((root/'summary.json').read_text())
    failure=json.loads((root/'failure.json').read_text())
    config=json.loads((root/'configuration.json').read_text())
    assert summary['attempted_solves']==failure['attempted_solves']==0
    assert summary['container_invocations']==1 and summary['automatic_retries']==0
    assert not summary['cases']
    references,dirty_count=protection(workspace)
    execution_sources=json.loads((root/'source_hashes.json').read_text())
    assert all(digest(root/'sources_at_execution'/name)==expected for name,expected in execution_sources.items())
    data=load_arrays(root/'raw/patch_affine_mesh.npz'); state=load_arrays(root/'failure_state.npz')
    mapping=mapping_checks(data)
    assert all(mapping.values())
    _,J,_,_,_,_=kinematics(data,state['u'],extra_points())
    interpolation_error=float(np.max(np.abs(state['u']-exact_fields(data['coordinates'],'affine',1000.)['u'])))
    assert interpolation_error<1e-14 and np.all(state['pressure']==0.)
    assert np.array_equal(state['mixed_state'][data['mixed_u_map']],state['u'].ravel())
    assert np.array_equal(state['mixed_state'][data['mixed_p_map']],state['pressure'])
    assert not list((root/'iterates').rglob('iterate_*.npz'))
    report={'status':'failed','scope':'engineering execution, not a material or convergence verdict',
        'execution':'failed','numerical_qualification':'not_run','SNES_calls':0,
        'evaluated_equilibrium_states':0,'container_invocations':1,'automatic_retries':0,
        'cases':{case['name']:{'status':'not_run','n':case['n'],'kappa':case['kappa']} for case in config['cases']},
        'convergence':convergence({},config),
        'original_records_preserved':True,
        'raw_summary_classification_correction':'Original summary conflated missing MMS states with failed precision. All eight equilibrium cases are not_run; no convergence order was measured.',
        'raw_post_verification_scope':'Original empty-case readback passed no equilibrium state; it is not numerical qualification.',
        'saved_state':{'type':'analytic displacement interpolation and zero pressure before SNES; not equilibrium',
            'mesh_mapping':mapping,'maximum_displacement_interpolation_error':interpolation_error,
            'precheck_minimum_sampled_J':float(J.min()),'precheck_maximum_sampled_J':float(J.max()),
            'accepted_Newton_states':0},
        'diagnosis':{'confirmed':'Native assembler compares expression and mesh coordinate-element hashes; mismatch raised before SNES.',
            'candidate':'Affine body is exactly zero. FFCx gives domain-free simplified expressions coordinate hash 0. The original comprehension did not log the failing expression key; this attribution remains unverified.',
            'candidate_status':'unknown','fix':'Mesh-bound zero Constant for affine/shear body, plus per-expression hash/failure diagnostics; same physical body force.',
            'native_retest':'not_run','original_reproduction_resolved':'unknown'},
        'original_ventricular_1_percent_gate':'failed_unchanged','growth':'not_run','FSI':'not_run','GPU':0}
    save_json(root/'delivery_interpretation.json',report)
    sources=list(SOURCES)+['src/prl/rendering/mixed_cube.py',str(Path(__file__).relative_to(workspace).as_posix())]
    source_hashes={}
    for name in sources:
        if name.endswith('.py'):
            ast.parse((workspace/name).read_text(encoding='utf-8'))
        target=root/'sources_at_delivery'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(workspace/name,target); source_hashes[name]=digest(target)
    save_json(root/'delivery_source_hashes.json',source_hashes)
    source_changed={name:{'execution':old,'delivery':source_hashes[name]}
                    for name,old in execution_sources.items() if source_hashes[name]!=old}
    save_json(root/'post_failure_changes.json',{'original_execution_sources_retained':True,'changes':source_changed,
        'native_verification':'not_run','physics_parameters_or_threshold_changes':False})
    native=Path(__file__).parent/'native_runtime'
    origins={'function.py':'/usr/local/dolfinx-real/lib/python3.12/dist-packages/dolfinx/fem/function.py',
        'Expression.h':'/usr/local/dolfinx-real/include/dolfinx/fem/Expression.h',
        'assembler.h':'/usr/local/dolfinx-real/include/dolfinx/fem/assembler.h',
        'ffcx_representation.py':'/dolfinx-env/lib/python3.12/site-packages/ffcx/ir/representation.py'}
    save_json(native/'source_manifest.json',{'source_image':IMAGE,'container':'prl-mixed-cube-benchmark-v01-20260918',
        'method':'docker cp from already stopped container; no exec/start/new container',
        'scope':'unmodified diagnostic source evidence only, not imported into production',
        'license':'Original copyright and LGPL/SPDX headers retained',
        'files':[{'path':name,'native_path':origin,'sha256':digest(native/name)} for name,origin in origins.items()]})
    environment=dict(os.environ,PYTHONPATH=str(workspace/'src'),PYTHONDONTWRITEBYTECODE='1',
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    command=[sys.executable,'-B','-X','utf8','-m','pytest','-q','-p','no:cacheprovider',
        'tests/prl/test_mixed_cube.py','tests/prl/test_ventricle_3d.py','tests/prl/test_volume_projection.py']
    tests=subprocess.run(command,cwd=workspace,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=60)
    save_json(root/'post_failure_tests.json',{'command':command,'stdout':tests.stdout,'stderr':tests.stderr,
        'exit_code':tests.returncode,'scope':'host analytical/regression tests only; no native runtime'})
    if tests.returncode:
        raise RuntimeError('Host regression failure; preserve outputs and stop')
    style_path=Path('C:/Users/chenb/.codex/skills/cb-plot-unified-style/assets/cb_plot_unified_style.py')
    shutil.copy2(style_path,root/'sources_at_delivery/style.py')
    os.environ['MPLCONFIGDIR']=str(root/'.plot_cache')
    specification=importlib.util.spec_from_file_location('benchmark_style',style_path)
    style=importlib.util.module_from_spec(specification); sys.modules[specification.name]=style
    specification.loader.exec_module(style)
    from prl.rendering.mixed_cube import draw
    exports=draw(root,style)
    command=[sys.executable,'-B','-X','utf8',
        'C:/Users/chenb/.codex/skills/cb-plot-unified-style/scripts/validate_cb_plot_style.py',exports['manifest']]
    validation=subprocess.run(command,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=30)
    save_json(root/'publication_style_check.json',{'status':'passed' if validation.returncode==0 else 'failed',
        'command':command,'exit_code':validation.returncode,'stdout':validation.stdout,'stderr':validation.stderr,
        'scope':'600dpi publication profile; this approved 160dpi exploratory diagnostic is not publication final'})
    save_json(root/'delivery_protection.json',{'status':'passed','protected_files':len(references),
        'preexisting_dirty_files':dirty_count,'execution_sources_preserved':len(execution_sources),
        'post_failure_native_runs':0,'new_deletions':0,'temporary_directory_cleanup':'none requested or performed'})
    print(json.dumps({'status':'passed','scope':'failure readback and host delivery, not solver qualification',
        'figure':exports,'protected_files':len(references),'old_changes':dirty_count},indent=2))


if __name__=='__main__':
    main()
