"""Saved-state passive-ring figures and delivery, including incomplete fine runs."""
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np


def plot_data(path, mechanics):
    """Reconstruct actual accepted states; an absent fine state is never invented."""
    data=mechanics.load_arrays(path)
    report=json.loads(str(data['verification']))
    meshes={}; cases={}
    for name in ['M0','M1']:
        prefix=name+'_mesh_'
        meshes[name]={key[len(prefix):]:value for key,value in data.items() if key.startswith(prefix)}
        mesh=meshes[name]; cases[name]=[]
        if not mesh:
            continue
        reference=mechanics.cavity(mesh,np.zeros_like(mesh['coordinates']),0.)[0]
        for index in data[name+'_indices'].astype(int):
            prefix=f'{name}_{index}_'
            state={key[len(prefix):]:value for key,value in data.items() if key.startswith(prefix)}
            actual=mechanics.fields(mesh,state,float(data['mu']),float(data['kappa']))
            stress=actual['stress']
            deviator=stress-np.trace(stress,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
            area=mechanics.cavity(mesh,state['u'],float(state['load']))[0]
            expected=report['cases'][name][f'passive_{index}']
            if expected['status']!='passed' or abs(area-expected['cavity_area'])>1e-11:
                raise ValueError('Figure requires an independently accepted, unchanged state')
            cases[name].append({'index':int(index),'load':float(state['load']),'u':state['u'],
                'equivalent':np.sqrt(1.5*np.sum(deviator**2,axis=(-1,-2))).mean(axis=1)/float(data['mu']),
                'volume':np.max(np.abs(actual['J']-1),axis=1)*100,
                'displacement':np.linalg.norm(state['u'],axis=1)[mesh['cells']].mean(axis=1),
                'area_percent':(area/reference-1)*100,'source':expected['source']})
    selected='M1' if len(cases['M1'])==5 else 'M0'
    if len(cases[selected])!=5:
        raise ValueError('This pressure-sequence layout needs five actual accepted states')
    return meshes,cases,selected,report


def draw(data_path,png_path,svg_path,style_module,mechanics,mode,axis_box_size_in,figure_size_in):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection,LineCollection
    from matplotlib.colors import Normalize
    from matplotlib.ticker import FixedLocator,NullFormatter

    meshes,cases,selected,report=plot_data(data_path,mechanics)
    mesh=meshes[selected]; frames=cases[selected]; peak=frames[-1]
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=16.,axis_label_size=18.,annotation_font_size=16.,sample_size_and_stat_font_size=14.,
        legend_font_size=14.,axes_line_width=1.5,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=key,reason='Existing compact FEM style; equal-scale maps or explicit multi-state layout, with fixed physical axis boxes.')
               for key,value in asdict(style).items() if value!=defaults[key]]
    width,height=figure_size_in; side=axis_box_size_in[0]
    figure=plt.figure(figsize=figure_size_in)
    locations=[(1.1,7.),(8.,7.),(1.1,1.4),(8.,1.4)] if mode=='qualification' else [(x,y) for y in [6.5,1.3] for x in [1.1,6.5,11.9]]
    axes=[figure.add_axes((x/width,y/height,side/width,side/height)) for x,y in locations]
    parts=np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    edges=mesh['cells'][:,[[0,5,1],[1,3,2],[2,4,0]]].reshape(-1,3)
    _,ids,counts=np.unique(np.sort(edges[:,[0,2]],axis=1),axis=0,return_inverse=True,return_counts=True)
    boundary=mesh['coordinates'][edges[counts[ids]==1]]
    parameter=np.linspace(0,1,7)
    shape=np.column_stack((2*parameter**2-3*parameter+1,4*parameter-4*parameter**2,2*parameter**2-parameter))
    reference=np.einsum('qa,eai->eqi',shape,boundary)
    def field(axis,frame,key,maximum=None):
        triangles=(mesh['coordinates']+frame['u'])[mesh['cells'][:,parts]].reshape(-1,3,2)
        maximum=float(frame[key].max()) if maximum is None else maximum
        artist=PolyCollection(triangles,array=np.repeat(frame[key],4),norm=Normalize(0,maximum),
                              cmap='magma' if key=='volume' else 'viridis',edgecolors=(0,0,0,.2),linewidths=.1)
        axis.add_collection(artist)
        axis.add_collection(LineCollection(reference,colors='#888888',linewidths=.65,linestyles='--'))
        return artist
    def spatial(axis,title):
        axis.set(xlim=(-1.25,1.25),ylim=(-1.25,1.25),xlabel='x / L',ylabel='y / L',aspect='equal')
        axis.xaxis.set_major_locator(FixedLocator([-1,0,1])); axis.yaxis.set_major_locator(FixedLocator([-1,0,1]))
        style_module.apply_axes_style(axis,style=style); style_module.add_top_information(axis,title,style=style)
    def colorbar(artist,left,bottom,label):
        cax=figure.add_axes((left/width,bottom/height,.20/width,side/height))
        figure.colorbar(artist,cax=cax).set_label(label,fontsize=14,labelpad=10)
        cax.tick_params(labelsize=14)
    if mode=='qualification':
        colors=np.array(['#4C9F70','#D6B656','#5B8DB8'])
        triangles=mesh['coordinates'][mesh['cells'][:,parts]].reshape(-1,3,2)
        axes[0].add_collection(PolyCollection(triangles,facecolors=np.repeat(colors[mesh['layers']-1],4),edgecolors=(0,0,0,.25),linewidths=.12))
        for component,marker in [(0,'s'),(1,'^')]:
            indices=np.flatnonzero(mesh['fixed'][:,component])
            axes[0].plot(*mesh['coordinates'][indices].T,linestyle='none',marker=marker,color='#BA3E34',ms=6)
        for angle in np.linspace(0,2*np.pi,12,endpoint=False):
            direction=np.array([np.cos(angle),np.sin(angle)])
            axes[0].annotate('',xy=direction*(20/27),xytext=direction*.57,arrowprops={'arrowstyle':'->','color':'#A92D28','lw':1.2})
        axes[0].text(0,0,'Pressure 0 to 0.08\nactive = 0\nouter wall free',ha='center',va='center',fontsize=14)
        spatial(axes[0],f'A  {selected} reference mesh and loading')
        artist=field(axes[1],peak,'displacement')
        axes[1].text(0,0,f"p / mu = 0.08\narea +{peak['area_percent']:.4f}%\nactual 1x deformation",ha='center',va='center',fontsize=13)
        spatial(axes[1],'B  Peak displacement magnitude / L')
        colorbar(artist,12.05,7.,'Element mean |u| / L')
        pressure=np.array([frame['load'] for frame in frames])
        analytic=np.array([mechanics.analytic_c(p)/(20/27)**2*100 for p in pressure])
        axes[2].plot(pressure,analytic,'-',color='#222222',label='Incompressible reference',linewidth=1.5)
        for name,marker,color in [('M0','o','#216C91'),('M1','s','#AE594A')]:
            if cases[name]:
                axes[2].plot([f['load'] for f in cases[name]],[f['area_percent'] for f in cases[name]],linestyle='none',marker=marker,
                             markerfacecolor='none',color=color,label=f'{name} DG2',markersize=7)
                positive=[f for f in cases[name] if f['load']>0]
                axes[3].plot([f['load'] for f in positive],[f['volume'].max() for f in positive],marker+'-',color=color,label=f'{name} DG2',markersize=7)
        axes[2].set(xlim=(-.003,.083),ylim=(-1,25),xlabel='p / mu',ylabel='Cavity area change (%)')
        axes[2].xaxis.set_major_locator(FixedLocator([0,.02,.04,.06,.08]))
        axes[2].yaxis.set_major_locator(FixedLocator([0,5,10,15,20,25]))
        axes[2].legend(loc='upper left')
        axes[3].axhline(1.,color='#B44035',linestyle='--',linewidth=1.5)
        axes[3].text(.047,1.14,'Original 1% gate',color='#B44035',fontsize=13)
        axes[3].set(xlim=(.015,.085),ylim=(.001,2.),yscale='log',xlabel='p / mu',ylabel='max |J - 1| (%)')
        axes[3].xaxis.set_major_locator(FixedLocator([.02,.04,.06,.08]))
        axes[3].yaxis.set_major_locator(FixedLocator([.001,.01,.1,1.]))
        for index,title in [(2,'C  Accepted pressure response'),(3,'D  Local volume gate (positive loads)')]:
            style_module.apply_axes_style(axes[index],style=style)
            style_module.add_top_information(axes[index],title,style=style)
        axes[3].yaxis.set_minor_locator(FixedLocator([.002,.005,.02,.05,.2,.5]))
        axes[3].yaxis.set_minor_formatter(NullFormatter())
        outcome='two-mesh qualification PASSED' if report['status']=='passed' else 'M0 sequence PASSED; M1 incomplete after native signal 11'
        figure.text(.08,.963,f'Passive ring: {outcome}',fontsize=14)
        figure.text(.08,.515,'Five real accepted M0 pressure states; no active contraction or physiological time.',fontsize=14)
        figure.text(.08,.035,'Green / yellow / blue: assumed endo / ECM / myo (same passive law). Displacement magnitude is not strain.',fontsize=12)
    elif mode=='pressure_states':
        maximum=max(float(frame['equivalent'].max()) for frame in frames)
        for index,frame in enumerate(frames):
            artist=field(axes[index],frame,'equivalent',maximum)
            spatial(axes[index],f"{chr(65+index)}  p / mu = {frame['load']:.2f}")
            origin='retained' if frame['source']=='retained_without_solve' else 'new equilibrium'
            axes[index].text(0,0,f"area +{frame['area_percent']:.3f}%\n{origin}",ha='center',va='center',fontsize=13)
        colorbar(artist,15.55,6.5,'Mean equivalent stress / mu')
        volume_map=field(axes[5],peak,'volume')
        spatial(axes[5],'F  Peak local volume change')
        axes[5].text(0,0,f"max |J - 1|\n{peak['volume'].max():.5f}%\ngate: 1%",ha='center',va='center',fontsize=13)
        colorbar(volume_map,15.55,1.3,'Element max |J - 1| (%)')
        figure.text(.062,.965,f'{selected}: five accepted pressure states | same stress scale and actual 1x deformation',fontsize=14)
        figure.text(.062,.493,'Pressure continuation is NOT heartbeat time. Gray outlines: reference mesh. No interpolated frames.',fontsize=14)
        figure.text(.062,.035,'M0 zero / 0.02 reused; 0.04 / 0.06 / 0.08 newly accepted. Fine-mesh qualification remains incomplete.',fontsize=13)
    else:
        raise ValueError('Unknown passive figure mode')
    exported=style_module.export_figure(figure,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    if Path(exported.svg)!=Path(svg_path):
        Path(exported.svg).replace(svg_path)
        manifest=json.loads(Path(exported.manifest).read_text())
        manifest['exports']['svg']=str(Path(svg_path).resolve())
        Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.close(figure)
    return {'selected_mesh':selected,'accepted_states_shown':len(frames),'new_equilibrium_solves':0,
            'stage_status':report['status'],'peak_area_percent':peak['area_percent'],
            'peak_volume_percent':float(peak['volume'].max())}


def prepare(workspace,skill_root):
    import re
    import subprocess
    import sys
    import nbformat
    from prl.runs.fenicsx_pressure import PASSIVE_RESULT
    from prl.runs.fenicsx_ring import digest
    from prl.runs.fenicsx_runtime import save_json
    from prl.result_store import result_path,result_admission
    from prl.verification.fenicsx_pressure import verify_pressure
    from prl.verification import fenicsx_ring as mechanics
    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,PASSIVE_RESULT); skills=Path(skill_root)
    if (root/'post_verification.json').exists() or (root/'figures').exists():
        raise FileExistsError('Passive delivery preparation is create-only')
    if not result_admission(workspace,128*1024**2)['can_start']:
        raise RuntimeError('Postprocessing storage admission refused')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    if not all(digest(root/item['path'])==item['sha256'] for item in formal['files']):
        raise ValueError('Original scientific invocation changed')
    report=verify_pressure(root); save_json(root/'post_verification.json',report)
    config=json.loads((root/'configuration.json').read_text())
    data={'verification':np.array(json.dumps(report)),'mu':np.array(config['mu']),'kappa':np.array(config['kappa'])}
    for name in ['M0','M1']:
        mesh_path=root/'ring/raw'/f'{name}_mesh.npz'
        if mesh_path.exists():
            data.update({f'{name}_mesh_{key}':value for key,value in mechanics.load_arrays(mesh_path).items()})
        indices=[]
        for label,record in report['cases'][name].items():
            if record['status']!='passed':
                continue
            index=int(label.split('_')[1]); indices.append(index)
            parent='ring/raw' if record['source']=='new' else 'retained_passive'
            state=mechanics.load_arrays(root/parent/f'{name}_state_{label}.npz')
            data.update({f'{name}_{index}_{key}':state[key] for key in ['u','pressure','load','activation']})
        data[name+'_indices']=np.array(sorted(indices),dtype=int)
    np.savez_compressed(root/'figure_data.npz',**data)
    revisions=[]
    for mode in ['qualification','pressure_states']:
        subprocess.run([sys.executable,'-B','-X','utf8',str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
            str(root/'figures'),'--main','S1S5','--analysis-key',mode,'--data',str(root/'figure_data.npz'),
            '--python','helper='+str(Path(__file__).resolve()),
            '--python','mechanics='+str(workspace/'src/prl/verification/fenicsx_ring.py'),
            '--python','style='+str(skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'),
            '--model','config='+str(root/'configuration.json'),'--model','verification='+str(root/'post_verification.json')],check=True)
        revision=next((root/f'figures/FigS1S5_{mode}').glob('FigS1S5_*')); prefix=revision.name
        snapshots={key:next(revision.glob(f'*_{key}.py')).name for key in ['helper','mechanics','style']}
        side,canvas=(3.7,(13.8,12.)) if mode=='qualification' else (3.2,(17.8,11.3))
        notebook=nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_markdown_cell('# 圆环被动压力：实有接受态与未完成边界\n粗网格5态真实保存，其中2态复用、3态本轮新增；细网格原生段错误退出，未接受零载态。\n所有场量从u/p独立重算，1倍形变；压力延拓不是生理时间。'),
            nbformat.v4.new_code_cell(f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 作图调整参数：沿用紧凑FEM风格，六面板仅改变有记录的轴框尺寸；实际1倍形变。
STYLE_SOURCE = 'Existing compact FEM diagnostics with CB style'
DPI = 600
axis_box_size_in = ({side}, {side})
FIGURE_SIZE_IN = {canvas!r}
def load_snapshot(name,filename):
    spec=importlib.util.spec_from_file_location(name,REVISION_DIR/filename)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module
helper=load_snapshot('passive_plot_snapshot',{snapshots['helper']!r})
mechanics=load_snapshot('independent_mechanics_snapshot',{snapshots['mechanics']!r})
style=load_snapshot('cb_style_snapshot',{snapshots['style']!r})
helper.draw(DATA_PATH,OUTPUT_PNG,OUTPUT_SVG,style,mechanics,{mode!r},axis_box_size_in,FIGURE_SIZE_IN)'''),
            nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG),width=1100))')],
            metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
        nbformat.write(notebook,revision/f'03_{prefix}_plot.ipynb')
        methods=revision/f'02_{prefix}_methods.txt'; content=methods.read_text(encoding='utf-8')
        values={
            '风格来源':f'既有紧凑FEM诊断风格，CB显式override；主轴{side}英寸方框，600dpi PNG及可编辑SVG。',
            '用户提供的期刊规格':'未指定；内部数值资格图，不是排版后的投稿成图。',
            '03_材料方法来源':'稳定方法src/prl/verification/fenicsx_ring.py的物理快照mechanics，版本内helper/style，配置和独立核验同包保存；不依赖工作区重算、不调用FEM。',
            '数据/模型变换':'输入包含原始网格及全部已接受u/p；独立重算F/J/Cauchy应力。位移为单元六节点模长均值，应力为积分点von Mises均值，J为单元积分点最大绝对偏差百分数；六节点三角形拆四个显示子三角，不平滑。验收仍用全部积分点，不以展示均值替代。面积由二次内边界积分重算。解析参照使用原不可压NH公式，不是有限bulk精确解。',
            '统计方法与不确定性':'确定性压力加载，无生物样本/误差棒。仅粗网格完成；细网格未接受零载态，不能声称粗细通过或热点收敛。零载J=0偏差未放在对数图，原始状态保留。5个实际压力状态不是生理时间，2态复用/3态新增均明示。',
            '生物学分组颜色':'不适用。绿/黄/蓝为假设心内膜/ECM/心肌材料域，当前被动参数相同；蓝色曲线/空心圈为M0数值结果，黑线为解析参照。'}
        for key,value in values.items():
            content=re.sub(r'(?m)^- '+re.escape(key)+r':.*$',lambda match:'- '+key+': '+value,content)
        methods.write_text(content,encoding='utf-8'); revisions.append(str(revision))
    return {'status':'passed','scientific_status':report['status'],'revisions':revisions,'new_equilibrium_solves':0}


def finalize(workspace):
    """Freeze partial successes and the native failure without relabeling the stage."""
    import shutil
    from prl.result_store import result_path,register_result,result_admission
    from prl.runs.fenicsx_pressure import PASSIVE_RESULT
    from prl.runs.fenicsx_ring import digest,package_manifest
    from prl.runs.fenicsx_runtime import save_json
    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,PASSIVE_RESULT)
    if (root/'manifest.json').exists() or (root/'summary.json').exists():
        raise FileExistsError('Passive result package is already frozen')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    internal=json.loads((root/'protected_preflight.json').read_text())
    external=json.loads((root/'external_protected_preflight.json').read_text())
    dirty=json.loads((root/'preexisting_changes.json').read_text())
    if not (all(digest(root/item['path'])==item['sha256'] for item in formal['files']) and
            all(digest(workspace/path)==sha for path,sha in internal.items()) and
            all(digest(path)==sha for path,sha in external.items()) and
            all(digest(workspace/item['path'])==item['sha256'] for item in dirty)):
        raise ValueError('Protected source, invocation or unrelated edit drift')
    report=json.loads((root/'post_verification.json').read_text())
    runtime=json.loads((root/'execution.json').read_text())
    figures={}
    for mode in ['qualification','pressure_states']:
        revision=next((root/f'figures/FigS1S5_{mode}').glob('FigS1S5_*')); prefix=revision.name
        if '- 包状态: 最终包' not in (revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8'):
            raise ValueError('Final Notebook/style/visual QA required')
        figures[mode]={kind:(revision/f'{number}_{prefix}{suffix}').relative_to(root).as_posix()
                       for kind,number,suffix in [('notebook','03','_plot.ipynb'),('png','04','.png'),('svg','05','.svg')]}
    coarse='passed' if len(report['cases']['M0'])==5 and all(s['status']=='passed' for s in report['cases']['M0'].values()) else 'failed'
    summary={'status':report['status'],'engineering_execution':runtime['status'],'evidence_delivery':'passed',
             'coarse_pressure_sequence':coarse,'fine_execution':'failed','mesh_comparison':'not_run',
             'new_accepted_equilibria':report['new_accepted_equilibria'],'retained_equilibria':report['reused_equilibria'],
             'attempted_equilibria':report['attempted_equilibria'],'coarse_peak':report['cases']['M0'].get('passive_4'),
             'failure':'PETSc native signal 11 at M1 zero load; exact native call site unknown',
             'repair_implemented':False,'original_environment_replay':'not_run','automatic_retries':0,'gpu':0,
             'contour':'not_run','active_contraction':'not_run','three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run','biological_validation':'not_run',
             'next_action':'Pending approval: isolate and repair zero-Newton diagnostics in a real runtime microprobe, then only the five fine-mesh states; do not repeat accepted coarse states.'}
    rendering={'status':'passed','visual_qa':'passed','style_validation':'passed','figures':figures,
               'actual_accepted_pressure_states':5,'retained_states':2,'new_states':3,'fine_accepted_states':0,
               'source':'saved u/p independently reconstructed with NumPy; no interpolated or synthetic result frames',
               'new_FEM_solves':0,'deformation_scale':1,'physiological_time':'not_calibrated',
               'temporary_cleanup':'not_authorized; registered figure_runtime retained'}
    audit={'status':'passed','stage_execution':runtime['status'],'coarse_sequence':coarse,
           'formal_invocation_files_unchanged':len(formal['files']),'protected_parent_files_unchanged':len(internal)+len(external),
           'preexisting_dirty_files_unchanged':len(dirty),'before_run_tests':67,'after_postprocess_tests':68,'subtests':21,
           'postprocessing_new_FEM_solves':0,'native_failure_reruns':0,'native_call_site_confirmed':False,
           'notebook_execution':'passed','style_validation':'passed','visual_qa':'passed'}
    for filename,value in [('summary.json',summary),('rendering.json',rendering),('delivery_audit.json',audit),
                           ('delivery_storage.json',result_admission(workspace))]:
        save_json(root/filename,value)
    sources=sorted(set(list(json.loads((root/'source_hashes.json').read_text()))+[
        'src/prl/cli.py','src/prl/rendering/fenicsx_passive_ring.py','tests/prl/test_fenicsx_pressure.py',
        'project_control/ventricle_fem_ring_passive_qualification_execution_v01.md']))
    for relative in sources:
        target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(workspace/relative,target)
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>F6-S1-S5 粗网格压力序列通过，细网格停止</title>
<style>body{{max-width:1200px;margin:32px auto;padding:0 20px;color:#173e2e;font:16px/1.7 'Microsoft YaHei',sans-serif}}img{{width:100%}}a{{color:#176b4d}}</style>
<h1>粗网格完整压力序列通过；细网格零载原生退出</h1>
<p>阶段执行failed；M0压力序列passed；粗细比较not_run；证据与图件passed。新增3个接受态，复用2态，非零压力0.02/0.04/0.06/0.08。</p>
<p>最高压力p/mu=0.08：腔室面积+22.4593%，局部壁体积变化最大0.0134833%，低于原1%门。相对不可压解析响应误差最大0.0684168%，低于原M0的2%门。</p>
<img src="{figures['qualification']['png']}" alt="真实模型、1倍位移、压力面积响应及局部J门">
<h2>5个真实压力状态</h2><p>0/0.02为复用，0.04/0.06/0.08为本轮新增。统一应力色标，1倍实际形变；压力延拓不是心动时刻。</p>
<img src="{figures['pressure_states']['png']}" alt="5个真实接受压力态的等效应力和峰值局部J">
<h2>细网格停止的证据边界</h2><p>M1几何和切线检查通过；零载monitor-0残量2.175e-16后出现PETSc SIGSEGV 11，容器退出15、OOMKilled=false。未保存最终SNES原因和完整末态，不能计作接受平衡。</p>
<p>优先排查零次Newton时仍读取因子诊断的路径，但没有原生调用栈，崩溃位置尚未确认。没有第二个容器、自动重跑或Ring修复。下一步需先微型接口定位与修复，再只恢复细网格5态。</p>
<p>一次23.705秒单CPU容器，0GPU；826父文件、98正式调用文件及50项无关修改保持。68测试+21子测试通过不代表原生零次更新路径已验证。</p>
<p><a href="post_verification.json">独立验证</a> · <a href="failure_diagnosis.json">故障事实与假设</a> · <a href="stderr.log">原始stderr</a> · <a href="failed_initial_audit.json">保存初猜复核</a> · <a href="{figures['qualification']['notebook']}">资格图Notebook</a> · <a href="{figures['pressure_states']['notebook']}">压力态Notebook</a></p>
<p>当前是未标定二维理想圆环，三层同被动材料、主动关闭；原轮廓/三维/FSI/生长未运行，也不构成生物学验证。</p></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    save_json(root/'manifest.json',package_manifest(root))
    register_result(workspace,root,summary['status'],digest(root/'manifest.json'))
    return summary
