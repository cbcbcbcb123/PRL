"""Seal saved diagnostics and accepted figures; no solver calls or deletion."""
from pathlib import Path
import json
from PIL import Image
from prl.result_store import result_path,result_admission,register_result
from prl.runs.fenicsx_contour import FINE_RESULT
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import save_json
from prl.cockpit import render_cockpit,validate_cockpit_links

workspace=Path.cwd().resolve(); root=result_path(workspace,FINE_RESULT)
formal=json.loads((root/'formal_invocation_manifest.json').read_text())
parents=json.loads((root/'protected_preflight.json').read_text())
assert all(digest(root/item['path'])==item['sha256'] for item in formal['files'])
assert all(digest(workspace/p)==value for p,value in parents.items())
assert all(digest(workspace/p)==value for p,value in json.loads((root/'source_hashes.json').read_text()).items())
verification=json.loads((root/'verification.json').read_text())
failure=json.loads((root/'failure.json').read_text())
assert failure['attempted_states']==2 and failure['completed_states']==1
assert verification['status']=='failed' and verification['failed_checks']==['state_1']
assert [k for k,v in verification['cases']['M1']['passive_1']['checks'].items() if not v]==['local_volume']
revision=root/'figures/FigS1Q_fine_diagnostic/FigS1Q_fine_diagnostic_v01_20260917'; prefix=revision.name
methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
assert '人工/代理视觉验收: 通过' in methods and '包状态: 最终包' in methods
pairs=[(f'01_{prefix}_data.npz','raw/M1_mesh.npz'),
       (f'01a_{prefix}_data_coarse_mesh.npz','comparison/M0_mesh.npz'),
       (f'01b_{prefix}_data_coarse_state.npz','comparison/M0_state_passive_1.npz'),
       (f'01c_{prefix}_data_fine_state.npz','raw/M1_state_passive_1.npz'),
       (f'01d_{prefix}_data_geometry.npz','raw/M1_input_mesh.npz'),
       (f'01e_{prefix}_data_rest.npz','raw/M1_state_passive_0.npz'),
       (f'01f_{prefix}_data_verification.json','verification.json')]
assert all(digest(revision/a)==digest(root/b) for a,b in pairs)
style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
assert style['validation']['passed']
with Image.open(revision/f'06_{prefix}_preview.gif') as preview: assert preview.n_frames==2
baseline=json.loads((workspace/'project_control/evidence/git_main_integration_v01/preflight_manifest.json').read_text())
unrelated=[i for i in baseline['files'] if i['path'] in baseline['excluded']]
assert len(unrelated)==50 and all(digest(workspace/i['path'])==i['sha256'] for i in unrelated)
summary={'status':'failed','delivery_status':'passed','geometry':'passed','local_volume':'failed',
         'scientific_invocations':1,'attempted_states':2,'saved_states':2,'accepted_states':1,
         'coarse_solves':0,'automatic_retries':0,'gpu':0,'mesh_generation_calls':0,
         'comparison':verification['comparison'],'volume':verification['volume'],
         'scientific_boundary':'Global area agreement does not certify local incompressibility. No asymptotic convergence or biological validation.',
         'next_action':'Pending bounded repair decision: separate boundary-corner geometry from pointwise volume-constraint discretization; no blind refinement or continued loading',
         'figure':(revision/f'04_{prefix}.png').relative_to(root).as_posix(),
         'gif':(revision/f'06_{prefix}_preview.gif').relative_to(root).as_posix(),
         'active_contraction':'not_run','biological_validation':'not_run'}
save_json(root/'summary.json',summary)
save_json(root/'rendering.json',{'status':'passed','scientific_status':'failed','scientific_solves':0,
          'figure_inputs_hash_match':len(pairs),'states':2,'temporal_interpolation':False,
          'visual_qa':'passed','outputs':package_manifest(revision)['files']})
render_cockpit(workspace); links=validate_cockpit_links(workspace)
assert links['status']=='passed'
space=result_admission(workspace,planned_new_bytes=1024**2)
assert space['can_start']
audit={'status':'passed','formal_invocation_files_unchanged':len(formal['files']),
       'protected_parent_files_unchanged':len(parents),'unrelated_dirty_files_unchanged':len(unrelated),
       'source_at_execution_unchanged':True,'figure_input_hash_matches':len(pairs),
       'tests':{'passed':73,'subtests_passed':21},'cockpit':links,
       'repository_bytes':space['repository']['usage']['logical_bytes'],
       'external_stage_bytes_before_final_metadata':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
       'disk_free_bytes':space['disk_free_bytes'],'fixed_stage_limit_bytes':None,
       'scientific_solves_in_finalization':0,'deletions':0,'moves':0}
save_json(root/'delivery_audit.json',audit)
save_json(root/'manifest.json',package_manifest(root))
register_result(workspace,root,'failed',digest(root/'manifest.json'))
save_json(workspace/'project_control/evidence/f6s1q_fine_diagnostic_v01/delivery.json',
          {'result_root':str(root),'scientific_status':'failed','manifest_sha256':digest(root/'manifest.json'),**audit})
print(json.dumps(audit,indent=2))
