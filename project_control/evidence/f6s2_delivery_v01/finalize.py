"""Seal failed science plus successful offline diagnosis/figure delivery, without a solve."""
import json
from pathlib import Path
import shutil
from prl.result_store import result_admission,register_result
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import save_json

workspace=Path(__file__).resolve().parents[3]
evidence=Path(__file__).parent
root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918')
if (root/'manifest.json').exists() or (root/'summary.json').exists():
    raise FileExistsError('Delivery is already frozen')
formal=json.loads((root/'formal_invocation_manifest.json').read_text())
internal=json.loads((root/'protected_preflight.json').read_text())
external=json.loads((root/'external_protected_preflight.json').read_text())
dirty=json.loads((root/'preexisting_changes.json').read_text())
source_hashes=json.loads((root/'source_hashes.json').read_text())
diagnosis=json.loads((root/'interface_diagnosis.json').read_text())
report=json.loads((root/'post_verification.json').read_text())
runtime=json.loads((root/'execution.json').read_text())
tests=json.loads((evidence/'tests_after_rendering.json').read_text())
revision=next((root/'figures/FigS2_3d_start').glob('FigS2_*')); prefix=revision.name
methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
actual_changes={p for p,sha in source_hashes.items() if digest(workspace/p)!=sha}
checks={
    'formal_failed_invocation_unchanged':all(digest(root/f['path'])==f['sha256'] for f in formal['files']),
    'protected_ancestors_and_dirty':protected_unchanged(workspace,internal,external,dirty),
    'inputs_unchanged':all(digest(root/p)==sha for p,sha in json.loads((root/'input_identities.json').read_text()).items()),
    'source_changes_only_recorded_fix':actual_changes==set(diagnosis['source_changes']) and all(
        digest(workspace/p)==change['after_fix'] for p,change in diagnosis['source_changes'].items()),
    'single_invocation_and_no_retry':runtime['scientific_invocations']==1 and runtime['automatic_retries']==0,
    'first_failure_stopped':sorted(p.name for p in (root/'iterates').iterdir())==['M0_zero'],
    'raw_state_count_one':len(list((root/'raw').glob('*_state_*.npz')))==1,
    'runtime_isolation':all(runtime['container_checks'].values()) and runtime['gpu']==0,
    'original_failure_preserved':runtime['status']=='failed' and json.loads((root/'failure.json').read_text())['status']=='failed',
    'diagnosis_passed':diagnosis['status']=='passed',
    'offline_zero_passed':report['cases']['M0']['zero']['status']=='passed',
    'stage_still_incomplete':report['status']=='failed' and report['failed_checks']==['M0_complete','M1_complete'],
    'tests_passed':tests['status']=='passed',
    'notebook_visual_and_style':('- 包状态: 最终包' in methods and '人工/代理视觉验收: 通过' in methods and style['validation']['passed']),
    'figure_data_copy':digest(root/'figure_data.npz')==digest(revision/f'01_{prefix}_data.npz'),
}
if not all(checks.values()):
    raise ValueError('Delivery blocked: '+str([k for k,v in checks.items() if not v]))
admission=result_admission(workspace,4*1024**2)
if not admission['can_start']:
    raise RuntimeError('Final storage admission refused')
figures={kind:(revision/f'{number}_{prefix}{suffix}').relative_to(root).as_posix()
    for kind,number,suffix in [('notebook','03','_plot.ipynb'),('png','04','.png'),('svg','05','.svg')]}
summary={'status':'failed','engineering_execution':'failed','evidence_delivery':'passed',
    'reason':'First 3D zero solve completed but native independent audit failed on row-shaped pressure array.',
    'reference_geometry':'passed','offline_retained_zero_verification':'passed','interface_fix_offline':'passed',
    'interface_fix_native_reexecution':'not_run','attempted_equilibria':1,'newton_updates':0,
    'accepted_during_invocation':0,'accepted_by_post_fix_offline_audit':1,'remaining_equilibria':'not_run',
    'remaining_count':13,'pressure_loading':'not_run','active_loading':'not_run','mesh_response':'not_run',
    'zero':report['cases']['M0']['zero'],'geometry':{n:json.loads((root/'input'/f'{n}_geometry.json').read_text()) for n in ['M0','M1']},
    'elapsed_seconds':runtime['elapsed_seconds'],'scientific_invocations':1,'gpu':0,'automatic_retries':0,
    'fsi':'not_run','growth':'not_run','biological_validation':'not_run','physiological_time':'not_calibrated',
    'next_action':'Request bounded continuation approval: reuse the retained M0 zero without recomputation, verify exact DOF maps with the fixed adapter, then attempt the remaining 13 originally planned states, first failure stops.'}
