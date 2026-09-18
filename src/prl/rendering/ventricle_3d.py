"""Actual 3D cutaway and saved zero-state delivery; never synthesize missing loads."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def boundary_faces(data):
    """Expose the y>=0 half of the actual tetrahedral mesh, not a new geometry."""
    edge_pairs=[(2,3),(1,3),(1,2),(0,3),(0,2),(0,1)]
    xyz=data['coordinates']; cells=data['cells']; faces={}
    selected=np.where(xyz[cells[:,:4]].mean(axis=1)[:,1]>0)[0]
    for cell_id in selected:
        cell=cells[cell_id]; center=xyz[cell[:4]].mean(axis=0)
        edge={tuple(sorted((i,j))):cell[k+4] for k,(i,j) in enumerate(edge_pairs)}
        for local in [(1,2,3),(0,3,2),(0,1,3),(0,2,1)]:
            a,b,c=local; key=tuple(sorted(cell[list(local)]))
            if key in faces:
                faces[key]=None
                continue
            vertices=xyz[cell[[a,b,c]]]
            if np.dot(np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0]),vertices.mean(axis=0)-center)<0:
                b,c=c,b
            nodes=[cell[a],cell[b],cell[c],edge[tuple(sorted((b,c)))],
                   edge[tuple(sorted((a,c)))],edge[tuple(sorted((a,b)))]]
            faces[key]=(nodes,cell_id)
    kept=[entry for entry in faces.values() if entry is not None]
    return np.asarray([f for f,c in kept]),np.asarray([c for f,c in kept])


def draw(data_path,png_path,svg_path,style_module,mechanics):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize,to_rgba
    from matplotlib.ticker import FixedLocator
    data=mechanics.load_arrays(data_path)
    cfg=json.loads(str(data['configuration'].item()))
    mesh={k[5:]:v for k,v in data.items() if k.startswith('mesh_')}
    state={k[6:]:v for k,v in data.items() if k.startswith('state_')}
    fields=mechanics.fields(mesh,state,cfg)
    if float(state['load'])!=0 or float(state['activation'])!=0:
        raise ValueError('This retained start figure is specifically the zero-load state')
    style=style_module.StyleSpec(axis_box_size_in=(3.6,3.6),tick_label_size=16.,axis_label_size=18.,
        annotation_font_size=16.,sample_size_and_stat_font_size=14.,legend_font_size=14.,axes_line_width=1.5,
        major_tick_length_pt=5.,major_tick_width_pt=1.,minor_tick_length_pt=3.,minor_tick_width_pt=.8,
        data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=k,reason='Existing compact FEM diagnostic style; orthographic equal-scale 3D cutaway.')
        for k,v in asdict(style).items() if v!=defaults[k]]
    figure=plt.figure(figsize=(14.4,13.6))
    axes=[figure.add_axes((x/14.4,y/13.6,3.6/14.4,3.6/13.6)) for x,y in [(1.3,8.),(8.1,8.),(1.3,2.8)]]
    text_axis=figure.add_axes((8.1/14.4,2.8/13.6,4.6/14.4,3.6/13.6)); text_axis.set_axis_off()
    faces,owners=boundary_faces(mesh)
    pieces=np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    view=np.array([1.8,-2.4,1.6]); view/=np.linalg.norm(view)
    horizontal=np.cross([0.,0.,1.],view); horizontal/=np.linalg.norm(horizontal)
    vertical=np.cross(view,horizontal); projection=np.stack([horizontal,vertical],axis=1)
    nodes=mesh['coordinates']+state['u']; surface=nodes[faces[:,pieces]].reshape(-1,3,3)
    depth=surface.mean(axis=1)@view; order=np.argsort(depth)
    projected=surface@projection
    center=(projected.reshape(-1,2).min(axis=0)+projected.reshape(-1,2).max(axis=0))/2
    half=np.ptp(projected.reshape(-1,2),axis=0).max()*.6
    for axis,title in zip(axes[:2],['A  Reference structure (cutaway)','B  Actual solved zero-load state']):
        axis.set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),
                 xlabel="Projected x / L",ylabel="Projected height / L",aspect='equal')
        axis.xaxis.set_major_locator(FixedLocator([-1.,0.,1.]))
        axis.yaxis.set_major_locator(FixedLocator([-1.,0.,1.]))
        style_module.apply_axes_style(axis,style=style)
        style_module.add_top_information(axis,title,style=style)
    colors=np.array([to_rgba(x) for x in ['#4C9F70','#D6B656','#5B8DB8']])
    cell_colors=colors[mesh['layers'][owners]-1]
    shade=np.cross(surface[:,1]-surface[:,0],surface[:,2]-surface[:,0])
    shade/=np.linalg.norm(shade,axis=1)[:,None]
    brightness=.72+.28*np.abs(shade@view)
    facecolors=np.repeat(cell_colors,4,axis=0); facecolors[:,:3]*=brightness[:,None]
    axes[0].add_collection(PolyCollection(projected[order],facecolors=facecolors[order],
        edgecolors=(.1,.15,.2,.5),linewidths=.15))
    base=np.abs(nodes[:,2])<1e-12
    base&=nodes[:,1]>=0
    axes[0].plot(*(nodes[base]@projection).T,'o',color='#A83935',ms=1.5)
    volume=np.max(np.abs(fields['J']-1),axis=1)*100
    artist=PolyCollection(projected[order],array=np.repeat(volume[owners],4)[order],norm=Normalize(0,1),
        cmap='viridis',edgecolors=(.4,.5,.55,.5),linewidths=.15)
    axes[1].add_collection(artist)
    cax=figure.add_axes((12.05/14.4,8./13.6,.22/14.4,3.6/13.6))
    figure.colorbar(artist,cax=cax).set_label('max |J - 1| (%)',fontsize=18,labelpad=10)
    cax.tick_params(labelsize=16,direction='out')
    errors=[json.loads(str(data[name+'_geometry'].item()))['relative_cavity_geometry_error']*100 for name in ['M0','M1']]
    axes[2].bar([0,1],errors,width=.45,color=['#5B8DB8','#4C9F70'])
    axes[2].set(xlim=(-.6,1.6),ylim=(0,8),xlabel='Constructed 3D mesh',ylabel='Reference cavity error (%)')
    axes[2].set_xticks([0,1],['M0','M1']); axes[2].set_yticks([0,2,4,6,8])
    for i,value in enumerate(errors):
        axes[2].text(i,value+.25,f'{value:.3f}%',ha='center',fontsize=16)
    style_module.apply_axes_style(axes[2],style=style)
    style_module.add_top_information(axes[2],'C  Geometry only; not convergence',style=style)
    text_axis.text(0,1.02,'D  What has actually been verified',fontsize=16,transform=text_axis.transAxes)
    lines=[('M0 zero load: offline audit PASSED','#20694D'),
           ('max displacement = 0; J = 1','#222222'),
           ('Free residual = 1.24e-16','#222222'),
           ('Execution stopped on array-layout error','#A83935'),
           ('Pressure / active loads: NOT RUN','#A83935'),
           ('M1 equilibrium: NOT RUN','#A83935'),
           ('FSI / growth / biology: NOT RUN','#555555')]
    for i,(label,color) in enumerate(lines):
        text_axis.text(0,.87-.125*i,label,fontsize=14,color=color,transform=text_axis.transAxes)
    figure.text(.06,.965,'Idealized 3D solid established | stage FAILED at interface validation; no automatic rerun',fontsize=16)
    figure.text(.06,.932,'Real saved zero-load state only. Missing pressure/contraction states are not fabricated.',fontsize=14)
    figure.text(.06,.137,'Green / yellow / blue: assumed endo / ECM / myo. Red points: fixed basal ring. Outer wall free.',fontsize=12)
    figure.text(.06,.104,'Half-ellipsoidal shell, P2/P1 tetrahedra; mu=1, kappa=1000. Geometry and material are uncalibrated.',fontsize=12)
    figure.text(.06,.071,'Planned loads: follower cavity pressure and tangentially dispersed myocardial tension. Neither has been solved.',fontsize=12)
    figure.text(.06,.038,'Cutaway removes the display half only; full 3D wall was solved. True 1x coordinates, no physiological time.',fontsize=12)
    exported=style_module.export_figure(figure,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    Path(exported.svg).replace(svg_path)
    manifest=json.loads(Path(exported.manifest).read_text())
    manifest['exports']['svg']=str(Path(svg_path).resolve())
    Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.close(figure)
    return {'status':'passed','scientific_stage':'failed','actual_solved_states':1,'deformation_scale':1,
            'new_FEM_solves':0,'pressure_and_active_states':'not_run'}


def prepare(workspace,skills):
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path,result_admission
    from prl.runs.ventricle_3d import RESULT
    from prl.runs.fenicsx_runtime import save_json
    from prl.runs.fenicsx_ring import digest
    from prl.verification.ventricle_3d import verify,load_arrays
    workspace=Path(workspace); skills=Path(skills); root=result_path(workspace,RESULT)
    if (root/'post_verification.json').exists() or (root/'figures').exists():
        raise FileExistsError('Create-only delivery preparation')
    if not result_admission(workspace,128*1024**2)['can_start']:
        raise RuntimeError('Postprocessing storage refused')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    if not all(digest(root/f['path'])==f['sha256'] for f in formal['files']):
        raise ValueError('Formal failed invocation changed')
    report=verify(root); save_json(root/'post_verification.json',report)
    config=json.loads((root/'configuration.json').read_text())
    data={'configuration':np.array(json.dumps(config)),'verification':np.array(json.dumps(report))}
    data.update({'mesh_'+k:v for k,v in load_arrays(root/'raw/M0_mesh.npz').items()})
    data.update({'state_'+k:v for k,v in load_arrays(root/'raw/M0_state_zero.npz').items()})
    for name in ['M0','M1']:
        data[name+'_geometry']=np.array((root/'input'/f'{name}_geometry.json').read_text())
    np.savez_compressed(root/'figure_data.npz',**data)
    subprocess.run([sys.executable,'-B','-X','utf8',str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
        str(root/'figures'),'--main','S2','--analysis-key','3d_start','--data',str(root/'figure_data.npz'),
        '--python','helper='+str(Path(__file__).resolve()),
        '--python','mechanics='+str(workspace/'src/prl/verification/ventricle_3d.py'),
        '--python','style='+str(skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'),
        '--model','config='+str(root/'configuration.json'),'--model','verification='+str(root/'post_verification.json')],check=True)
    revision=next((root/'figures/FigS2_3d_start').glob('FigS2_*')); prefix=revision.name
    snapshots={key:next(revision.glob(f'*_{key}.py')).name for key in ['helper','mechanics','style']}
    code=f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 作图调整参数: reuse compact FEM style; every override recorded by helper.
STYLE_SOURCE = 'Existing compact FEM diagnostics, explicit CB overrides'
DPI = 600
axis_box_size_in = (3.6, 3.6)
FIGURE_SIZE_IN = (14.4, 13.6)
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
helper = load_snapshot('solid_plot_snapshot', {snapshots['helper']!r})
mechanics = load_snapshot('solid_audit_snapshot', {snapshots['mechanics']!r})
style = load_snapshot('cb_style_snapshot', {snapshots['style']!r})
helper.draw(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, style, mechanics)'''
    notebook=nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell('# 理想化三维心室：结构与唯一真实无载态\n执行在数组格式复核处失败。只离线修复读取并核验，无第二次FEM。载荷/生长/FSI均未运行，不补造5帧。'),
        nbformat.v4.new_code_cell(code),nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=1100))')],
        metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
    nbformat.write(notebook,revision/f'03_{prefix}_plot.ipynb')
    methods=revision/f'02_{prefix}_methods.txt'; content=methods.read_text(encoding='utf-8')
    values={'风格来源':'既有紧凑FEM图件，主轴3.6×3.6英寸，600dpi PNG与可编辑SVG；字号等例外有manifest。',
        '用户提供的期刊规格':'未指定；内部数值资格及失败交付，不是发表验证图。',
        '03_材料方法来源':'helper/mechanics/style及配置和核验物理复制；01包含原始3D网格、唯一无载u/p/应力和两输入几何指标，Notebook不依赖FEM或代码仓。',
        '数据/模型变换':'从保存u/p独立重算F/J。选择y>=0单元的外表面形成显示剖开，计算仍为完整壳；P2面分四个显示三角、按真实1倍3D坐标正交投影、无平滑。A仅层颜色作光照，B场值不作光照变色。',
        '统计方法与不确定性':'仅一个真实无载平衡态。C为输入网格体积相对解析半椭球的几何误差，不是FEM网格收敛。没有生物样本、显著性检验、心动时间或虚构加载状态。',
        '生物学分组颜色':'不适用。绿/黄/蓝为假设心内膜/ECM/心肌材料域标签，三层本轮同被动参数。未校准。'}
    for key,value in values.items():
        content=re.sub(r'(?m)^- '+re.escape(key)+r':.*$',lambda match:'- '+key+': '+value,content)
    methods.write_text(content,encoding='utf-8')
    return {'status':'passed','scientific_stage':'failed','revisions':[str(revision)],'new_FEM_solves':0}
