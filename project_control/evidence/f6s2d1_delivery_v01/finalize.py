"""Freeze the two-state mesh diagnostic; never reinterpret equilibrium as quality."""
import json
from pathlib import Path
import shutil
from prl.result_store import result_admission,register_result
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import save_json

workspace=Path(__file__).resolve().parents[3]; evidence=Path(__file__).parent
root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918')
if (root/'manifest.json').exists() or (root/'summary.json').exists():
    raise FileExistsError('Delivery is already frozen')
def read(name):
    return json.loads((root/name).read_text())
formal=read('formal_invocation_manifest.json'); internal=read('protected_preflight.json')
external=read('external_protected_preflight.json'); dirty=read('preexisting_changes.json'); sources=read('source_hashes.json')
report=read('mesh_diagnostic.json'); runtime=read('execution.json'); failure=read('failure.json')
tests=json.loads((evidence/'tests_after_rendering.json').read_text())
revision=next((root/'figures/FigS2D1_3d_mesh_comparison').glob('FigS2D1_*')); prefix=revision.name
methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
records=report['new_mesh']['cases']['M1']
checks={
    'formal_invocation_unchanged':all(digest(root/f['path'])==f['sha256'] for f in formal['files']),
    'protected_ancestors_and_dirty':protected_unchanged(workspace,internal,external,dirty),
    'execution_sources_unchanged':all(digest(workspace/p)==sha for p,sha in sources.items()),
    'input_copies_unchanged':all(digest(root/p)==sha for p,sha in read('input_identities.json').items()),
    'mechanics_unchanged':read('mechanical_identity.json')['status']=='passed',
    'single_bounded_invocation':runtime['scientific_invocations']==1 and runtime['automatic_retries']==0 and runtime['runtime_microprobes']==0,
    'exact_two_state_scope':report['checks']['exact_two_state_scope'],
    'first_failure_stopped':failure['attempted_states']==2 and failure['accepted_states']==1 and
        sorted(p.name for p in (root/'iterates').iterdir())==['M1_pressure_1','M1_zero'],
    'raw_state_count_two':len(list((root/'raw').glob('*_state_*.npz')))==2,
    'runtime_isolation':all(runtime['container_checks'].values()) and runtime['gpu']==0 and not runtime['OOMKilled'],
    'zero_accepted_pressure_rejected':records['zero']['status']=='passed' and records['pressure_1']['failed_checks']==['local_volume'],
    'old_failure_not_relabelled':report['retained_coarse']['failed_checks']==['local_volume'] and not report['comparison']['pointwise_qualification_both_meshes'],
    'host_native_agreement':read('report_comparison.json')['status']=='passed',
    'matched_loads':report['checks']['matched_pressure_and_no_active'],
    'tests_passed':tests['status']=='passed',
    'figure_executed_visual_and_style':('- 包状态: 最终包' in methods and '人工/代理视觉验收: 通过' in methods and style['validation']['passed']),
    'figure_data_copy':digest(root/'figure_data.npz')==digest(revision/f'01_{prefix}_data.npz'),
    'portable_helper_matches':digest(workspace/'src/prl/rendering/ventricle_3d_resume.py')==digest(next(revision.glob('*_helper.py'))),
    'portable_probe_matches':digest(workspace/'src/prl/verification/ventricle_mesh_probe.py')==digest(next(revision.glob('*_probe.py'))),
}
if not all(checks.values()):
    raise ValueError('Delivery blocked: '+str([k for k,v in checks.items() if not v]))
admission=result_admission(workspace,4*1024**2)
if not admission['can_start']:
    raise RuntimeError('Storage refused')
figures={kind:(revision/f'{number}_{prefix}{suffix}').relative_to(root).as_posix()
    for kind,number,suffix in [('notebook','03','_plot.ipynb'),('png','04','.png'),('svg','05','.svg')]}
summary={'status':'failed','nonlinear_equilibrium':'passed','fine_zero':'passed','fine_pressure_acceptance':'failed',
    'evidence_delivery':'passed','reason':'M1 refinement only reduces local distortion by 4.806%; both meshes fail original 1% gate.',
    'attempted_new_equilibria':2,'accepted_new_equilibria':1,'newton_updates':3,
    'pressure_states':{'M0':report['retained_coarse'],'M1':records['pressure_1']},
    'comparison':report['comparison'],'spatial':report['spatial'],'elapsed_seconds':runtime['elapsed_seconds'],
    'scientific_invocations':1,'gpu':0,'automatic_retries':0,'active_loading':'not_run','fsi':'not_run','growth':'not_run',
    'biological_validation':'not_run','physiological_time':'not_calibrated','complete_3d_loading_qualification':'not_run',
    'interpretation':'Similar integrated cavity responses do not certify pointwise volume control. Error remains in cells adjacent to the fixed base. Two curved meshes cannot separate geometry, clamp and pressure-space effects.',
    'next_action':'Pending confirmation: review/freeze a single-variable local volumetric-discretization qualification with unchanged material, load and basal clamp; include stability/locking checks before another shell solve. No further run authorized by this record.'}
