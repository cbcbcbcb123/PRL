"""Seal the first-pressure local-volume failure without changing its judgment."""
import json
from pathlib import Path
import shutil
from prl.result_store import result_admission,register_result
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import save_json

workspace=Path(__file__).resolve().parents[3]; evidence=Path(__file__).parent
root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918')
if (root/'manifest.json').exists() or (root/'summary.json').exists():
    raise FileExistsError('Delivery is already frozen')
def read(name):
    return json.loads((root/name).read_text())
formal=read('formal_invocation_manifest.json'); internal=read('protected_preflight.json')
external=read('external_protected_preflight.json'); dirty=read('preexisting_changes.json'); sources=read('source_hashes.json')
report=read('post_verification.json'); runtime=read('execution.json'); diagnosis=read('offline_diagnosis.json')
failure=read('failure.json'); restart=read('restart_interface.json')
tests=json.loads((evidence/'tests_after_rendering.json').read_text())
revision=next((root/'figures/FigS2R_3d_overview').glob('FigS2R_*')); prefix=revision.name
methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
checks={
    'formal_invocation_unchanged':all(digest(root/f['path'])==f['sha256'] for f in formal['files']),
    'protected_ancestors_and_dirty':protected_unchanged(workspace,internal,external,dirty),
    'scientific_execution_sources_unchanged':all(digest(workspace/p)==sha for p,sha in sources.items()),
    'input_copies_unchanged':all(digest(root/p)==sha for p,sha in read('input_identities.json').items()),
    'native_exact_restart_passed':restart['status']=='passed' and restart['new_equilibrium_solves']==0 and restart['newton_updates']==0,
    'mechanics_unchanged':read('mechanical_identity.json')['status']=='passed',
    'single_bounded_invocation':runtime['scientific_invocations']==1 and runtime['automatic_retries']==0 and runtime['runtime_microprobes']==0,
    'first_failure_stopped':failure['attempted_states']==1 and failure['accepted_states']==0 and
        sorted(p.name for p in (root/'iterates').iterdir())==['M0_pressure_1'],
    'new_raw_state_count_one':len(list((root/'raw').glob('*_state_*.npz')))==1,
    'runtime_isolation':all(runtime['container_checks'].values()) and runtime['gpu']==0 and not runtime['OOMKilled'],
    'only_local_volume_rejected':report['cases']['M0']['pressure_1']['failed_checks']==['local_volume'],
    'remaining_not_run':not report['cases']['M1'] and set(report['cases']['M0'])=={'zero','pressure_1'},
    'host_native_agreement':read('report_comparison.json')['status']=='passed',
    'offline_diagnosis_passed':diagnosis['status']=='passed' and diagnosis['new_FEM_solves']==0,
    'tests_passed':tests['status']=='passed',
    'figure_executed_visual_and_style':('- 包状态: 最终包' in methods and '人工/代理视觉验收: 通过' in methods and style['validation']['passed']),
    'figure_physical_data_copy':digest(root/'figure_data.npz')==digest(revision/f'01_{prefix}_data.npz'),
    'portable_helper_matches':digest(workspace/'src/prl/rendering/ventricle_3d_resume.py')==digest(next(revision.glob('*_helper.py'))),
    'portable_mechanics_matches':digest(workspace/'src/prl/verification/ventricle_3d.py')==digest(next(revision.glob('*_mechanics.py'))),
}
if not all(checks.values()):
    raise ValueError('Delivery blocked: '+str([k for k,v in checks.items() if not v]))
admission=result_admission(workspace,4*1024**2)
if not admission['can_start']:
    raise RuntimeError('Storage refused')
figures={kind:(revision/f'{number}_{prefix}{suffix}').relative_to(root).as_posix()
    for kind,number,suffix in [('notebook','03','_plot.ipynb'),('png','04','.png'),('svg','05','.svg')]}
summary={'status':'failed','native_interface_validation':'passed','nonlinear_equilibrium':'passed',
    'loaded_state_acceptance':'failed','evidence_delivery':'passed','reason':'M0 first pressure violates frozen local-volume gate.',
    'attempted_new_equilibria':1,'accepted_new_equilibria':0,'retained_zero_reused':1,'newton_updates':3,
    'remaining_count':12,'remaining_equilibria':'not_run','pressure_loading':'failed','active_loading':'not_run',
    'mesh_response':'not_run','pressure_state':report['cases']['M0']['pressure_1'],
    'diagnosis':diagnosis,'elapsed_seconds':runtime['elapsed_seconds'],'scientific_invocations':1,
    'gpu':0,'automatic_retries':0,'fsi':'not_run','growth':'not_run','biological_validation':'not_run',
    'physiological_time':'not_calibrated',
    'next_action':'Pending confirmation: existing M1 zero then p=0.01 only, unchanged physics/thresholds, compare with retained M0 failure; no active/growth/FSI.'}
