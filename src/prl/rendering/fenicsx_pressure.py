"""Reproducible plots from preserved pressure-space states; no FEM solves."""
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np


def prepare(workspace, skill_root):
    """Create a diagnostic figure package from saved states, without a solver."""
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path,result_admission
    from prl.runs.fenicsx_pressure import RESULT
    from prl.runs.fenicsx_ring import digest
    from prl.verification.fenicsx_pressure import verify_pressure,volume_projection
    from prl.verification.fenicsx_ring import load_arrays,fields

    workspace=Path(workspace).resolve(strict=True)
    root=result_path(workspace,RESULT)
    if (root/'post_verification.json').exists() or (root/'figures').exists():
        raise FileExistsError('Delivery preparation is create-only')
    if not result_admission(workspace,32*1024**2)['can_start']:
        raise RuntimeError('Postprocessing storage admission refused')
    frozen=json.loads((root/'formal_invocation_manifest.json').read_text())
    if not all(digest(root/f['path'])==f['sha256'] for f in frozen['files']):
        raise ValueError('Preserved invocation changed')
    report=verify_pressure(root)
    # File presence alone is not successful equilibrium completion.
    report['accepted_equilibria']=sum(r['status']=='passed' for c in report['cases'].values() for r in c.values())
    report['contour_status']='not_run' if not report['cases']['contour'] else report['status']
    report['interpretation']='No nonzero-load DG2 equilibrium; J=1 is the initial iterate, not a volume repair. Response checks do not prove locking in a failed linear solve.'
    with (root/'post_verification.json').open('x',encoding='utf-8') as handle:
        json.dump(report,handle,indent=2)
    fine=result_path(workspace,Path('results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917'))/'raw'
    fine_files=[fine/'M1_mesh.npz',fine/'M1_state_passive_1.npz']
    projection={'coarse':report['retained_CG1']['contour']['projection'],
        'fine':volume_projection(*(load_arrays(p) for p in fine_files)),
        'fine_sources':{str(p):digest(p) for p in fine_files},
        'meaning':'Squared L2 norm fraction, not volume fraction or biological validation; no mechanical solve.'}
    with (root/'volume_projection.json').open('x',encoding='utf-8') as handle:
        json.dump(projection,handle,indent=2)
    old_mesh=load_arrays(root/'comparison/ring/mesh.npz')
    old_state=load_arrays(root/'comparison/ring/state.npz')
    old_fields=fields(old_mesh,old_state)
    new_mesh=load_arrays(root/'ring/raw/M0_mesh.npz')
    meta=json.loads((root/'ring/raw/M0_state_passive_1.json').read_text())
    if meta['snes_reason']!=-3 or meta['iterations']!=0:
        raise ValueError('This figure is specifically a first-linear-solve failure diagnostic')
    data={f'new_{k}':new_mesh[k] for k in ['coordinates','cells','layers','fixed']}
    data.update({f'old_{k}':old_mesh[k] for k in ['coordinates','cells']})
    data.update(old_u=old_state['u'],old_stress=old_fields['stress'],old_J=old_fields['J'],
        object=np.array('Ideal annulus'),iterations=np.array([h['iteration'] for h in meta['history']]),
        residuals=np.array([h['residual'] for h in meta['history']]))
    np.savez_compressed(root/'figure_data.npz',**data)
    skills=Path(skill_root)
    command=[sys.executable,'-B','-X','utf8',str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
        str(root/'figures'),'--main','S1R','--analysis-key','pressure_failure','--data',str(root/'figure_data.npz'),
        '--python','helper='+str(Path(__file__).resolve()),
        '--python','style='+str(skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'),
        '--data-role','old_mesh='+str(root/'comparison/ring/mesh.npz'),
        '--data-role','old_state='+str(root/'comparison/ring/state.npz'),
        '--data-role','new_mesh='+str(root/'ring/raw/M0_mesh.npz'),
        '--data-role','new_state='+str(root/'ring/raw/M0_state_passive_1.npz'),
        '--model','diagnosis='+str(root/'post_verification.json')]
    subprocess.run(command,check=True)
    revision=next((root/'figures/FigS1R_pressure_failure').glob('FigS1R_*'))
    prefix=revision.name
    helper=next(revision.glob('*_helper.py')).name
    style=next(revision.glob('*_style.py')).name
    notebook=nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell('# F6-S1-R 压力空间失败诊断\n只读已保存状态；不重新求解。B/C为旧CG1平衡解，D为新DG2失败残量。\n二维无量纲、1倍变形；不是三维、生理时间或生长证据。'),
        nbformat.v4.new_code_cell(f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 复用项目紧凑FEM风格；尺寸是每个主轴的物理宽高（英寸）。
STYLE_SOURCE = 'Existing compact FEM diagnostics with CB style'
DPI = 600
axis_box_size_in = (3.7, 3.7)
FIGURE_SIZE_IN = (13.8, 12.0)
figure_size_in = FIGURE_SIZE_IN
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
helper = load_snapshot('pressure_plot_snapshot', {helper!r})
style = load_snapshot('cb_style_snapshot', {style!r})
summary = helper.draw(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, style, axis_box_size_in, figure_size_in)
summary'''),
        nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=900))')],
        metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
    nbformat.write(notebook,revision/f'03_{prefix}_plot.ipynb')
    methods=revision/f'02_{prefix}_methods.txt'
    content=methods.read_text(encoding='utf-8')
    replacements={
        '风格来源':'沿用F6-S1-Q紧凑FEM诊断图；CB统一风格，显式3.7英寸方轴及留白；600 dpi PNG和可编辑SVG。',
        '用户提供的期刊规格':'未指定；用于科学诊断，不是排版后的投稿成图。',
        '03_材料方法来源':'版本包内helper/style源码快照及diagnosis审计；原始旧/新mesh/state也物理复制保留。',
        '数据/模型变换':'独立NumPy从旧CG1位移/压力重算J和应力；1倍变形；六节点三角形拆成四个显示子三角。应力为等效Cauchy应力积分点算术均值，J为单元积分点最大绝对偏差；不平滑、不改数据。新DG2仅显示迭代0残量，无压力平衡解。',
        '统计方法与不确定性':'确定性数值状态；不适用生物样本统计、误差棒和显著性。原始p/mu=0.02；算法迭代不是生理时间。',
        '生物学分组颜色':'不适用；绿/黄/蓝表示假设的心内膜/ECM/心肌材料域，不表示生物实验组。'}
    for key,value in replacements.items():
        content=re.sub(r'(?m)^- '+re.escape(key)+r':.*$',lambda match:'- '+key+': '+value,content)
    methods.write_text(content,encoding='utf-8')
    return {'status':'passed','scientific_status':report['status'],'revision':str(revision),'equilibria_computed':0}


def finalize(workspace):
    """Freeze checked diagnostic deliverables; never upgrades scientific status."""
    import shutil
    from prl.result_store import result_path,register_result
    from prl.runs.fenicsx_pressure import RESULT
    from prl.runs.fenicsx_ring import digest,package_manifest

    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,RESULT)
    if (root/'manifest.json').exists() or (root/'summary.json').exists():
        raise FileExistsError('The result package is already finalized')
    revision=next((root/'figures/FigS1R_pressure_failure').glob('FigS1R_*'))
    prefix=revision.name
    methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    if '- 包状态: 最终包' not in methods:
        raise ValueError('Notebook execution and visual QA must precede result freezing')
    original=json.loads((root/'formal_invocation_manifest.json').read_text())
    unchanged=all(digest(root/f['path'])==f['sha256'] for f in original['files'])
    internal=json.loads((root/'protected_preflight.json').read_text())
    external=json.loads((root/'external_protected_preflight.json').read_text())
    parents=all(digest(workspace/p)==h for p,h in internal.items()) and all(digest(p)==h for p,h in external.items())
    if not unchanged or not parents:
        raise ValueError('Protected scientific evidence changed during postprocessing')
    report=json.loads((root/'post_verification.json').read_text())
    runtime=json.loads((root/'execution.json').read_text())
    summary={'status':report['status'],'engineering_delivery':'passed','accepted_equilibria':report['accepted_equilibria'],
        'saved_states':report['new_saved_states'],'contour':report['contour_status'],
        'interpretation':report['interpretation'],'scientific_invocations':runtime['scientific_invocations'],
        'automatic_retries':0,'gpu':0,'formal_invocation_unchanged':unchanged,
        'protected_parent_files':len(internal)+len(external),'parents_unchanged':parents,
        'three_dimensional_FSI_growth':'not_run','biological_validation':'not_run',
        'next_step':'Obtain mixed linear system diagnostics before a separately approved repair solve.'}
    rendering={'status':'passed','source':'preserved states only','new_equilibrium_solves':0,
        'notebook':str((revision/f'03_{prefix}_plot.ipynb').relative_to(root)),
        'png':str((revision/f'04_{prefix}.png').relative_to(root)),
        'svg':str((revision/f'05_{prefix}.svg').relative_to(root)),
        'visual_qa':'passed','style_validation':'passed','scientific_status':report['status'],
        'temporary_directory':str(root/'figure_runtime'),'temporary_cleanup':'not_authorized',
        'source_helper_sha256':digest(revision/f'03c_{prefix}_helper.py')}
    for name,data in [('summary.json',summary),('rendering.json',rendering)]:
        with (root/name).open('x',encoding='utf-8') as handle:
            json.dump(data,handle,indent=2)
    (root/'sources_at_delivery').mkdir(exist_ok=False)
    shutil.copyfile(__file__,root/'sources_at_delivery/fenicsx_pressure_rendering.py')
    for name in ['ventricle_fem_pressure_space_execution_v01.md','ventricle_development_fsg_idealized_public_data_decision_v01.md']:
        shutil.copyfile(workspace/'project_control'/name,root/'sources_at_delivery'/name)
    with (root/'manifest.json').open('x',encoding='utf-8') as handle:
        json.dump(package_manifest(root),handle,indent=2)
    register_result(workspace,root,report['status'],digest(root/'manifest.json'))
    return summary


def draw(data_path,png_path,svg_path,style_module,axis_box_size_in=(3.7,3.7),figure_size_in=(13.8,12.0)):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    from matplotlib.ticker import FixedLocator,NullFormatter

    with np.load(data_path,allow_pickle=False) as archive:
        data={k:archive[k] for k in archive.files}
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=16.,axis_label_size=18.,annotation_font_size=16.,sample_size_and_stat_font_size=14.,
        legend_font_size=14.,axes_line_width=1.5,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    baseline=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=k,reason='Established compact FEM diagnostic style; equal-scale spatial panels and explicit margins.')
               for k,v in asdict(style).items() if v!=baseline[k]]
    width,height=figure_size_in; side=axis_box_size_in[0]
    figure=plt.figure(figsize=figure_size_in)
    axes=[figure.add_axes((left/width,bottom/height,side/width,side/height)) for left,bottom in
          [(1.1,7.0),(8.0,7.0),(1.1,1.4),(8.0,1.4)]]
    parts=np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    current=data['old_coordinates']+data['old_u']
    old_triangles=(data['old_coordinates']+data['old_u'])[data['old_cells'][:,parts]].reshape(-1,3,2)
    reference=data['new_coordinates'][data['new_cells'][:,parts]].reshape(-1,3,2)
    colors=np.array(['#4C9F70','#D6B656','#5B8DB8'])
    axes[0].add_collection(PolyCollection(reference,facecolors=np.repeat(colors[data['new_layers']-1],4),
        edgecolors=(.1,.1,.1,.25),linewidths=.12))
    for component,marker in [(0,'s'),(1,'^')]:
        indices=np.flatnonzero(data['new_fixed'][:,component])
        axes[0].plot(*data['new_coordinates'][indices].T,linestyle='none',marker=marker,color='#BA3E34',ms=6)
    stress=data['old_stress']; deviator=stress-np.trace(stress,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
    equivalent=np.sqrt(1.5*np.sum(deviator**2,axis=(-1,-2))).mean(axis=1)
    stress_map=PolyCollection(old_triangles,array=np.repeat(equivalent,4),cmap='viridis',edgecolors=(0,0,0,.15),linewidths=.1)
    axes[1].add_collection(stress_map)
    axes[1].add_collection(PolyCollection(reference,facecolors='none',edgecolors=(.3,.3,.3,.10),linewidths=.1))
    old_j=np.max(np.abs(data['old_J']-1),axis=1)*100
    maximum=float(old_j.max())
    normalization=Normalize(0,maximum)
    collection=PolyCollection(old_triangles,array=np.repeat(old_j,4),norm=normalization,cmap='magma',
                              edgecolors=(0,0,0,.15),linewidths=.1)
    axes[2].add_collection(collection)
    all_points=np.vstack((data['new_coordinates'],current,data['old_coordinates']+data['old_u']))
    center=(all_points.min(axis=0)+all_points.max(axis=0))/2
    half=np.ptp(all_points,axis=0).max()*.57
    old_peak=float(old_j.max())
    titles=['Same reference mesh and gauges','CG1 retained equilibrium: stress / mu',
            f'CG1 retained: peak |J - 1| = {old_peak:.4f}%', 'DG2: linear solve failed at step 0']
    for axis,title in zip(axes[:3],titles[:3]):
        axis.set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),xlabel='x / L',ylabel='y / L')
        axis.set_aspect('equal')
        for values,locator in [(axis.get_xlim(),axis.xaxis),(axis.get_ylim(),axis.yaxis)]:
            locator.set_major_locator(FixedLocator(np.arange(np.ceil(values[0]),np.floor(values[1])+1)))
        style_module.apply_axes_style(axis,style=style)
        style_module.add_top_information(axis,title,style=style)
    axes[3].plot(data['iterations'],data['residuals'],'o',color='#BA3E34',markersize=8)
    axes[3].axhline(1e-9,color='#777777',linestyle='--',linewidth=1.5)
    axes[3].set(xlim=(-.5,1.),ylim=(1e-11,1.),yscale='log',xlabel='Newton updates',ylabel='Free residual norm')
    axes[3].xaxis.set_major_locator(FixedLocator([0,1]))
    axes[3].yaxis.set_major_locator(FixedLocator([1e-10,1e-7,1e-4,1e-1]))
    axes[3].text(.08,.70,f"Residual = {float(data['residuals'][-1]):.3e}\nSNES reason = -3\nNo accepted pressure equilibrium",transform=axes[3].transAxes,fontsize=14,va='top')
    style_module.apply_axes_style(axes[3],style=style)
    axes[3].yaxis.set_minor_locator(FixedLocator([1e-9,1e-8,1e-6,1e-5,1e-3,1e-2]))
    axes[3].yaxis.set_minor_formatter(NullFormatter())
    style_module.add_top_information(axes[3],titles[3],style=style)
    stress_axis=figure.add_axes((12.05/width,7.0/height,.20/width,side/height))
    volume_axis=figure.add_axes((5.15/width,1.4/height,.20/width,side/height))
    figure.colorbar(stress_map,cax=stress_axis).set_label('Mean equivalent stress / mu',fontsize=14,labelpad=10)
    figure.colorbar(collection,cax=volume_axis).set_label('Element max |J - 1| (%)',fontsize=14,labelpad=10)
    for axis in [stress_axis,volume_axis]:
        axis.tick_params(labelsize=14)
    figure.text(.085,.963,f"{str(data['object'])}: p / mu = 0.02 | DG2 attempt FAILED; old CG1 equilibrium retained",fontsize=14)
    figure.text(.085,.515,'Fields shown are the OLD CG1 control. DG2 stopped before the first Newton update.',fontsize=14)
    figure.text(.085,.035,'Assumed endo / ECM / myo: green / yellow / blue. DG2 J = 1 at the initial iterate is NOT a qualified response.',fontsize=13)
    exported=style_module.export_figure(figure,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    if Path(exported.svg)!=Path(svg_path):
        Path(exported.svg).replace(svg_path)
        manifest=json.loads(Path(exported.manifest).read_text())
        manifest['exports']['svg']=str(Path(svg_path).resolve())
        Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.close(figure)
    return {'object':str(data['object']),'old_peak_percent':old_peak,'DG2_status':'failed','equilibria_computed':0}


def prepare_resume_failure(workspace,skill_root):
    """Save an honest monitor-failure figure; do not fabricate a pressure state."""
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path,result_admission
    from prl.runs.fenicsx_pressure import RESUME_RESULT
    from prl.runs.fenicsx_ring import digest
    from prl.verification.fenicsx_pressure import verify_pressure
    from prl.verification.fenicsx_ring import load_arrays,fields,cavity
    root=result_path(workspace,RESUME_RESULT); skills=Path(skill_root)
    if (root/'post_verification.json').exists() or (root/'figures').exists():
        raise FileExistsError('Failure figure preparation is create-only')
    if not result_admission(workspace,32*1024**2)['can_start']:
        raise RuntimeError('Figure storage admission refused')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    if not all(digest(root/item['path'])==item['sha256'] for item in formal['files']):
        raise ValueError('Original invocation changed')
    report=verify_pressure(root)
    if report['state'] is not None or not report['checks'].get('failed_initial_preserved'):
        raise ValueError('This figure requires the saved, unchanged initial failure state')
    (root/'post_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    mesh=load_arrays(root/'ring/raw/M0_mesh.npz')
    mixed=load_arrays(root/'last_attempt.npz')['mixed_state']
    state={'u':mixed[mesh['mixed_u_map']].reshape(-1,2),'pressure':mixed[mesh['mixed_p_map']],
           'load':.02,'activation':0.}
    actual=fields(mesh,state); force=actual['force']-cavity(mesh,state['u'],.02)[1]
    data={k:mesh[k] for k in ['coordinates','cells','fixed','layers','inner_edges']}
    data.update(force=force,u=state['u'],free_norm=np.linalg.norm(force[~mesh['fixed']]))
    np.savez_compressed(root/'figure_data.npz',**data)
    command=[sys.executable,'-B','-X','utf8',str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
        str(root/'figures'),'--main','S1S4','--analysis-key','monitor_failure','--data',str(root/'figure_data.npz'),
        '--python','helper='+str(Path(__file__).resolve()),
        '--python','style='+str(skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'),
        '--data-role','mesh='+str(root/'ring/raw/M0_mesh.npz'),
        '--data-role','initial='+str(root/'ring/raw/M0_attempt.npz'),
        '--data-role','last_attempt='+str(root/'last_attempt.npz'),
        '--model','verification='+str(root/'post_verification.json'),
        '--model','failure='+str(root/'failure.json')]
    subprocess.run(command,check=True)
    revision=next((root/'figures/FigS1S4_monitor_failure').glob('FigS1S4_*')); prefix=revision.name
    helper=next(revision.glob('*_helper.py')).name; style=next(revision.glob('*_style.py')).name
    notebook=nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell('# F6-S1-S4 监测接口失败证据\n保存初始态未更新；不是受压平衡。只读复算，不重新求解。'),
        nbformat.v4.new_code_cell(f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 作图调整参数：沿用项目紧凑FEM诊断风格；不放大初始形变。
STYLE_SOURCE = 'Existing compact FEM diagnostic style with CB style'
DPI = 600
axis_box_size_in = (3.7, 3.7)
FIGURE_SIZE_IN = (14.4, 7.4)
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
helper = load_snapshot('pressure_failure_plot', {helper!r})
style = load_snapshot('cb_style_snapshot', {style!r})
helper.draw_resume_failure(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, style, axis_box_size_in, FIGURE_SIZE_IN)'''),
        nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=1000))')],
        metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
    nbformat.write(notebook,revision/f'03_{prefix}_plot.ipynb')
    methods=revision/f'02_{prefix}_methods.txt'; content=methods.read_text(encoding='utf-8')
    replacements={
        '风格来源':'沿用紧凑FEM诊断图，CB统一风格；3.7英寸方轴，显式边距；600 dpi PNG和可编辑SVG。',
        '用户提供的期刊规格':'未指定；内部失败诊断，不是投稿成图。',
        '03_材料方法来源':'不适用通用模板目录；本项目稳定方法为src/prl/verification/fenicsx_ring.py，复制的mesh/initial/last_attempt及verification构成本图输入。helper/style为版本内物理快照。',
        '数据/模型变换':'从保存混合初值映射u/p，独立积分内力减去随动腔压外力；每节点残量向量取2范数，单元显示六节点最大值，无插值平滑。六节点三角形拆四个显示子三角。初始u=0；不是计算出的受压形变或接受态。',
        '统计方法与不确定性':'确定性离散初值，无生物统计/误差棒/显著性。保留初值与末次尝试逐字节相同。回调失败于首次Newton更新前，因此无多时刻结果、不补造帧。',
        '生物学分组颜色':'不适用；三种颜色仅为假设的材料域标签，当前被动材料相同。'}
    for key,value in replacements.items():
        content=re.sub(r'(?m)^- '+re.escape(key)+r':.*$',lambda match:'- '+key+': '+value,content)
    methods.write_text(content,encoding='utf-8')
    return {'revision':str(revision),'scientific_status':'failed','new_equilibria':0}


