"""Portable contour figures from copied raw u/p; no solver or invented frames."""
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np


def plot_data(path, mechanics):
    data = mechanics.load_arrays(path); report = json.loads(str(data['verification']))
    meshes, cases, controls = {}, {}, {}
    for name in ['M0','M1']:
        prefix = name+'_mesh_'
        mesh = meshes[name] = {k[len(prefix):]:v for k,v in data.items() if k.startswith(prefix)}
        cases[name] = []
        for index in data[name+'_indices'].astype(int):
            prefix = f'{name}_{index}_'
            state = {k[len(prefix):]:v for k,v in data.items() if k.startswith(prefix)}
            values = mechanics.fields(mesh,state,float(data['mu']),float(data['kappa']))
            area = mechanics.cavity(mesh,state['u'],float(state['load']))[0]
            record = report['cases'][name][f'passive_{index}']
            if abs(area-record['cavity_area']) > 1e-10 or abs(np.max(np.abs(values['J']-1))-record['max_abs_J_minus_one']) > 1e-10:
                raise ValueError('Plotted raw fields disagree with independent accepted/failure report')
            stress = values['stress']
            deviator = stress-np.trace(stress,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
            cases[name].append({'index':int(index),'u':state['u'],'load':float(state['load']),'status':record['status'],
                'stress':np.sqrt(1.5*np.sum(deviator**2,axis=(-1,-2))).mean(axis=1)/float(data['mu']),
                'volume':np.max(np.abs(values['J']-1),axis=1)*100,'area_percent':record['cavity_area_change']*100})
        prefix = name+'_CG1_mesh_'
        oldmesh = {k[len(prefix):]:v for k,v in data.items() if k.startswith(prefix)}
        prefix = name+'_CG1_state_'
        oldstate = {k[len(prefix):]:v for k,v in data.items() if k.startswith(prefix)}
        values = mechanics.fields(oldmesh,oldstate,float(data['mu']),float(data['kappa']))
        controls[name] = float(np.max(np.abs(values['J']-1))*100)
        expected = report['retained_failed_CG1'][name]['audit']['max_abs_J_minus_one']*100
        if abs(controls[name]-expected) > 1e-8:
            raise ValueError('CG1 comparison must reproduce the preserved failed state')
    return data, meshes, cases, controls, report


def draw(data_path,png_path,svg_path,style_module,mechanics,mode,axis_box_size_in=(3.6,3.6),figure_size_in=(14.4,13.6)):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    from matplotlib.ticker import FixedLocator, MaxNLocator, NullFormatter

    data,meshes,cases,controls,report = plot_data(data_path,mechanics)
    frames = [(name,frame) for name in ['M0','M1'] for frame in cases[name]]
    if not frames:
        raise ValueError('No completed saved FEM states; do not fabricate result fields')
    selected = 'M1' if len(cases['M1']) == 2 else 'M0'
    peak = cases[selected][-1]; mesh = meshes[selected]
    style = style_module.StyleSpec(axis_box_size_in=axis_box_size_in,tick_label_size=16.,axis_label_size=18.,
        annotation_font_size=16.,sample_size_and_stat_font_size=14.,legend_font_size=14.,axes_line_width=1.5,
        major_tick_length_pt=5.,major_tick_width_pt=1.,minor_tick_length_pt=3.,minor_tick_width_pt=.8,
        data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    defaults = asdict(style_module.DEFAULT_STYLE)
    overrides = [style_module.StyleOverride(field=k,reason='Reuse compact FEM four-panel style, equal spatial scales and fixed panel sizes.')
        for k,v in asdict(style).items() if v != defaults[k]]
    width,height = figure_size_in; side = axis_box_size_in[0]
    figure = plt.figure(figsize=figure_size_in)
    positions = [(1.3,8.),(8.1,8.),(1.3,2.8),(8.1,2.8)]
    axes = [figure.add_axes((x/width,y/height,side/width,side/height)) for x,y in positions]
    parts = np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    nodes = np.concatenate([meshes[name]['coordinates']+frame['u'] for name,frame in frames])
    center = (nodes.min(axis=0)+nodes.max(axis=0))/2; half = float(np.ptp(nodes,axis=0).max()*.57)
    def ticks(axis,limits):
        values = MaxNLocator(nbins=4).tick_values(*limits)
        axis.set_major_locator(FixedLocator(values[(values>=limits[0])&(values<=limits[1])]))
    def spatial(axis,title):
        axis.set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),xlabel='x / L',ylabel='y / L',aspect='equal')
        ticks(axis.xaxis,axis.get_xlim()); ticks(axis.yaxis,axis.get_ylim())
        style_module.apply_axes_style(axis,style=style); style_module.add_top_information(axis,title,style=style)
    def field(axis,name,frame,key,maximum):
        current = meshes[name]
        polygons = (current['coordinates']+frame['u'])[current['cells'][:,parts]].reshape(-1,3,2)
        artist = PolyCollection(polygons,array=np.repeat(frame[key],4),norm=Normalize(0,maximum),
            cmap='magma' if key=='volume' else 'viridis',edgecolors=(0,0,0,.22),linewidths=.065)
        axis.add_collection(artist)
        for loop in ['inner_nodes','outer_nodes']:
            curve = data['geometry_xy'][data['geometry_'+loop]]
            curve = np.vstack((curve,curve[0])); axis.plot(*curve.T,ls='--',color='#888888',lw=.8)
        return artist
    def colorbar(artist,x,y,label):
        cax = figure.add_axes((x/width,y/height,.22/width,side/height))
        figure.colorbar(artist,cax=cax).set_label(label,labelpad=10,fontsize=18)
        cax.tick_params(labelsize=16,direction='out'); ticks(cax.yaxis,(artist.norm.vmin,artist.norm.vmax))
    stress_max = max(float(frame['stress'].max()) for _,frame in frames)
    if mode == 'qualification':
        palette = np.array(['#4C9F70','#D6B656','#5B8DB8'])
        polygons = mesh['coordinates'][mesh['cells'][:,parts]].reshape(-1,3,2)
        axes[0].add_collection(PolyCollection(polygons,facecolors=np.repeat(palette[mesh['layers']-1],4),edgecolors=(0,0,0,.28),linewidths=.065))
        for point,label,marker in zip(data['geometry_anchors'],['A','B'],['s','^']):
            axes[0].plot(*point,marker=marker,color='#B3463E',ms=7)
            axes[0].annotate(label,point,xytext=(5,8),textcoords='offset points')
        inner = data['geometry_xy'][data['geometry_inner_nodes']]
        for index in np.linspace(0,len(inner)-1,10,dtype=int):
            a,b = inner[[index,(index+1)%len(inner)]]; direction=b-a
            normal = np.array([direction[1],-direction[0]])/np.linalg.norm(direction)
            point = (a+b)/2
            axes[0].annotate('',xy=point+.09*normal,xytext=point-.14*normal,
                arrowprops={'arrowstyle':'->','color':'#B3463E','lw':1.2})
        spatial(axes[0],f'A  {selected} reference; constructed layers')
        artist = field(axes[1],selected,peak,'stress',stress_max)
        spatial(axes[1],f'B  {selected} p / mu = {peak["load"]:.2f}; 1x deformation')
        colorbar(artist,12.05,8.,'Mean equivalent stress / mu')
        artist = field(axes[2],selected,peak,'volume',max(float(peak['volume'].max()),1e-12))
        spatial(axes[2],f'C  {selected} local volume deviation')
        colorbar(artist,5.25,2.8,'Element max |J - 1| (%)')
        x = np.array([0,1]); old = [controls[name] for name in ['M0','M1']]
        axes[3].plot(x,old,'x--',color='#AD4A40',ms=10,mew=2,label='CG1: retained failed')
        actual_x=[]; actual=[]
        for index,name in enumerate(['M0','M1']):
            if len(cases[name])==2:
                actual_x.append(index); actual.append(float(cases[name][1]['volume'].max()))
        axes[3].plot(actual_x,actual,'o-',color='#20694D',ms=8,label='DG2: current result')
        axes[3].axhline(1.,color='#777777',ls=':',lw=1.5)
        axes[3].text(.05,1.14,'Original 1% gate',fontsize=14)
        axes[3].set(xlim=(-.18,1.18),ylim=(.1,25),yscale='log',xlabel='Same displacement mesh',ylabel='max |J - 1| (%)')
        axes[3].set_xticks([0,1],['M0','M1']); axes[3].yaxis.set_major_locator(FixedLocator([.1,1.,10.]))
        axes[3].legend(loc='upper left',frameon=False)
        style_module.apply_axes_style(axes[3],style=style)
        style_module.add_top_information(axes[3],'D  Local volume: old vs current',style=style)
        axes[3].yaxis.set_minor_locator(FixedLocator([.2,.5,2.,5.,20.])); axes[3].yaxis.set_minor_formatter(NullFormatter())
        figure.text(.065,.957,f'Contour at first pressure: {report["status"].upper()} | fixed 1% local volume gate',fontsize=16)
        figure.text(.065,.925,f'{selected}: cavity area {peak["area_percent"]:+.5f}%; max |J - 1| = {peak["volume"].max():.5f}%. No active contraction.',fontsize=14)
    elif mode == 'pressure_states':
        for axis,(name,frame) in zip(axes,frames):
            artist = field(axis,name,frame,'stress',stress_max)
            spatial(axis,f'{name} p / mu = {frame["load"]:.2f}; {frame["status"].upper()}')
        for axis in axes[len(frames):]:
            axis.text(.5,.5,'NOT RUN',transform=axis.transAxes,ha='center'); axis.set_axis_off()
        colorbar(artist,12.05,8.,'Mean equivalent stress / mu')
        colorbar(artist,12.05,2.8,'Same stress scale')
        figure.text(.065,.957,f'{len(frames)} saved states: two meshes, zero and first pressure | actual 1x deformation',fontsize=16)
        figure.text(.065,.925,'One common stress scale; gray dashed outlines are the reference boundaries.',fontsize=14)
    else:
        raise ValueError('Unknown contour figure layout')
    layer_note = ('Green / yellow / blue: assumed endo / ECM / myo. Same passive material; A: ux=uy=0, B: uy=0.'
        if mode == 'qualification' else 'All panels show equivalent stress, not layer labels. Three constructed layers share the same passive material.')
    figure.text(.065,.136,layer_note,fontsize=12)
    figure.text(.065,.103,'Follower pressure inside, outer wall free. Only the outer contour is image-derived; material is uncalibrated.',fontsize=12)
    figure.text(.065,.070,'Pressure continuation is NOT heartbeat time. Two mesh levels do not prove hotspot or asymptotic convergence.',fontsize=12)
    figure.text(.065,.037,'Fields are independently reconstructed from saved u/p. No 3D, active contraction, FSI, growth or biological validation.',fontsize=12)
    exported = style_module.export_figure(figure,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    Path(exported.svg).replace(svg_path)
    manifest = json.loads(Path(exported.manifest).read_text()); manifest['exports']['svg']=str(Path(svg_path).resolve())
    Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.close(figure)
    return {'status':'passed','scientific_gate':report['status'],'actual_states':len(frames),'new_FEM_solves':0,'deformation_scale':1}


def prepare(workspace,skill_root):
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path,result_admission
    from prl.runs.fenicsx_contour_pressure import RESULT
    from prl.runs.fenicsx_ring import digest
    from prl.runs.fenicsx_runtime import save_json
    from prl.verification.fenicsx_contour_pressure import verify_contour_pressure
    from prl.verification.fenicsx_ring import load_arrays

    workspace=Path(workspace).resolve(strict=True); skills=Path(skill_root); root=result_path(workspace,RESULT)
    if (root/'post_verification.json').exists() or (root/'figures').exists():
        raise FileExistsError('Contour figure preparation is create-only')
    if not result_admission(workspace,128*1024**2)['can_start']:
        raise RuntimeError('Postprocessing storage admission refused')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    if not all(digest(root/item['path'])==item['sha256'] for item in formal['files']):
        raise ValueError('Formal invocation changed')
    report=verify_contour_pressure(root); save_json(root/'post_verification.json',report)
    config=json.loads((root/'configuration.json').read_text())
    data={'verification':np.array(json.dumps(report)),'mu':np.array(config['mu']),'kappa':np.array(config['kappa'])}
    data.update({'geometry_'+key:value for key,value in load_arrays(root/'input/M0_input_mesh.npz').items()})
    for name in ['M0','M1']:
        meshpath=root/'raw'/f'{name}_mesh.npz'
        if meshpath.exists():
            data.update({name+'_mesh_'+k:v for k,v in load_arrays(meshpath).items()})
        indices=[]
        for index in [0,1]:
            path=root/'raw'/f'{name}_state_passive_{index}.npz'
            if path.exists():
                indices.append(index)
                state=load_arrays(path)
                data.update({f'{name}_{index}_{k}':state[k] for k in ['u','pressure','load','activation']})
        data[name+'_indices']=np.array(indices,dtype=int)
        data.update({name+'_CG1_mesh_'+k:v for k,v in load_arrays(root/'comparison'/name/'mesh.npz').items()})
        old=load_arrays(root/'comparison'/name/'state.npz')
        data.update({name+'_CG1_state_'+k:old[k] for k in ['u','pressure','load','activation']})
    np.savez_compressed(root/'figure_data.npz',**data)
    revisions=[]
    for mode in ['qualification','pressure_states']:
        subprocess.run([sys.executable,'-B','-X','utf8',str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
            str(root/'figures'),'--main','S1S7','--analysis-key',mode,'--data',str(root/'figure_data.npz'),
            '--python','helper='+str(Path(__file__).resolve()),'--python','mechanics='+str(workspace/'src/prl/verification/fenicsx_ring.py'),
            '--python','style='+str(skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'),
            '--model','config='+str(root/'configuration.json'),'--model','verification='+str(root/'post_verification.json')],check=True)
        revision=next((root/f'figures/FigS1S7_{mode}').glob('FigS1S7_*')); prefix=revision.name
        snapshots={key:next(revision.glob(f'*_{key}.py')).name for key in ['helper','mechanics','style']}
        notebook=nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_markdown_cell('# 原图像外轮廓：两网格零载与首压力\n内腔和层界为构造，材料未标定。所有场量由保存u/p独立复算；实际1倍形变，不是心动时间。'),
            nbformat.v4.new_code_cell(f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 作图调整参数：沿用已确认紧凑FEM四面板风格；轴框、字号及所有例外写入样式manifest。
STYLE_SOURCE = 'Existing compact FEM diagnostics with CB explicit overrides'
DPI = 600
axis_box_size_in = (3.6, 3.6)
FIGURE_SIZE_IN = (14.4, 13.6)
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
helper = load_snapshot('contour_plot_snapshot', {snapshots['helper']!r})
mechanics = load_snapshot('independent_mechanics_snapshot', {snapshots['mechanics']!r})
style = load_snapshot('cb_style_snapshot', {snapshots['style']!r})
helper.draw(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, style, mechanics, {mode!r}, axis_box_size_in, FIGURE_SIZE_IN)'''),
            nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=1100))')],
            metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
        nbformat.write(notebook,revision/f'03_{prefix}_plot.ipynb')
        methods=revision/f'02_{prefix}_methods.txt'; content=methods.read_text(encoding='utf-8')
        values={'风格来源':'既有紧凑FEM风格，CB显式override；主轴3.6英寸方框，600dpi PNG与可编辑SVG。',
            '用户提供的期刊规格':'未指定；内部数值资格图，非投稿排版图。',
            '03_材料方法来源':'本项目使用src/prl/verification/fenicsx_ring.py稳定独立力学模块，复制mechanics/helper/style、配置及核验至本版本；原始网格/u/p物理复制至01数据。无需工作区或FEM求解器即可重画。',
            '数据/模型变换':'由u/p独立重算F/J/Cauchy应力；等效应力为每单元积分点von Mises均值，J图为每单元积分点最大绝对偏差百分数。六节点三角拆四个显示三角，实际1倍形变，不平滑。CG1峰值也从保留u/p重算，不改写其failed。验收基于全部原始积分点而非显示均值。',
            '统计方法与不确定性':'确定性两网格各零载/首压力，没有生物样本、误差棒或假设检验。按实存状态展示，不插值为时间帧；通过首压力不等于完整被动资格、多级渐近或热点收敛。',
            '生物学分组颜色':'不适用。绿/黄/蓝表示构造心内膜/ECM/心肌几何域，当前相同被动参数，不是实验生物学分组。'}
        for key,value in values.items():
            content=re.sub(r'(?m)^- '+re.escape(key)+r':.*$',lambda match:'- '+key+': '+value,content)
        methods.write_text(content,encoding='utf-8'); revisions.append(str(revision))
    return {'status':'passed','scientific_status':report['status'],'revisions':revisions,'new_FEM_solves':0}


def audit_agreement(actual,expected):
    """Compare platform reports; mechanical acceptance remains a separate gate."""
    differences=[]
    def compare(a,b,path='',parent_a=None,parent_b=None):
        if isinstance(b,dict):
            if not isinstance(a,dict) or set(a)!=set(b):
                return False
            return all([compare(a[key],value,path+'/'+key,a,b) for key,value in b.items()])
        if isinstance(b,list):
            return isinstance(a,list) and len(a)==len(b) and all([compare(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))])
        if isinstance(b,float):
            if np.isclose(a,b,rtol=1e-10,atol=1e-12):
                return True
            allowance=0.
            if path.startswith('/cases/') and path.endswith('/pressure_area_difference_work'):
                # The independent audit evaluates p*(A_plus-A_minus)/(2h), h=1e-5.
                # Only this reported finite-difference diagnostic gets a cancellation
                # allowance, scaled by machine precision, pressure, area and h.
                # The original 2e-6 virtual-work test and every categorical gate stay exact.
                pressure=max(abs(parent_a['pressure']),abs(parent_b['pressure']))
                area=max(1.,abs(parent_a['cavity_area']),abs(parent_b['cavity_area']))
                allowance=16*np.finfo(float).eps*pressure*area/1e-5
            accepted=bool(np.isfinite(a) and np.isfinite(b) and abs(a-b)<=allowance)
            differences.append({'path':path,'host':a,'container':b,'absolute_difference':abs(a-b),
                'finite_difference_roundoff_allowance':allowance,'accepted':accepted})
            return accepted
        return a==b
    matched=compare(actual,expected)
    return {'status':'passed' if matched else 'failed','base_rtol':1e-10,'base_atol':1e-12,
        'finite_difference_step':1e-5,'differences_beyond_base_comparison':differences,
        'physical_gates_changed':False,'categorical_checks_must_match_exactly':True}


def finalize(workspace):
    """Seal tested/visually accepted evidence; never run another equilibrium."""
    import shutil
    from prl.result_store import result_path,result_admission,register_result
    from prl.runs.fenicsx_contour_pressure import RESULT,SOURCES,protected_unchanged
    from prl.runs.fenicsx_ring import digest,package_manifest
    from prl.runs.fenicsx_runtime import save_json

    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,RESULT)
    if (root/'manifest.json').exists() or (root/'summary.json').exists():
        raise FileExistsError('Delivery already frozen')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    internal=json.loads((root/'protected_preflight.json').read_text())
    external=json.loads((root/'external_protected_preflight.json').read_text())
    dirty=json.loads((root/'preexisting_changes.json').read_text())
    identities=json.loads((root/'input_identities.json').read_text())
    if (not protected_unchanged(workspace,internal,external,dirty)
        or not all(digest(root/item['path'])==item['sha256'] for item in formal['files'])
        or not all(digest(root/path)==item['sha256'] for path,item in identities.items())
        or not all(digest(workspace/path)==sha for path,sha in json.loads((root/'source_hashes.json').read_text()).items())):
        raise ValueError('Protected evidence or formal science source drift')
    report=json.loads((root/'post_verification.json').read_text())
    runtime=json.loads((root/'execution.json').read_text())
    native=json.loads((root/'verification.json').read_text())
    agreement=audit_agreement(report,native)
    if agreement['status']!='passed':
        raise ValueError('Host and native independent audit disagree')
    boundary=json.loads((root/'boundary_screen.json').read_text())
    tests=json.loads((root/'tests_after_rendering.json').read_text())
    if tests['status']!='passed' or boundary['status']!='passed':
        raise ValueError('Tests or supplementary geometric screen needs attention')
    figures={}
    for mode in ['qualification','pressure_states']:
        revision=next((root/f'figures/FigS1S7_{mode}').glob('FigS1S7_*')); prefix=revision.name
        methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
        style=json.loads((revision/f'04_{prefix}_style_manifest.json').read_text())
        if '- 包状态: 最终包' not in methods or '人工/代理视觉验收: 通过' not in methods or not style['validation']['passed']:
            raise ValueError('Executed/final Notebook, style validation and visual QA required')
        if digest(revision/f'01_{prefix}_data.npz')!=digest(root/'figure_data.npz'):
            raise ValueError('Figure source copy mismatch')
        figures[mode]={kind:(revision/f'{number}_{prefix}{suffix}').relative_to(root).as_posix()
            for kind,number,suffix in [('notebook','03','_plot.ipynb'),('png','04','.png'),('svg','05','.svg')]}
    admission=result_admission(workspace,4*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Final storage admission refused')
    peak={name:report['cases'][name]['passive_1'] for name in ['M0','M1']}
    summary={'status':report['status'],'engineering_execution':runtime['status'],'evidence_delivery':'passed',
        'slice':'original outer contour, constructed cavity/layers; two meshes zero and first pressure only',
        'accepted_equilibria':report['accepted_equilibria'],'attempted_equilibria':report['attempted_equilibria'],
        'saved_Newton_vectors':sum(len(case['states']) for rows in report['iterates'].values() for case in rows.values()),
        'peak':peak,'mesh_response':report['comparison'],'independent_checks':len(report['checks']),
        'sampled_boundary_screen':boundary['status'],'elapsed_seconds':runtime['elapsed_seconds'],
        'automatic_retries':0,'gpu':0,'ring_reruns':0,'mesh_generation_calls':0,
        'full_contour_passive_qualification':'not_run','active_contraction':'not_run','three_dimensional_model':'not_run',
        'fsi':'not_run','growth':'not_run','biological_validation':'not_run',
        'next_action':'Pending approval: from retained 0.02 states, complete original 0.04/0.06/0.08 on two contour meshes (at most six new states); unchanged physics and gates, single CPU, first failure stops; no active/3D/FSI yet.'}
    rendering={'status':'passed','visual_qa':'passed','style_validation':'passed','figures':figures,
        'actual_saved_equilibria':4,'new_FEM_solves':0,'deformation_scale':1,
        'source':'copied raw mesh/u/p; NumPy reconstruction; preserved failed CG1 controls',
        'physiological_time':'not_calibrated','interpolated_time_frames':0,
        'temporary_cleanup':'not_authorized; figure_runtime and task-owned test temporary files retained'}
    audit={'status':'passed','formal_invocation_files_unchanged':len(formal['files']),
        'protected_parent_files_unchanged':len(internal)+len(external),'preexisting_dirty_files_unchanged':len(dirty),
        'input_copies_match':len(identities),'host_native_independent_agreement':'passed',
        'tests':tests,'notebook_execution':'passed','style_validation':'passed','visual_qa':'passed',
        'postprocessing_new_FEM_solves':0,'repository_bytes':admission['repository']['usage']['logical_bytes']}
    for name,value in [('summary.json',summary),('rendering.json',rendering),('delivery_audit.json',audit),
        ('delivery_storage.json',admission),('cross_platform_agreement.json',agreement)]:
        save_json(root/name,value)
    for relative in sorted(set(SOURCES+['src/prl/rendering/fenicsx_contour_pressure.py','tests/prl/test_fenicsx_contour_pressure_render.py'])):
        target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(workspace/relative,target)
    coarse,fine=peak['M0'],peak['M1']
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F6-S1-S7 原轮廓首压力两网格资格</title>
<style>body{{max-width:1200px;margin:32px auto;padding:0 20px;color:#173e2e;font:16px/1.7 'Microsoft YaHei',sans-serif}}img{{width:100%}}a{{color:#176b4d}}td,th{{padding:8px 18px;border-bottom:1px solid #ccd}}</style>
<h1>原轮廓零载与首压力：粗细网格均通过原1%局部体积门</h1>
<p>FEniCSx P2/DG2、二维平面应变有限变形NH；mu=1、kappa=1000未标定。仅外边界来自图像，内腔/心内膜/ECM/心肌界面为构造，三层使用相同被动材料。内壁随动压力，外壁自由；A固定ux/uy，B固定uy。Ta=0。</p>
<table><tr><th>p/mu=0.02</th><th>M0：3541三角形</th><th>M1：14164三角形</th></tr>
<tr><td>腔室面积变化</td><td>{coarse['cavity_area_change']*100:+.6f}%</td><td>{fine['cavity_area_change']*100:+.6f}%</td></tr>
<tr><td>max|J−1|</td><td>{coarse['max_abs_J_minus_one']*100:.6f}%</td><td>{fine['max_abs_J_minus_one']*100:.6f}%</td></tr>
<tr><td>旧CG1 max|J−1|（仍failed）</td><td>6.71167%</td><td>11.15248%</td></tr></table>
<p>本轮4态全部接受，40项独立范围检查通过；细网格独立自由力残量{fine['independent_free_force']:.3e}，点态体积约束残差{fine['volume']['pointwise_constraint_max']:.3e}。
粗细面积响应差{report['comparison']['absolute']*100:.6f}个百分点、相对差{report['comparison']['relative']*100:.5f}%。</p>
<img src="{figures['qualification']['png']}" alt="真实参考结构、受压形变应力及新旧局部体积对照">
<h2>四个真实保存状态，统一色标</h2><p>每个网格仅零载和首压力两态，1倍形变；不是心动时刻，没有插值假帧。</p>
<img src="{figures['pressure_states']['png']}" alt="两网格各零载和受压的真实等效应力图">
<h2>证据边界与下一步</h2><p>这支持旧CG1不能充分约束局部J偏差的离散解释，不是只要提高容积模量或继续加密就能解决。
DG2有限bulk控制通过不证明严格不可压极限稳定，也不是三维四面体的直接资格。
细网格局部J峰值仍高于粗网格，热点尚未证明收敛；当前只通过首压力，不能宣称完整被动资格或实验吻合。</p>
<p>附加24/48段每二次边界边采样未见边界自交且腔室保持包含关系；这是采样筛查，不是精确曲线全局单射证明。
下一步待确认：复用两个网格0.02已接受态，仅续算原0.04/0.06/0.08，最多6态；同物理/1%门、单CPU/0GPU、首失败停止。之后再裁决主动收缩。</p>
<p>一次{runtime['elapsed_seconds']:.3f}秒单CPU禁网容器；0GPU/网格生成/圆环重算/自动重跑。24个真实Newton向量保存；{tests['passed']}测试+{tests['subtests_passed']}子测试通过。
{len(internal)+len(external)}父/祖先文件与{len(dirty)}无关修改保持，旧失败不回写。三维、主动、FSI、生长、生物学验证均not_run。</p>
<p>交付比较曾因唯一有限差分虚功字段相差1.332e-12而停止；原失败与报告保留。只给该显示量按机器精度/压力/面积/差分步长设置舍入比较余量，不改任何物理门或判定。</p>
<p><a href="post_verification.json">独立核验</a> · <a href="boundary_screen.json">边界采样筛查</a> · <a href="delivery_audit.json">交付审计</a> · <a href="cross_platform_agreement.json">跨平台逐字段复核</a> · <a href="configuration.json">冻结配置</a> · <a href="command.json">唯一正式调用</a> · <a href="{figures['qualification']['notebook']}">结构/资格Notebook</a> · <a href="{figures['pressure_states']['notebook']}">真实状态Notebook</a></p>
<p>复核：在PRL设置PYTHONPATH=src，运行 python -B -X utf8 -m prl verify fem-fenicsx-contour-pressure。
原run入口为create-only，已完成阶段不允许原地重跑。图件仅使用版本内副本，可用Notebook校验器单独复画到新版本；正式图件已冻结。</p></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    save_json(root/'manifest.json',package_manifest(root))
    register_result(workspace,root,summary['status'],digest(root/'manifest.json'))
    return {'status':summary['status'],'audit':audit,'manifest_sha256':digest(root/'manifest.json'),
        'files':sum(p.is_file() for p in root.rglob('*')),'logical_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file())}
