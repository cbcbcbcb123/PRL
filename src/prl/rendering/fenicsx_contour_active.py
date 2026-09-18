"""Seal an independently verified active contour comparison without another solve."""
import json
from pathlib import Path
import shutil

from prl.result_store import result_path,result_admission,register_result
from prl.runs.fenicsx_contour_pressure import ACTIVE_RESULT,protected_unchanged
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import save_json
from .fenicsx_contour_pressure import audit_agreement


def finalize(workspace):
    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,ACTIVE_RESULT)
    if (root/'manifest.json').exists() or (root/'summary.json').exists():
        raise FileExistsError('Delivery already frozen')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    internal=json.loads((root/'protected_preflight.json').read_text())
    external=json.loads((root/'external_protected_preflight.json').read_text())
    dirty=json.loads((root/'preexisting_changes.json').read_text())
    identities=json.loads((root/'input_identities.json').read_text())
    sources=json.loads((root/'source_hashes.json').read_text())
    if (not protected_unchanged(workspace,internal,external,dirty)
        or not all(digest(root/item['path'])==item['sha256'] for item in formal['files'])
        or not all(digest(root/path)==item['sha256'] for path,item in identities.items())
        or not all(digest(workspace/path)==sha for path,sha in sources.items())):
        raise ValueError('Protected evidence, inputs or formal science source drift')
    report=json.loads((root/'post_verification.json').read_text())
    native=json.loads((root/'verification.json').read_text())
    agreement=audit_agreement(report,native)
    if agreement['status']!='passed':
        save_json(root/'delivery_comparison_failure.json',agreement)
        raise ValueError('Independent host/native reports differ; do not rerun FEM')
    runtime=json.loads((root/'execution.json').read_text())
    boundary=json.loads((root/'boundary_observations.json').read_text())
    tests=json.loads((root/'tests_after_rendering.json').read_text())
    if tests['status']!='passed' or boundary['status']!='passed':
        raise ValueError('Tests or supplementary boundary screen need attention')
    planned=[f'{name}_active_{i}' for name in ['M0','M1'] for i in range(1,5)]
    actual=[key for key in planned if (root/'iterates'/key).is_dir()]
    failed_at=[]
    for index,key in enumerate(actual):
        name,label=key.split('_',1)
        if report['cases'][name].get(label,{}).get('status')!='passed':
            failed_at.append(index)
    stop_checks={'attempts_exact_prefix':actual==planned[:len(actual)],
        'attempt_count':len(actual)==report['attempted_equilibria'],
        'first_failure_stops':not failed_at or failed_at==[len(actual)-1] and (root/'failure.json').exists(),
        'single_invocation':runtime['scientific_invocations']==1,'runtime_isolation':all(runtime['container_checks'].values()),
        'parents_preserved':runtime['parents_unchanged'],'no_gpu_or_retry':runtime['gpu']==0 and runtime['automatic_retries']==0,
        'no_recomputation':runtime['retained_equilibria_recomputed']==0}
    if not all(stop_checks.values()):
        raise ValueError('Execution scope or controlled stop not validated')
    figures={}
    for mode in ['active_overview','active_states']:
        revision=next((root/f'figures/FigS1S9_{mode}').glob('FigS1S9_*')); prefix=revision.name
        methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
        style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
        if '- 包状态: 最终包' not in methods or '人工/代理视觉验收: 通过' not in methods or not style['validation']['passed']:
            raise ValueError('Executed/final Notebook, style and visual QA required')
        if digest(revision/f'01_{prefix}_data.npz')!=digest(root/'figure_data.npz'):
            raise ValueError('Figure source copy mismatch')
        figures[mode]={kind:(revision/f'{number}_{prefix}{suffix}').relative_to(root).as_posix()
            for kind,number,suffix in [('notebook','03','_plot.ipynb'),('png','04','.png'),('svg','05','.svg')]}
    admission=result_admission(workspace,4*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Final storage admission refused')
    states=[{'mesh':name,'label':label,'source':case['source'],'status':case['status'],
        'pressure':case['pressure'],'activation':case['activation'],'cavity_area_change':case['cavity_area_change'],
        'area_change_from_pressurized_baseline':case['area_change_from_pressurized_baseline'],
        'max_abs_J_minus_one':case['max_abs_J_minus_one']} for name,rows in report['cases'].items() for label,case in rows.items()]
    monotonic={name:all(b['cavity_area']<a['cavity_area'] for a,b in zip(list(rows.values()),list(rows.values())[1:]))
        for name,rows in report['cases'].items()}
    summary={'status':report['status'],'engineering_execution':runtime['status'],'evidence_delivery':'passed',
        'attempted_new_equilibria':report['attempted_equilibria'],'accepted_new_equilibria':report['accepted_new_equilibria'],
        'reused_equilibria':4,'states':states,'monotonic_cavity_reduction_observed':monotonic,
        'saved_new_Newton_vectors':sum(len(case['states']) for rows in report['iterates'].values() for case in rows.values()),
        'elapsed_seconds':runtime['elapsed_seconds'],'independent_checks':len(report['checks']),
        'failed_checks':report['failed_checks'],'comparison':report['comparison'],'gpu':0,'automatic_retries':0,
        'high_pressure_qualification':'failed','physiological_time':'not_calibrated','three_dimensional_model':'not_run',
        'fsi':'not_run','growth':'not_run','biological_validation':'not_run',
        'next_action':'Pending approval: idealized 3D ventricular solid geometry and fibre field, then qualify low-pressure and active loading. Do not add FSI/growth or claim 2D DG2 qualification transfers directly to 3D.'}
    audit={'status':'passed','formal_invocation_files_unchanged':len(formal['files']),
        'protected_parent_files_unchanged':len(internal)+len(external),'preexisting_dirty_files_unchanged':len(dirty),
        'input_copies_match':len(identities),'host_native_independent_agreement':'passed','stop_checks':stop_checks,
        'tests':tests,'notebook_execution':'passed','style_validation':'passed','visual_qa':'passed',
        'postprocessing_new_FEM_solves':0,'repository_bytes':admission['repository']['usage']['logical_bytes']}
    rendering={'status':'passed','visual_qa':'passed','style_validation':'passed','figures':figures,
        'actual_saved_load_states':len(states),'new_FEM_solves':0,'deformation_scale':1,'interpolated_frames':0,
        'physiological_time':'not_calibrated','source':'copied raw meshes/u/p, unchanged independent NumPy mechanics'}
    for filename,value in [('summary.json',summary),('rendering.json',rendering),('delivery_audit.json',audit),
        ('delivery_storage.json',admission),('cross_platform_agreement.json',agreement)]:
        save_json(root/filename,value)
    delivery_sources=list(sources)+['src/prl/rendering/fenicsx_contour_pressure.py',
        'src/prl/rendering/fenicsx_contour_active.py','src/prl/verification/contour_boundary.py',
        'tests/prl/test_fenicsx_contour_pressure_render.py','tests/prl/test_contour_boundary.py']
    for relative in sorted(set(delivery_sources)):
        target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(workspace/relative,target)
    rows=''.join(f'<tr><td>{s["mesh"]}</td><td>{s["activation"]:.3f}</td><td>{s["source"]}</td>'
        f'<td>{s["area_change_from_pressurized_baseline"]*100:+.6f}%</td><td>{s["cavity_area_change"]*100:+.6f}%</td>'
        f'<td>{s["max_abs_J_minus_one"]*100:.6f}%</td><td>{s["status"]}</td></tr>' for s in states)
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F6-S1-S9 低压心肌主动收缩</title><style>body{{max-width:1400px;margin:32px auto;padding:0 20px;color:#173e2e;font:16px/1.7 'Microsoft YaHei',sans-serif}}img{{width:100%}}a{{color:#176b4d}}td,th{{padding:8px 12px;border-bottom:1px solid #ccd}}</style>
<h1>低压主动收缩：{report['status']}；主动张力部分抵消压力扩张</h1>
<p>二维P2/DG2平面应变有限变形Neo-Hookean，mu=1、kappa=1000未标定。只外轮廓来自图像，内腔/三层界面为构造。内腔固定随动压力p/mu=0.02、外壁自由；A固定ux/uy、B固定uy。</p>
<p>外侧构造心肌层使用既有主动能量Ta/2(|Ff0|²−1)，参考纤维f0=(-Y,X,0)/sqrt(X²+Y²)。纤维是关于原点的环向假设，不是实测纤维或逐点轮廓切向；其他层没有主动应力。</p>
<p>两网格各四个新增张力态，尝试{report['attempted_equilibria']}、接受{report['accepted_new_equilibria']}；零张力基线和无载态只读复用。{len(report['checks'])}项独立范围检查。粗细腔面积均随张力单调降低，但最高张力只相对受压基线缩小约1.85%，仍比无载参考态大约17.9%。这不是强收缩、心动周期或实验拟合。</p>
<table><tr><th>网格</th><th>Ta/mu</th><th>来源</th><th>相对受压基线</th><th>相对无载参考</th><th>局部max|J−1|</th><th>状态</th></tr>{rows}</table>
<img src="{figures['active_overview']['png']}" alt="结构与纤维假设、总和主动应力、J及缩腔曲线">
<h2>五个真实张力加载态</h2><p>统一等效应力色标、实际1倍形变。百分数相对同压力Ta=0基线。载荷级不是心动时间；无插值假帧。</p>
<img src="{figures['active_states']['png']}" alt="五个真实张力态及局部体积门">
<h2>适用边界</h2><p>旧0.08高压失败保持failed，本次没有高压重算或放宽1%门。二维两网格总面积响应通过不证明应力热点收敛，不直接授予三维离散资格。边界24/48段采样是筛查，不是全局单射证明。材料、压力、纤维、心动时序均未实验标定。</p>
<p>一次{runtime['elapsed_seconds']:.3f}秒、单CPU/8GiB/禁网/0GPU；{summary['saved_new_Newton_vectors']}个真实Newton向量保留，0自动重跑。{tests['passed']}测试+{tests['subtests_passed']}子测试通过，{len(internal)+len(external)}父/祖先文件和{len(dirty)}无关修改保持。</p>
<h2>唯一下一步（待确认）</h2><p>进入理想化三维心室固体：先建立几何/网格和可解释纤维方向，再检验低压与主动载荷。暂不加入血流或生长；不把当前二维结果称为三维心跳验证。</p>
<p><a href="post_verification.json">独立核验</a> · <a href="boundary_observations.json">边界筛查</a> · <a href="delivery_audit.json">交付审计</a> · <a href="configuration.json">配置</a> · <a href="command.json">唯一调用</a> · <a href="prerequisite/high_pressure_failure.json">保留高压失败</a> · <a href="{figures['active_overview']['notebook']}">结构/力学Notebook</a> · <a href="{figures['active_states']['notebook']}">五态Notebook</a></p>
<p>只读复核：python -B -X utf8 -m prl verify fem-fenicsx-contour-pressure --active-at-qualified-pressure。原run为create-only，不重跑冻结结果。图件可从版本内副本独立复算至新版本，无需求解器。</p></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    save_json(root/'manifest.json',package_manifest(root))
    register_result(workspace,root,summary['status'],digest(root/'manifest.json'))
    return {'status':summary['status'],'delivery':'passed','audit':audit,'manifest_sha256':digest(root/'manifest.json'),
        'files':sum(p.is_file() for p in root.rglob('*')),'logical_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file())}
