"""Portable plots of retained and newly solved 3D states; no FEM invocation."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def report_agreement(native,host,path=''):
    """Frozen cross-platform tolerances, never a replacement for physical gates."""
    if isinstance(native,dict) and isinstance(host,dict):
        if set(native)!=set(host):
            return [path+': keys differ']
        return [error for key in native for error in report_agreement(native[key],host[key],path+'/'+key)]
    if isinstance(native,list) and isinstance(host,list):
        if len(native)!=len(host):
            return [path+': lengths differ']
        return [error for i,(a,b) in enumerate(zip(native,host)) for error in report_agreement(a,b,path+'/'+str(i))]
    if isinstance(native,(int,float)) and not isinstance(native,bool) and isinstance(host,(int,float)) and not isinstance(host,bool):
        tolerance=1e-9 if path.split('/')[-1] in ['pressure_virtual_work_error','active_virtual_work_error'] else 1e-12
        same=np.isclose(native,host,rtol=1e-10,atol=tolerance)
    else:
        same=native==host
    return [] if same else [path+': values differ']


def draw(data_path,png_path,svg_path,style_module,mechanics,geometry,kind='overview',probe=None):
    if kind=='mesh_comparison':
        return draw_mesh_comparison(data_path,png_path,svg_path,style_module,mechanics,geometry,probe)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize,to_rgba
    from matplotlib.ticker import FixedLocator
    data=mechanics.load_arrays(data_path)
    cfg=json.loads(str(data['configuration'].item())); report=json.loads(str(data['verification'].item()))
    mesh={k[8:]:v for k,v in data.items() if k.startswith('mesh_M0_')}
    records=report['cases']['M0']
    available=[s['label'] for s in cfg['states'] if s['label'] in records]
    def state(label):
        prefix='state_M0_'+label+'__'
        return {k[len(prefix):]:v for k,v in data.items() if k.startswith(prefix)}
    computed={label:mechanics.fields(mesh,state(label),cfg) for label in available}
    equiv={}
    local_j={}
    for label,result in computed.items():
        sigma=result['stress']; deviator=sigma-np.trace(sigma,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
        vm=np.sqrt(1.5*np.sum(deviator**2,axis=(-1,-2)))
        equiv[label]=np.sum(vm*result['weights'],axis=1)/result['weights'].sum(axis=1)
        _,extra,_,_,_,_=mechanics.kinematics(mesh,state(label)['u'],mechanics.extra_points())
        local_j[label]=np.maximum(np.max(np.abs(result['J']-1),axis=1),np.max(np.abs(extra-1),axis=1))*100
    style=style_module.StyleSpec(axis_box_size_in=(3.6,3.6),tick_label_size=16.,axis_label_size=18.,
        annotation_font_size=16.,sample_size_and_stat_font_size=14.,legend_font_size=14.,axes_line_width=1.5,
        major_tick_length_pt=5.,major_tick_width_pt=1.,minor_tick_length_pt=3.,minor_tick_width_pt=.8,
        data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=k,reason='Existing compact FEM diagnostic layout, with equal-scale orthographic 3D cutaways.')
               for k,v in asdict(style).items() if v!=defaults[k]]
    faces,owners=geometry.boundary_faces(mesh)
    pieces=np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    view=np.array([1.8,-2.4,1.6]); view/=np.linalg.norm(view)
    horizontal=np.cross([0.,0.,1.],view); horizontal/=np.linalg.norm(horizontal)
    projection=np.stack([horizontal,np.cross(view,horizontal)],axis=1)
    all_xy=np.concatenate([(mesh['coordinates']+state(label)['u'])@projection for label in available])
    center=(all_xy.min(axis=0)+all_xy.max(axis=0))/2; half=np.ptp(all_xy,axis=0).max()*.57
    stress_norm=Normalize(0,max(max(v) for v in equiv.values()) or 1.)
    j_norm=Normalize(0,max(1.,max(max(v) for v in local_j.values())))
    colors=np.array([to_rgba(x) for x in ['#4C9F70','#D6B656','#5B8DB8']])
    def cutaway(axis,label,title,field=None,structure=False):
        nodes=mesh['coordinates']+(0 if structure else state(label)['u'])
        surface=nodes[faces[:,pieces]].reshape(-1,3,3); order=np.argsort(surface.mean(axis=1)@view)
        axis.set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),
                 xlabel='Projected x / L',ylabel='Projected height / L',aspect='equal')
        axis.xaxis.set_major_locator(FixedLocator([-1.,0.,1.])); axis.yaxis.set_major_locator(FixedLocator([-1.,0.,1.]))
        if structure:
            facecolors=np.repeat(colors[mesh['layers'][owners]-1],4,axis=0)
            normals=np.cross(surface[:,1]-surface[:,0],surface[:,2]-surface[:,0])
            normals/=np.linalg.norm(normals,axis=1)[:,None]
            facecolors[:,:3]*=(.72+.28*np.abs(normals@view))[:,None]
            artist=PolyCollection((surface@projection)[order],facecolors=facecolors[order],edgecolors=(.1,.15,.2,.5),linewidths=.15)
        else:
            values=equiv[label] if field=='stress' else local_j[label]
            artist=PolyCollection((surface@projection)[order],array=np.repeat(values[owners],4)[order],
                norm=stress_norm if field=='stress' else j_norm,cmap='viridis',edgecolors=(.1,.15,.2,.4),linewidths=.12)
        axis.add_collection(artist)
        if structure:
            base=(np.abs(nodes[:,2])<1e-12)&(nodes[:,1]>=0)
            axis.plot(*(nodes[base]@projection).T,'o',color='#A83935',ms=1.6)
        style_module.apply_axes_style(axis,style=style)
        style_module.add_top_information(axis,title,style=style)
        return artist
    def colorbar(figure,artist,rect,label):
        cax=figure.add_axes(rect); figure.colorbar(artist,cax=cax).set_label(label,fontsize=16,labelpad=9)
        cax.tick_params(labelsize=14,direction='out')
    if kind=='overview':
        width,height=14.4,13.6; figure=plt.figure(figsize=(width,height))
        axes=[figure.add_axes((x/width,y/height,3.6/width,3.6/height)) for x,y in [(1.3,8.),(8.1,8.),(1.3,2.8),(8.1,2.8)]]
        last=available[-1]; spec=next(s for s in cfg['states'] if s['label']==last)
        cutaway(axes[0],'zero','A  Reference structure',structure=True)
        artist=cutaway(axes[1],last,'B  Last stored: '+last,field='stress')
        colorbar(figure,artist,(12.05/width,8./height,.22/width,3.6/height),'Cell-mean equivalent stress / mu')
        artist=cutaway(axes[2],last,'C  Local volume distortion',field='J')
        colorbar(figure,artist,(5.25/width,2.8/height,.22/width,3.6/height),'Cell max |J - 1| (%)')
        series=[('pressure',['zero','pressure_1','pressure_2'],'#377BA8'),('active',['zero','active_1','active_2'],'#D55E00'),
                ('combined',['pressure_2','combined_1','combined_2'],'#23906A')]
        for name,marker in [('M0','o'),('M1','s')]:
            for branch,labels,color in series:
                subset=[(i,report['cases'].get(name,{}).get(label)) for i,label in enumerate(labels)]
                subset=[(i,r) for i,r in subset if r is not None and 'volume_change' in r]
                if len(subset)<2:
                    continue
                axes[3].plot([i for i,r in subset],[r['volume_change']*100 for i,r in subset],
                    marker=marker,ls='-' if name=='M0' else '--',color=color,label=name+' '+branch)
                for i,r in subset:
                    if r['status']=='failed':
                        axes[3].plot(i,r['volume_change']*100,'x',color='#A83935',ms=12,mew=2.)
        axes[3].axhline(0,color='.6',lw=.8); axes[3].set(xlim=(-.1,2.1),xticks=[0,1,2],xlabel='Load level (not time)',ylabel='Cavity volume change (%)')
        style_module.apply_axes_style(axes[3],style=style); style_module.add_top_information(axes[3],'D  Stored equilibrium responses',style=style)
        handles,_=axes[3].get_legend_handles_labels()
        if handles:
            axes[3].legend(frameon=False,fontsize=11,loc='best')
        subtitle=f'B/C: M0, p/mu={spec["p"]:g}, Ta/mu={spec["Ta"]:g}; state {records[last]["status"].upper()}. True 1x deformation.'
    else:
        preferred=['zero','pressure_1','pressure_2','active_2','combined_1','combined_2']
        selected=[label for label in preferred if label in available]
        selected+= [label for label in available if label not in selected and label not in preferred]
        selected=selected[:6]; width,height=18.8,13.6; figure=plt.figure(figsize=(width,height)); axes=[]
        for i,label in enumerate(selected):
            x=[1.3,7.1,12.9][i%3]; y=8. if i<3 else 2.8
            axis=figure.add_axes((x/width,y/height,3.6/width,3.6/height)); axes.append(axis)
            artist=cutaway(axis,label,chr(65+i)+'  '+label,field='stress')
            result=records[label]
            axis.text(.02,.03,f'dV = {result["volume_change"]*100:+.3f}%\n{result["status"].upper()}',
                      transform=axis.transAxes,fontsize=13,color='#20694D' if result['status']=='passed' else '#A83935')
        colorbar(figure,artist,(17.15/width,3.0/height,.22/width,8.4/height),'Cell-mean equivalent stress / mu; shared scale')
        subtitle='M0 actual saved states; common view, common stress scale, true 1x deformation. No interpolated states.'
    figure.text(.06,.965,'Idealized 3D solid | qualification '+report['status'].upper(),fontsize=18)
    figure.text(.06,.932,subtitle,fontsize=14)
    figure.text(.06,.137,'Structure: endo (green), ECM (yellow), myo (blue); fixed basal ring (red), free outer wall.',fontsize=12)
    figure.text(.06,.105,'P2/P1 tetrahedra; mu=1, kappa=1000. Follower lumen pressure; dispersed tangential active tension in myo only.',fontsize=12)
    figure.text(.06,.073,'J panels use quadrature + 56 additional points per cell. Original local gate: max |J-1| <= 1%. No nodal smoothing.',fontsize=12)
    figure.text(.06,.041,'Display cutaway only; full 3D wall solved. No flow, growth, measured material/fibers, or physiological time calibration.',fontsize=12)
    exported=style_module.export_figure(figure,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    Path(exported.svg).replace(svg_path)
    manifest=json.loads(Path(exported.manifest).read_text()); manifest['exports']['svg']=str(Path(svg_path).resolve())
    Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8'); plt.close(figure)
    return {'status':'passed','scientific_status':report['status'],'states':available,'deformation_scale':1,'new_FEM_solves':0}


def draw_mesh_comparison(data_path,png_path,svg_path,style_module,mechanics,geometry,probe):
    """Same-load cutaways: two real meshes, shared stress/J scales, no smoothing."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize,to_rgba
    data=mechanics.load_arrays(data_path); cfg=json.loads(str(data['configuration'].item()))
    report=json.loads(str(data['verification'].item())); records=report['cases']
    meshes={name:{k[8:]:v for k,v in data.items() if k.startswith('mesh_'+name+'_')} for name in ['M0','M1']}
    states={}; measures={}
    for name in meshes:
        prefix=f'state_{name}_pressure_1__'
        states[name]={k[len(prefix):]:v for k,v in data.items() if k.startswith(prefix)}
        if states[name]:
            measures[name]=probe.cell_measures(meshes[name],states[name],cfg,mechanics)
    style=style_module.StyleSpec(axis_box_size_in=(3.6,3.6),tick_label_size=16.,axis_label_size=18.,
        annotation_font_size=16.,sample_size_and_stat_font_size=14.,legend_font_size=14.,axes_line_width=1.5,
        major_tick_length_pt=5.,major_tick_width_pt=1.,minor_tick_length_pt=3.,minor_tick_width_pt=.8,
        data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=k,reason='Reuse compact 3D FEM diagnostic axes; same projection and scales for both meshes.')
               for k,v in asdict(style).items() if v!=defaults[k]]
    width,height=18.8,12.8; figure=plt.figure(figsize=(width,height)); axes=[]
    view=np.array([1.8,-2.4,1.6]); view/=np.linalg.norm(view)
    horizontal=np.cross([0.,0.,1.],view); horizontal/=np.linalg.norm(horizontal)
    projection=np.stack([horizontal,np.cross(view,horizontal)],axis=1)
    coordinates=np.concatenate([mesh['coordinates']+states[name].get('u',0.) for name,mesh in meshes.items() if mesh])@projection
    center=(coordinates.min(axis=0)+coordinates.max(axis=0))/2; half=np.ptp(coordinates,axis=0).max()*.57
    norms={'equivalent_stress':Normalize(0,max(float(item['equivalent_stress'].max()) for item in measures.values()) or 1.),
           'max_abs_J_minus_one':Normalize(0,max(1.,max(float(item['max_abs_J_minus_one'].max())*100 for item in measures.values())))}
    pieces=np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]]); colors=np.array([to_rgba(c) for c in ['#4C9F70','#D6B656','#5B8DB8']])
    for row,name in enumerate(['M0','M1']):
        mesh=meshes[name]; y=7.6 if row==0 else 2.8
        if mesh:
            faces,owners=geometry.boundary_faces(mesh)
        for col,field in enumerate([None,'equivalent_stress','max_abs_J_minus_one']):
            axis=figure.add_axes(([1.25,7.,12.8][col]/width,y/height,3.6/width,3.6/height)); axes.append(axis)
            axis.set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),
                     xticks=[-1,0,1],yticks=[-1,0,1],xlabel='Projected x / L',ylabel='Projected height / L',aspect='equal')
            title=chr(65+row*3+col)+'  '+name+' '+['reference','stress','local volume'][col]
            style_module.apply_axes_style(axis,style=style); style_module.add_top_information(axis,title,style=style)
            if not mesh or (field is not None and name not in measures):
                axis.text(.5,.5,'NOT RUN',ha='center',transform=axis.transAxes)
                continue
            nodes=mesh['coordinates']+(states[name]['u'] if field else 0.)
            surface=nodes[faces[:,pieces]].reshape(-1,3,3); order=np.argsort(surface.mean(axis=1)@view)
            if field is None:
                facecolors=np.repeat(colors[mesh['layers'][owners]-1],4,axis=0)
                normal=np.cross(surface[:,1]-surface[:,0],surface[:,2]-surface[:,0]); normal/=np.linalg.norm(normal,axis=1)[:,None]
                facecolors[:,:3]*=(.72+.28*np.abs(normal@view))[:,None]
                artist=PolyCollection((surface@projection)[order],facecolors=facecolors[order],edgecolors=(.1,.15,.2,.4),linewidths=.12)
                base=(np.abs(nodes[:,2])<1e-12)&(nodes[:,1]>=0)
                axis.plot(*(nodes[base]@projection).T,'o',color='#A83935',ms=1.3)
            else:
                values=measures[name][field]*(100 if field=='max_abs_J_minus_one' else 1.)
                artist=PolyCollection((surface@projection)[order],array=np.repeat(values[owners],4)[order],norm=norms[field],
                    cmap='viridis',edgecolors=(.1,.15,.2,.35),linewidths=.1)
                if row==0:
                    cax=figure.add_axes(([0,10.95,16.75][col]/width,y/height,.2/width,3.6/height))
                    label='Cell-mean equivalent stress / mu' if col==1 else 'Cell max |J - 1| (%)'
                    figure.colorbar(artist,cax=cax).set_label(label,fontsize=16,labelpad=8); cax.tick_params(labelsize=14,direction='out')
            axis.add_collection(artist)
            if field=='equivalent_stress':
                audit=records[name]['pressure_1']
                axis.text(.03,.035,f'dV = {audit["volume_change"]*100:+.4f}%\n{audit["status"].upper()}',
                    transform=axis.transAxes,fontsize=14,color='#A83935' if audit['status']=='failed' else '#20694D')
    figure.text(.055,.963,'Same-load 3D mesh diagnostic | '+report['status'].upper(),fontsize=18)
    figure.text(.055,.930,'p/mu = 0.01, Ta = 0; same material, basal clamp and P2/P1 formulation. True 1x deformation.',fontsize=14)
    figure.text(.055,.145,'Reference: endo green / ECM yellow / myo blue; fixed basal ring red. Full 3D wall solved; cutaway is display-only.',fontsize=12)
    outcomes=[]
    for name in ['M0','M1']:
        if name in measures:
            outcomes.append(f'{name}: max |J-1| = {measures[name]["max_abs_J_minus_one"].max()*100:.4f}%')
    figure.text(.055,.113,'; '.join(outcomes)+'. Original local gate: 1%. Each column uses a shared scale.',fontsize=12)
    figure.text(.055,.081,'J: quadrature + 56 extra points/cell; no smoothing. M0 retained, M1 newly solved. Missing states are not fabricated.',fontsize=12)
    figure.text(.055,.049,'Two discrete curved geometries; not pure h-refinement or asymptotic convergence. No contraction, growth, flow or biological validation.',fontsize=12)
    exported=style_module.export_figure(figure,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    Path(exported.svg).replace(svg_path)
    manifest=json.loads(Path(exported.manifest).read_text()); manifest['exports']['svg']=str(Path(svg_path).resolve())
    Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8'); plt.close(figure)
    return {'status':'passed','scientific_status':report['status'],'displayed_pressure_states':list(measures),'deformation_scale':1,'new_FEM_solves':0}


def prepare(workspace,skills,*,fine_pressure=False):
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path,result_admission
    from prl.runs.ventricle_3d import RESUME_RESULT,FINE_RESULT
    from prl.runs.fenicsx_runtime import save_json
    from prl.runs.fenicsx_ring import digest
    from prl.verification.ventricle_3d import verify,load_arrays,state_path
    workspace=Path(workspace); skills=Path(skills); root=result_path(workspace,FINE_RESULT if fine_pressure else RESUME_RESULT)
    if (root/'post_verification.json').exists() or (root/'figures').exists():
        raise FileExistsError('Create-only postprocessing')
    if not result_admission(workspace,256*1024**2)['can_start']:
        raise RuntimeError('Postprocessing storage refused')
    formal=json.loads((root/'formal_invocation_manifest.json').read_text())
    if not all(digest(root/f['path'])==f['sha256'] for f in formal['files']):
        raise ValueError('Frozen invocation changed')
    report=verify(root); native=json.loads((root/'verification.json').read_text())
    differences=report_agreement(native,report)
    save_json(root/'report_comparison.json',{'status':'failed' if differences else 'passed','differences':differences,
        'ordinary_rtol':1e-10,'ordinary_atol':1e-12,'two_virtual_work_error_atol':1e-9})
    if differences:
        raise ValueError('Host/native comparison failed')
    save_json(root/'post_verification.json',report)
    if fine_pressure:
        from prl.verification.ventricle_mesh_probe import verify_probe
        diagnostic=verify_probe(root); save_json(root/'mesh_diagnostic.json',diagnostic)
        report={'status':diagnostic['status'],'cases':{'M0':{'pressure_1':diagnostic['retained_coarse']},**report['cases']}}
    cfg=json.loads((root/'configuration.json').read_text()); identities={}
    data={'configuration':np.array(json.dumps(cfg)),'verification':np.array(json.dumps(report))}
    for name,records in report['cases'].items():
        folder='retained' if fine_pressure and name=='M0' else 'raw'
        mesh_path=root/folder/f'{name}_mesh.npz'
        if not mesh_path.exists():
            continue
        identities[mesh_path.relative_to(root).as_posix()]=digest(mesh_path)
        data.update({f'mesh_{name}_'+k:v for k,v in load_arrays(mesh_path).items()})
        for label in records:
            path=root/folder/f'{name}_state_{label}.npz' if fine_pressure else state_path(root,cfg,name,label)
            identities[path.relative_to(root).as_posix()]=digest(path)
            data.update({f'state_{name}_{label}__'+k:v for k,v in load_arrays(path).items()
                         if k in ['u','pressure','load','activation']})
    data['source_identities']=np.array(json.dumps(identities)); np.savez_compressed(root/'figure_data.npz',**data)
    revisions=[]
    kinds=['mesh_comparison'] if fine_pressure else ['overview','states'] if len(report['cases']['M0'])>=5 else ['overview']
    main='S2D1' if fine_pressure else 'S2R'
    for kind in kinds:
        command=[sys.executable,'-B','-X','utf8',str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
            str(root/'figures'),'--main',main,'--analysis-key','3d_'+kind,'--data',str(root/'figure_data.npz')]
        snapshots={'helper':Path(__file__).resolve(),'mechanics':workspace/'src/prl/verification/ventricle_3d.py',
                   'geometry':workspace/'src/prl/rendering/ventricle_3d.py','style':skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'}
        if fine_pressure:
            snapshots['probe']=workspace/'src/prl/verification/ventricle_mesh_probe.py'
        for key,path in snapshots.items():
            command.extend(['--python',key+'='+str(path)])
        command.extend(['--model','config='+str(root/'configuration.json'),'--model','verification='+str(root/'post_verification.json')])
        subprocess.run(command,check=True)
        revision=next((root/f'figures/Fig{main}_3d_{kind}').glob('Fig'+main+'_*')); prefix=revision.name
        filenames={key:next(revision.glob(f'*_{key}.py')).name for key in snapshots}
        code=f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 作图调整参数: explicit compact FEM overrides, identical physical scales across states.
STYLE_SOURCE = 'Existing compact FEM diagnostic style'
DPI = 600
axis_box_size_in = (3.6, 3.6)
FIGURE_SIZE_IN = {(18.8,12.8) if fine_pressure else (14.4,13.6) if kind=='overview' else (18.8,13.6)!r}
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
snapshots = {{key: load_snapshot('f6s2r_'+key, filename) for key,filename in {filenames!r}.items()}}
snapshots['helper'].draw(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, snapshots['style'], snapshots['mechanics'], snapshots['geometry'], kind={kind!r}, probe=snapshots.get('probe'))'''
        notebook=nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(
            '# 三维固体实际状态\n只画保存的数值状态；M0历史数据保留，缺失或失败状态明确标注。加载级不是心动时间，无FSI/生长/实验标定。'),
            nbformat.v4.new_code_cell(code),nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=1100))')],
            metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
        nbformat.write(notebook,revision/f'03_{prefix}_plot.ipynb')
        methods=revision/f'02_{prefix}_methods.txt'; content=methods.read_text(encoding='utf-8')
        values={'风格来源':'既有紧凑FEM风格；3.6英寸方轴，600dpi PNG及可编辑SVG，显式样式例外。',
            '用户提供的期刊规格':'未指定；内部数值资格图，不是实验验证。',
            '03_材料方法来源':'01物理复制实存网格和各态u/p/载荷，含来源SHA256；03辅助代码、独立NumPy力学公式、图形几何、样式和配置全部快照。',
            '数据/模型变换':'从实存u/p独立重算F/J/Cauchy应力；等效应力为逐单元积分体积加权均值，J为积分点与额外56点最大绝对偏差；无节点平滑。显示y>0单元剖开、P2面分四片、真实1倍正交投影，共同轴限/场范围；求解仍完整三维。',
            '统计方法与不确定性':'无生物样本或推断统计；粗细两网格比较仅体积响应，不是热点收敛。加载级非时间；原无载与新态来源见核验。失败/缺失态不补造。',
            '生物学分组颜色':'不适用。结构层标签不是生物学组；三层被动参数相同且未标定，主动仅心肌域。'}
        for key,value in values.items():
            content=re.sub(r'(?m)^- '+re.escape(key)+r':.*$',lambda match:'- '+key+': '+value,content)
        methods.write_text(content,encoding='utf-8'); revisions.append(str(revision))
    output={'status':'passed','scientific_status':report['status'],'revisions':revisions,'new_FEM_solves':0}
    save_json(root/'render_preparation.json',output)
    return output