def draw_resume_failure(data_path,png_path,svg_path,style_module,axis_box_size_in=(3.7,3.7),figure_size_in=(14.4,7.4)):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.ticker import FixedLocator
    with np.load(data_path,allow_pickle=False) as archive:
        data={k:archive[k] for k in archive.files}
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=16.,axis_label_size=18.,annotation_font_size=16.,sample_size_and_stat_font_size=14.,
        legend_font_size=14.,axes_line_width=1.5,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    baseline=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=k,reason='Existing compact FEM diagnostics; equal-scale spatial panels and explicit margins.')
               for k,v in asdict(style).items() if v!=baseline[k]]
    width,height=figure_size_in; side=axis_box_size_in[0]
    figure=plt.figure(figsize=figure_size_in)
    axes=[figure.add_axes((left/width,1.65/height,side/width,side/height)) for left in [1.1,8.0]]
    parts=np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    triangles=data['coordinates'][data['cells'][:,parts]].reshape(-1,3,2)
    colors=np.array(['#4C9F70','#D6B656','#5B8DB8'])
    axes[0].add_collection(PolyCollection(triangles,facecolors=np.repeat(colors[data['layers']-1],4),edgecolors=(0,0,0,.25),linewidths=.12))
    for component,marker in [(0,'s'),(1,'^')]:
        indices=np.flatnonzero(data['fixed'][:,component])
        axes[0].plot(*data['coordinates'][indices].T,linestyle='none',marker=marker,color='#BA3E34',ms=6)
    angles=np.linspace(0,2*np.pi,12,endpoint=False)
    for angle in angles:
        direction=np.array([np.cos(angle),np.sin(angle)])
        axes[0].annotate('',xy=direction*.76,xytext=direction*.60,
                         arrowprops={'arrowstyle':'->','color':'#A92D28','lw':1.2})
    axes[0].text(0,0,'p / mu = 0.02\nactive = 0\nouter wall free',ha='center',va='center')
    value=np.linalg.norm(data['force'],axis=1)[data['cells']].max(axis=1)
    field=PolyCollection(triangles,array=np.repeat(value,4),cmap='magma',edgecolors=(0,0,0,.15),linewidths=.1)
    axes[1].add_collection(field)
    axes[1].text(0,0,f"Initial guess only\nFree residual norm\n{float(data['free_norm']):.3e}",ha='center',va='center')
    for axis,title in zip(axes,['A  Reference mesh and gauges','B  Initial force imbalance']):
        axis.set(xlim=(-1.16,1.16),ylim=(-1.16,1.16),xlabel='x / L',ylabel='y / L',aspect='equal')
        axis.xaxis.set_major_locator(FixedLocator([-1,0,1])); axis.yaxis.set_major_locator(FixedLocator([-1,0,1]))
        style_module.apply_axes_style(axis,style=style)
        style_module.add_top_information(axis,title,style=style)
    cax=figure.add_axes((12.05/width,1.65/height,.20/width,side/height))
    figure.colorbar(field,cax=cax).set_label('Max nodal residual per element',fontsize=14,labelpad=10)
    cax.tick_params(labelsize=14)
    figure.text(.077,.885,'F6-S1-S4 FAILED: monitor requested writable access to a read-locked PETSc vector.',fontsize=14)
    figure.text(.077,.825,'No accepted pressure equilibrium; saved state unchanged; no physiological time or volume qualification.',fontsize=14)
    figure.text(.077,.055,'Green / yellow / blue: assumed endo / ECM / myo domains (same passive law). Red squares/triangles: x/y gauges.',fontsize=13)
    exported=style_module.export_figure(figure,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    if Path(exported.svg)!=Path(svg_path):
        Path(exported.svg).replace(svg_path)
        manifest=json.loads(Path(exported.manifest).read_text()); manifest['exports']['svg']=str(Path(svg_path).resolve())
        Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.close(figure)
    return {'scientific_status':'failed','accepted_pressure_states':0,'free_initial_residual':float(data['free_norm'])}


def finalize_resume_failure(workspace):
    """Freeze the failed invocation and separately identify unvalidated patches."""
    import shutil
    from prl.result_store import result_path,register_result
    from prl.runs.fenicsx_pressure import RESUME_RESULT
    from prl.runs.fenicsx_ring import digest,package_manifest
    from prl.runs.fenicsx_runtime import save_json
    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,RESUME_RESULT)
    if (root/'manifest.json').exists():
        raise FileExistsError('Failure package already frozen')
    original=json.loads((root/'formal_invocation_manifest.json').read_text())
    internal=json.loads((root/'protected_preflight.json').read_text())
    external=json.loads((root/'external_protected_preflight.json').read_text())
    unchanged=all(digest(root/item['path'])==item['sha256'] for item in original['files'])
    parents=all(digest(workspace/p)==sha for p,sha in internal.items()) and all(digest(p)==sha for p,sha in external.items())
    preexisting=json.loads((root/'preexisting_changes.json').read_text())
    dirty_unchanged=all(digest(workspace/item['path'])==item['sha256'] for item in preexisting)
    if not unchanged or not parents or not dirty_unchanged:
        raise ValueError('Protected evidence or unrelated edits changed')
    report=json.loads((root/'post_verification.json').read_text())
    if report['accepted_equilibria']!=0 or report['state'] is not None or not report['checks'].get('failed_initial_preserved'):
        raise ValueError('Expected unchanged initial-state failure')
    revision=next((root/'figures/FigS1S4_monitor_failure').glob('FigS1S4_*')); prefix=revision.name
    if '- 包状态: 最终包' not in (revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8'):
        raise ValueError('Final figure QA required')
    rendering={'status':'passed','visual_qa':'passed','style_validation':'passed','new_equilibrium_solves':0,
               'notebook':(revision/f'03_{prefix}_plot.ipynb').relative_to(root).as_posix(),
               'png':(revision/f'04_{prefix}.png').relative_to(root).as_posix(),
               'svg':(revision/f'05_{prefix}.svg').relative_to(root).as_posix(),
               'meaning':'Initial loaded guess and force imbalance, NOT a deformed pressure equilibrium',
               'temporary_cleanup':'not_authorized; figure_runtime retained'}
    summary={'status':'failed','engineering_execution':'failed','evidence_delivery':'passed',
             'cause':'new monitor used writable Vec.array on a read-locked PETSc vector; error 73/101 before first Newton update',
             'newton_updates':0,'nonlinear_attempts':1,'accepted_pressure_equilibria':0,'zero_load_reruns':0,
             'automatic_retries':0,'gpu':0,'independent_initial_free_force':report['failed_initial']['independent_free_force_norm'],
             'patch_written':True,'patch_protocol_tests':'passed','patch_original_runtime_verification':'not_run',
             'actual_mumps_margin_this_attempt':None,'volume_qualification_this_attempt':'not_run',
             'old_contour_volume_gate':'failed','contour':'not_run','active_contraction':'not_run','three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run',
             'next_action':'pending approval: same-environment observer/options microtest, then one original first-pressure state; fail-stop, no automatic retry'}
    save_json(root/'rendering.json',rendering); save_json(root/'summary.json',summary)
    sources=list(json.loads((root/'source_hashes.json').read_text()))+[
        'src/prl/rendering/fenicsx_pressure.py','src/prl/cli.py','tests/prl/test_fenicsx_pressure.py',
        'project_control/ventricle_fem_ring_resume_execution_v01.md']
    for relative in sources:
        target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(workspace/relative,target)
    save_json(root/'delivery_audit.json',{'status':'passed','scientific_execution':'failed',
        'formal_invocation_files_unchanged':len(original['files']),
        'protected_files_unchanged':len(internal)+len(external),'preexisting_dirty_files_unchanged':len(preexisting),
        'before_run_tests':58,'after_patch_tests':60,'subtests':21,'original_runtime_patch_check':'not_run',
        'postprocess_new_fem_solves':0,'postprocess_global_factorizations':0,'visual_qa':'passed',
        'runtime_source_sha256':digest(root/'runtime_source/dolfinx_petsc.py')})
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>F6-S1-S4 初始监测失败</title>
<style>body{{max-width:1100px;margin:32px auto;padding:0 20px;color:#173e2e;font:16px/1.7 'Microsoft YaHei',sans-serif}}img{{width:100%}}a{{color:#176b4d}}</style>
<h1>F6-S1-S4：监测接口失败，尚无受压平衡</h1>
<p>科学/工程执行failed；失败证据保全与图件passed。新增记录代码错误地对只读锁定向量请求可写访问，首次Newton更新前退出。</p>
<img src="{rendering['png']}" alt="保存的三层圆环初值、载荷及独立重算未平衡力">
<p>加载初值自由力残量0.00866704，状态逐字节未变。J=1不代表局部体积资格；不生成虚假形变或多时刻图。</p>
<p>一次16.914秒单CPU容器，0 GPU/零载复算/自动重跑。619父文件和50项无关工作区变更保持。</p>
<p>只读获取与选项生命周期补丁已写入，60测试+21子测试通过；原PETSc/DOLFINx环境复验not_run。需先接口烟测，再另行批准恢复同一首压力态。</p>
<p><a href="failure.json">原始失败堆栈</a> · <a href="post_verification.json">独立复核</a> · <a href="summary.json">状态摘要</a> · <a href="{rendering['notebook']}">可复算Notebook</a> · <a href="runtime_source/dolfinx_petsc.py">实际运行时源码</a></p>
<p>当前仍是理想二维平面应变；真实外轮廓、主动收缩、三维、FSI与生长本轮未运行。</p></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    save_json(root/'manifest.json',package_manifest(root))
    register_result(workspace,root,'failed',digest(root/'manifest.json'))
    return summary
