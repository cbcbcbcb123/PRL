"""Freeze only the completed representation milestone; no solve, replay or deletion."""
from dataclasses import asdict
import json
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
    parent=Path('E:/Temp-Projects/PRL-results/ventricle_fem')
    roots=[parent/f'mixed_cube_representation_v{v:02d}_20260919' for v in (2,3)]
    if (evidence/'validation.json').exists() or any((root/'manifest.json').exists() for root in roots):
        raise FileExistsError('This milestone finalization is create-only')
    final=roots[-1]
    report=json.loads((final/'delivery_analysis.json').read_text(encoding='utf-8'))
    checks={}
    for root in roots:
        refs=json.loads((root/'protected_inputs.json').read_text(encoding='utf-8'))
        checks[root.name+'_protected']=all(digest(path)==expected for path,expected in refs['files'].items())
        sources=json.loads((root/'source_hashes.json').read_text(encoding='utf-8'))
        checks[root.name+'_execution_snapshots']=all(digest(root/'sources_at_execution'/path)==expected
                                                    for path,expected in sources.items())
    checks['six_terminal_readbacks']=report['completed_state_readback']=='passed' and report['completed_equilibria']==6
    checks['all_eight_attempted']=report['SNES_calls']==8 and len(report['cases'])==8
    checks['candidate_failure_not_hidden']=report['candidate_k100_qualification']['checks']['u_L2_order'] is False
    checks['both_controls_failed']=all(next(row for row in report['cases'] if row['name']==f'mms_p3p1_n{n}')['equilibrium']=='failed'
                                        for n in (4,8))
    checks['no_retries']=report['automatic_retries']==0 and report['container_invocations']==2
    old=json.loads((workspace/'project_control/evidence/mixed_cube_controls_v01_result/validation.json').read_text())
    checks['old_untracked_review_excerpts_unchanged']=all(digest(workspace/'docs/review/mixed_cube_controls_v01_20260919'/name)==value
                                                        for name,value in old['online_excerpt_hashes'].items())
    if not all(checks.values()):
        raise ValueError(checks)
    prefix='FigR2_mixed_cube_representation_v01_20260919'
    revision=final/'Figures'/'FigR2_mixed_cube_representation'/prefix
    manifest=revision/f'04_{prefix}_style_manifest.json'
    command=[sys.executable,'-B','-X','utf8',
             'C:/Users/chenb/.codex/skills/cb-plot-unified-style/scripts/validate_cb_plot_style.py',str(manifest)]
    process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=30)
    save_json(final/'publication_style_check.json',dict(status='passed' if process.returncode==0 else 'failed',
        command=command,exit_code=process.returncode,stdout=process.stdout,stderr=process.stderr,
        scope='General 600dpi publication requirement; project-approved 160dpi exploratory exception remains explicit'))
    preview=revision/f'04_{prefix}.png'
    if (evidence/'diagnostic.png').exists():
        raise FileExistsError('Preview already exists')
    shutil.copy2(preview,evidence/'diagnostic.png')
    source_names=['src/prl/runs/mixed_cube_representation_delivery.py',
                  'src/prl/runs/mixed_cube_representation_figure.py',
                  'src/prl/rendering/mixed_cube_representation.py',
                  'src/prl/verification/representation_guard_diagnosis.py',
                  'project_control/evidence/mixed_cube_representation_milestone_v01/error_localization.py',
                  'project_control/evidence/mixed_cube_representation_milestone_v01/guard_failure_diagnosis.json',
                  'project_control/evidence/mixed_cube_representation_milestone_v01/guard_failure_diagnosis_v03.json',
                  'project_control/evidence/mixed_cube_representation_milestone_v01/error_localization.json',
                  'project_control/evidence/mixed_cube_representation_milestone_v01/finalize_delivery.py']
    source_hashes={}
    for name in source_names:
        target=final/'delivery_sources'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            raise FileExistsError(target)
        shutil.copy2(workspace/name,target)
        source_hashes[name]=digest(target)
    save_json(final/'delivery_source_hashes.json',source_hashes)
    small={key:report[key] for key in ('delivery_integrity','all_matrix_equation_status',
        'candidate_k100_qualification','paired_pressure_contribution','completed_equilibria',
        'accepted_states_checked','accepted_paths_checked','saved_candidate_vectors','SNES_calls',
        'container_invocations','automatic_retries','quadrature_control')}
    small['cases']=[{key:row.get(key) for key in ('name','n','role','equilibrium','case_path_status',
        'metrics','DOF','solver_seconds','process_peak_rss_bytes','independent_comparison_eligible')}
        for row in report['cases']]
    small['original_ventricle']='failed'
    small['full_report_sha256']=digest(final/'delivery_analysis.json')
    save_json(evidence/'numerical_summary.json',small)
    packages=[]
    for root in roots:
        frozen=package_manifest(root)
        save_json(root/'manifest.json',frozen)
        sha=digest(root/'manifest.json')
        register_result(workspace,root,'failed',sha)
        packages.append({'root':str(root),'files':len(frozen['files'])+1,
            'bytes':sum(item['bytes'] for item in frozen['files'])+(root/'manifest.json').stat().st_size,
            'manifest_sha256':sha})
        assert all(digest(root/item['path'])==item['sha256'] for item in frozen['files'])
    storage=asdict(scan_workspace(workspace))
    save_json(evidence/'validation.json',{'status':'passed','scope':'milestone delivery/preservation; scientific qualification failed',
        'checks':checks,'candidate_complete_qualification':'failed','original_ventricle':'failed',
        'figure_workflow':'passed','publication_style':'passed' if process.returncode==0 else 'failed',
        'figure_preview_sha256':digest(preview),'preview_byte_identical':digest(preview)==digest(evidence/'diagnostic.png'),
        'packages':packages,'workspace_storage':storage,'workspace_under_3GiB':storage['logical_bytes']<=3*1024**3,
        'deletions':0,'new_review_package':False,'gpu':0,'docker_desktop_start_or_repair':0})
    print(json.dumps({'packages':packages,'workspace_storage':storage,'checks':checks},indent=2))


if __name__=='__main__':
    main()