audit={'status':'passed','checks':checks,'formal_files_unchanged':len(formal['files']),
       'protected_parent_files_unchanged':len(internal)+len(external),'preexisting_dirty_files_unchanged':len(dirty),
       'tests':tests,'repository_bytes':admission['repository']['usage']['logical_bytes'],
       'new_scientific_solves_in_postprocessing':0,'source_changes':diagnosis['source_changes'],
       'native_and_host_report_difference':'Explicit: native row-layout failure preserved; patched host audit accepts only the retained zero. No assertion of whole-report equality.'}
for filename,value in [('summary.json',summary),('delivery_audit.json',audit),('delivery_storage.json',admission),
    ('rendering.json',{'status':'passed','figures':figures,'notebook_execution':'passed','visual_qa':'passed',
        'style_validation':'passed','displayed_solved_states':1,'deformation_scale':1,'interpolated_frames':0,'new_FEM_solves':0})]:
    save_json(root/filename,value)
for relative in sorted(set(list(source_hashes)+['src/prl/rendering/ventricle_3d.py'])):
    target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(workspace/relative,target)
for filename in ['tests_before_run.json','tests_after_rendering.json','diagnose_retained.py','finalize.py']:
    target=root/'delivery_records'/filename; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(evidence/filename,target)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F6-S2 理想化三维固体：首接口失败保全</title><style>body{{max-width:1150px;margin:32px auto;padding:0 20px;font:16px/1.7 'Microsoft YaHei',sans-serif;color:#173e2e}}img{{width:100%}}a{{color:#176b4d}}</style>
<h1>三维结构已建成；本阶段failed，压力与收缩尚未运行</h1>
<p>真正三维半椭球壳、P2位移/P1压力四面体；构造心内膜/ECM/心肌三域，同mu=1、kappa=1000未标定。
基底环固定，外壁自由。计划内壁随动压力、外层切平面等权纤维分散主动张力；不是实测纤维。
粗/细网格1344/3960个四面体。当前只有粗网格无载态实际调用SNES，不能称为三维心跳。</p>
<p>一次{runtime['elapsed_seconds']:.3f}秒，1CPU/8GiB/禁网/0GPU；零载0次Newton更新后，压力数组(1,325)按一维读取导致IndexError。
原失败、原代码、原数组与原生复核均保留，首失败停止，未自动重跑。</p>
<p>最小回放复现后规范化DOF映射/压力布局，81测试通过；不改材料、离散、门限。
仅从原数据离线复核无载态passed：u=0、J=1、自由残差1.2368e-16。修正后的原生运行尚not_run；MUMPS因零Newton也尚未执行。</p>
<img src="{figures['png']}" alt="真实三维结构、固定基底及唯一无载J场；缺失加载态明确标注未运行">
<p>剖开只用于显示，求解对象为完整三维壳。C是输入几何近似误差，不是力学收敛。
未生成假5帧：压力、主动、组合、细网格平衡共余13态均not_run。</p>
<h2>下一步：有界续算待确认</h2><p>只读复用粗网格无载态，检查修正接口和精确DOF映射，再续原定13态；仍首失败停、单CPU、无GPU/重跑，不增加生长/FSI。</p>
<p><a href="configuration.json">固定配置</a> · <a href="failure.json">原失败</a> · <a href="interface_diagnosis.json">回放与修正证据</a> ·
<a href="post_verification.json">离线复核</a> · <a href="delivery_audit.json">保全审计</a> · <a href="{figures['notebook']}">可复算Notebook</a> · <a href="{figures['svg']}">SVG</a></p>
<p>只读复核：python -B -X utf8 -m prl verify fem-idealized-3d。总体仍返回failed，因为13态未运行。
原run是create-only，拒绝重跑。结果不进GitHub；无删除、安装、拉取或远端推送。</p></html>'''
(root/'index.html').write_text(page,encoding='utf-8')
save_json(root/'manifest.json',package_manifest(root))
register_result(workspace,root,'failed',digest(root/'manifest.json'))
result={'status':'failed','evidence_delivery':'passed','manifest_sha256':digest(root/'manifest.json'),
        'files':sum(p.is_file() for p in root.rglob('*')),
        'bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),'audit':audit}
save_json(evidence/'finalization.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