audit={'status':'passed','checks':checks,'formal_files_unchanged':len(formal['files']),
    'protected_parent_files_unchanged':len(internal)+len(external),'preexisting_dirty_files_unchanged':len(dirty),
    'tests':tests,'repository_bytes':admission['repository']['usage']['logical_bytes'],'new_scientific_solves_in_postprocessing':0}
for name,value in [('summary.json',summary),('delivery_audit.json',audit),('delivery_storage.json',admission),
    ('rendering.json',{'status':'passed','scientific_status':'failed','figures':figures,'notebook_execution':'passed',
        'visual_qa':'passed','style_validation':'passed','deformation_scale':1,'interpolated_frames':0,
        'displayed_pressure_states':['M0 retained failed','M1 new failed'],'new_FEM_solves':0})]:
    save_json(root/name,value)
for relative in sorted(set(list(sources)+['src/prl/rendering/ventricle_3d.py','src/prl/rendering/ventricle_3d_resume.py'])):
    target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(workspace/relative,target)
for name in ['tests_before_run.json','tests_after_rendering.json','finalize.py']:
    target=root/'delivery_records'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(evidence/name,target)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F6-S2-D1 三维粗细网格同压力诊断</title><style>body{{max-width:1250px;margin:30px auto;padding:0 20px;font:16px/1.7 'Microsoft YaHei',sans-serif;color:#173e2e}}img{{width:100%}}a{{color:#176b4d}}td,th{{padding:6px 18px;border-bottom:1px solid #ddd}}</style>
<h1>细网格仍未通过局部体积门；不继续盲目加密</h1>
<p>真正三维半椭球三层壳，P2位移/P1连续压力、mu=1/kappa=1000；基底环全固定、外壁自由、内壁随动压力p/mu=0.01，Ta=0。
本轮只新增M1零载及首压力；M0原数据复用。一次{runtime['elapsed_seconds']:.3f}秒、1CPU/8GiB/0GPU/0重跑。
M1零载passed；首压力3次Newton收敛、MUMPS及独立场量复核passed，唯独原1%局部体积门failed。</p>
<table><tr><th>指标</th><th>M0</th><th>M1</th></tr><tr><td>四面体</td><td>1344</td><td>3960</td></tr>
<tr><td>腔体积增加</td><td>1.089525%</td><td>1.105919%</td></tr>
<tr><td>最大局部体积偏差</td><td>1.522743%</td><td>1.449560%</td></tr>
<tr><td>超过1%单元</td><td>96/1344</td><td>120/3960</td></tr>
<tr><td>远离基底的最大偏差</td><td>0.529615%</td><td>0.459731%</td></tr></table>
<p>腔体积响应相对差1.48235%，通过预定整体响应参考门；局部误差仅降4.80598%，两者仍failed。
超限单元均与固定基底相接，M1为心内膜72个、ECM48个、心肌0个。单元数变化不能直接当作失真总体加重：网格数及单元体积不同。
两网格曲面近似也不同，不是纯h细化，不能声称渐近收敛或已分离夹持/压力空间原因。</p>
<img src="{figures['png']}" alt="同压力粗细三维参考结构、等效应力及局部J偏差；共同色标、真实一倍形变，两压力态failed">
<p>全部形变、应力及J从实存u/p独立重算；无节点平滑。保留M1零载与压力的完整原始状态及压力Newton 0/1/2/3。
没有主动、生长、流体、实验材料标定或生理时间；没有伪造五个平衡态。</p>
<h2>下一步待确认</h2><p>先审查并冻结更局部的体积约束离散单变量方案，材料、载荷和基底暂不变。
先检查压力自由度、稳定性/锁死与小基准，再申请同载壳对照；不直接搬用二维通过结论，不放宽1%门。</p>
<p><a href="configuration.json">配置</a> · <a href="failure.json">原失败</a> · <a href="post_verification.json">M1独立复核</a> ·
<a href="mesh_diagnostic.json">粗细对照</a> · <a href="delivery_audit.json">保全验收</a> ·
<a href="{figures['notebook']}">Notebook</a> · <a href="{figures['svg']}">SVG</a></p>
<p>只读复核：python -B -X utf8 -m prl verify fem-idealized-3d --fine-first-pressure，预期failed。
run为create-only拒绝重复。91测试通过不等于局部门通过。无删除、安装、拉取、Docker修复或远端推送。</p></html>'''
(root/'index.html').write_text(page,encoding='utf-8')
save_json(root/'manifest.json',package_manifest(root)); manifest_sha=digest(root/'manifest.json')
register_result(workspace,root,'failed',manifest_sha)
output={'status':'failed','evidence_delivery':'passed','manifest_sha256':manifest_sha,
    'files':sum(p.is_file() for p in root.rglob('*')),'bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),'audit':audit}
save_json(evidence/'finalization.json',output); print(json.dumps(output,indent=2))
