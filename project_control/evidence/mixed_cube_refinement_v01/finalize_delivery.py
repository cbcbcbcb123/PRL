"""Freeze the completed single-grid milestone; no solve or deletion."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from prl.runs.fenicsx_ring import digest, package_manifest
from prl.runs.fenicsx_runtime import save_json
from prl.result_store import register_result
from prl.storage import scan_workspace


def main():
    workspace=Path(__file__).resolve().parents[3]
    evidence=Path(__file__).resolve().parent
    root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/mixed_cube_refinement_v01_20260919')
    if (evidence/'validation.json').exists() or (root/'manifest.json').exists():
        raise FileExistsError('Finalization is create-only')
    report=json.loads((root/'delivery_analysis.json').read_text(encoding='utf-8'))
    refs=json.loads((root/'protected_inputs.json').read_text(encoding='utf-8'))
    sources=json.loads((root/'source_hashes.json').read_text(encoding='utf-8'))
    execution=json.loads((root/'execution.json').read_text(encoding='utf-8'))
    checks={
        'protected':all(digest(path)==value for path,value in refs['files'].items()),
        'source_snapshots':all(digest(root/'sources_at_execution'/path)==value for path,value in sources.items()),
        'independent_delivery':report['delivery_integrity']=='passed',
        'one_solve_only':report['new_SNES_calls']==1 and report['container_invocations']==1,
        'no_retries':report['automatic_retries']==0,
        'original_failures_preserved':report['original_n2_n4_n8_qualification']=='failed_unchanged'
            and report['original_ventricular_gate']=='failed_unchanged',
        'fixed_primary_pair':report['convergence']['primary_pair']==[8,12],
        'runtime_settings':all(execution['container_checks'].values()) and not execution['OOMKilled'],
    }
    if not all(checks.values()):
        raise ValueError(checks)
    test_names=['nodal_export','mixed_cube_representation','mixed_cube','mixed_cube_controls',
        'saved_segment','positive_j','ventricle_3d','volume_projection',
        'mixed_cube_representation_delivery','mixed_cube_representation_render',
        'mixed_cube_representation_figure','representation_guard_diagnosis',
        'mixed_cube_refinement','mixed_cube_refinement_delivery',
        'mixed_cube_refinement_render','mixed_cube_refinement_figure']
    test_command=[sys.executable,'-B','-X','utf8','-m','pytest','-q','-p','no:cacheprovider',
                  *[f'tests/prl/test_{name}.py' for name in test_names]]
    environment=dict(os.environ,PYTHONPATH=str(workspace/'src'),PYTHONDONTWRITEBYTECODE='1',
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    tests=subprocess.run(test_command,cwd=workspace,env=environment,capture_output=True,
                         text=True,encoding='utf-8',timeout=120)
    save_json(evidence/'tests_final.json',{'command':test_command,'stdout':tests.stdout,
        'stderr':tests.stderr,'exit_code':tests.returncode})
    if tests.returncode:
        raise ValueError('Final regression failed; no package freeze')
    prepared=json.loads((root/'figure_prepared.json').read_text(encoding='utf-8'))
    revision=Path(prepared['revision_dir']); prefix=revision.name
    preview=revision/f'04_{prefix}.png'
    methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    if '通过' not in methods or '最终包' not in methods:
        raise ValueError('Figure execution, visual review and final freeze must precede packaging')
    style_manifest=revision/f'04_{prefix}_style_manifest.json'
    command=[sys.executable,'-B','-X','utf8',
        'C:/Users/chenb/.codex/skills/cb-plot-unified-style/scripts/validate_cb_plot_style.py',str(style_manifest)]
    process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=30)
    save_json(root/'publication_style_check.json',dict(status='passed' if process.returncode==0 else 'failed',
        command=command,exit_code=process.returncode,stdout=process.stdout,stderr=process.stderr,
        scope='Generic 600dpi publication check; approved 160dpi exploration remains distinct'))
    if (evidence/'diagnostic.png').exists():
        raise FileExistsError('Preview already exists')
    shutil.copy2(preview,evidence/'diagnostic.png')
    source_names=['src/prl/runs/mixed_cube_refinement_delivery.py',
        'src/prl/runs/mixed_cube_refinement_figure.py','src/prl/rendering/mixed_cube_refinement.py',
        'src/prl/runs/mixed_cube_representation_delivery.py','src/prl/verification/saved_segment.py',
        'src/prl/verification/positive_j.py','tests/prl/test_mixed_cube_refinement_delivery.py',
        'tests/prl/test_mixed_cube_refinement_render.py','tests/prl/test_mixed_cube_refinement_figure.py',
        'project_control/evidence/mixed_cube_refinement_v01/finalize_delivery.py']
    hashes={}
    for name in source_names:
        target=root/'delivery_sources'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            raise FileExistsError(target)
        shutil.copy2(workspace/name,target); hashes[name]=digest(target)
    save_json(root/'delivery_source_hashes.json',hashes)
    small={key:report[key] for key in ('status','convergence','delivery_integrity','accepted_states_checked',
        'accepted_paths_checked','new_SNES_calls','container_invocations','automatic_retries')}
    small['cases']=[{key:row.get(key) for key in ('name','n','equilibrium','metrics','DOF','tetrahedra',
        'solver_seconds','process_peak_rss_bytes','error_integration')} for row in report['cases']]
    small['full_report_sha256']=digest(root/'delivery_analysis.json')
    save_json(evidence/'numerical_summary.json',small)
    frozen=package_manifest(root); save_json(root/'manifest.json',frozen)
    sha=digest(root/'manifest.json'); register_result(workspace,root,report['status'],sha)
    if not all(digest(root/item['path'])==item['sha256'] for item in frozen['files']):
        raise ValueError('Final package hash mismatch')
    storage=asdict(scan_workspace(workspace))
    package={'root':str(root),'files':len(frozen['files'])+1,
        'bytes':sum(item['bytes'] for item in frozen['files'])+(root/'manifest.json').stat().st_size,
        'manifest_sha256':sha}
    save_json(evidence/'validation.json',{'status':'passed','scope':'delivery, preservation and exploratory figure',
        'checks':checks,'refinement_qualification':report['status'],'original_ventricle':'failed',
        'protected_files':len(refs['files']),'preexisting_dirty_files':refs['preexisting_dirty_files'],
        'execution_sources':len(sources),'package':package,'figure_workflow':'passed',
        'publication_style':'passed' if process.returncode==0 else 'failed',
        'preview_byte_identical':digest(preview)==digest(evidence/'diagnostic.png'),
        'workspace_storage':storage,'workspace_under_3GiB':storage['logical_bytes']<=3*1024**3,
        'deletions':0,'new_review_package':False,'gpu':0,'docker_desktop_start_or_repair':0})
    print(json.dumps({'package':package,'checks':checks,'scientific_status':report['status']},indent=2))


if __name__=='__main__':
    main()