audit={'status':'passed','checks':checks,'formal_files_unchanged':len(formal['files']),
    'protected_parent_files_unchanged':len(internal)+len(external),'preexisting_dirty_files_unchanged':len(dirty),
    'tests':tests,'repository_bytes':admission['repository']['usage']['logical_bytes'],
    'new_scientific_solves_in_postprocessing':0}
for name,value in [('summary.json',summary),('delivery_audit.json',audit),('delivery_storage.json',admission),
    ('rendering.json',{'status':'passed','scientific_status':'failed','figures':figures,'notebook_execution':'passed',
        'visual_qa':'passed','style_validation':'passed','displayed_states':['M0 retained zero','M0 pressure_1 rejected'],
        'deformation_scale':1,'interpolated_frames':0,'new_FEM_solves':0})]:
    save_json(root/name,value)
for relative in sorted(set(list(sources)+['src/prl/rendering/ventricle_3d.py','src/prl/rendering/ventricle_3d_resume.py',
                                        'tests/prl/test_ventricle_3d_delivery.py'])):
    target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(workspace/relative,target)
for name in ['tests_before_run.json','tests_after_rendering.json','diagnose_retained.py','finalize.py']:
    target=root/'delivery_records'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(evidence/name,target)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F6-S2-R 三维首压力：平衡收敛，局部体积门失败</title>
<style>body{{max-width:1150px;margin:32px auto;padding:0 20px;font:16px/1.7 'Microsoft YaHei',sans-serif;color:#173e2e}}img{{width:100%}}a{{color:#176b4d}}</style>
<h1>三维首压力已求解；局部体积门失败，停止后续加载</h1>
<p>原无载向量逐项身份与原生接口复核passed，未重求无载。一次{runtime['elapsed_seconds']:.3f}秒容器，1CPU、0GPU、0重跑。
M0的p/mu=0.01、Ta=0状态经3次Newton达到平衡，残差1.69e-16，MUMPS/场量独立重算通过；
但max|J-1|=1.522743%，超过1%门限，本态不接受，余12态not_run。</p>
<p>模型：真正三维半椭球壳，心内膜/ECM/心肌三域，同mu=1、kappa=1000；P2位移/P1压力四面体。
基底环全固定、外壁自由、内腔随动压力。主动规则已定义但本轮尚未到达收缩分支；不是心动周期或实验模型。</p>
<img src="{figures['png']}" alt="三维剖开结构、首压力真实应力与局部J误差、腔体积响应；失败状态明确标注">
<p>真实1倍形变：腔体积扩大1.089525%，最大位移0.004042L。四面体无翻转；
96/1344单元超过局部门，全部是含固定基底顶点的单元，远离基底最大0.529615%。
积分点本身也达到1.314813%，并非只在额外采样点超限。</p>
<p>体积加权平均J-1仅5.77e-6、压力弱残差1.81e-18，仍不能替代逐点门限。
确定的是局部约束误差；网格、夹持与连续压力空间的贡献尚未分离，不擅自提高kappa或放宽门限。</p>
<h2>下一步待确认</h2><p>只用已有M1几何做零载和同p=0.01两个状态，与本包M0比较。
保持材料、边界、离散与1%门，首失败停；不继续主动、生长或FSI。通过也只算网格诊断，不冒充全阶段合格。</p>
<p><a href="configuration.json">配置</a> · <a href="restart_interface.json">原生接口资格</a> ·
<a href="failure.json">失败原件</a> · <a href="post_verification.json">独立复核</a> ·
<a href="offline_diagnosis.json">空间定位</a> · <a href="delivery_audit.json">保全验收</a> ·
<a href="{figures['notebook']}">Notebook</a> · <a href="{figures['svg']}">SVG</a></p>
<p>只读复核：python -B -X utf8 -m prl verify fem-idealized-3d --resume-qualified-zero。
命令应返回failed；run为create-only，拒绝重跑。无删除、安装、拉取、推送或新生理结论。</p></html>'''
(root/'index.html').write_text(page,encoding='utf-8')
save_json(root/'manifest.json',package_manifest(root)); manifest_sha=digest(root/'manifest.json')
register_result(workspace,root,'failed',manifest_sha)
output={'status':'failed','evidence_delivery':'passed','manifest_sha256':manifest_sha,
    'files':sum(p.is_file() for p in root.rglob('*')),'bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),'audit':audit}
save_json(evidence/'finalization.json',output); print(json.dumps(output,indent=2))
