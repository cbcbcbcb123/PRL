"""Saved-mesh diagnostics only: no solver calls or fabricated mechanical fields."""

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np


def diagnose(mesh):
    points=mesh['xy'][mesh['triangles']]
    angles=[]
    for i in range(3):
        a=points[:,(i+1)%3]-points[:,i]
        b=points[:,(i+2)%3]-points[:,i]
        angles.append(np.degrees(np.arccos(np.clip(np.sum(a*b,axis=1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)),-1,1))))
    minimum=np.min(angles,axis=0)
    layers={}
    for layer,label in [(1,'assumed_endocardium'),(2,'assumed_ECM'),(3,'assumed_myocardium')]:
        values=minimum[mesh['labels']==layer]
        layers[label]={'cells':len(values),'below_20_degrees':int(np.sum(values<20)),
                       'minimum_angle_degrees':float(values.min())}
    worst=int(np.argmin(minimum))
    return minimum,{'status':'failed' if np.any(minimum<20) else 'passed','geometry_gate':'minimum_angle','mechanical_equilibria':0,
                    'cells':len(minimum),'below_20_degrees':int(np.sum(minimum<20)),
                    'layers':layers,'worst_cell':worst,'minimum_angle_degrees':float(minimum[worst]),
                    'worst_centroid':points[worst].mean(axis=0).tolist(),
                    'interpretation':'All poor cells are in the two thin constructed layers. This does not diagnose material response.',
                    'next_step':'boundary sampling matched to local thin-layer thickness and constrained quality meshing; no threshold relaxation'}


def draw_mesh_diagnostic(data_path,png_path,svg_path,style_module,axis_box_size_in=(3.7,3.7),figure_size_in=(16.8,7.4)):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.ticker import FixedLocator

    with np.load(data_path,allow_pickle=False) as archive:
        mesh={key:archive[key] for key in archive.files}
    minimum,report=diagnose(mesh)
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=16.,axis_label_size=18.,annotation_font_size=16.,sample_size_and_stat_font_size=14.,
        legend_font_size=14.,axes_line_width=1.5,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    default=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=key,reason='Reuse established compact FEM engineering panels; explicit margins, equal spatial scale, no biological grouping.')
               for key,value in asdict(style).items() if value!=default[key]]
    fig=plt.figure(figsize=figure_size_in)
    axes=[fig.add_axes((x/figure_size_in[0],2.3/figure_size_in[1],3.7/figure_size_in[0],3.7/figure_size_in[1])) for x in [1.05,6.15,11.25]]
    triangles=mesh['xy'][mesh['triangles']]
    colors=np.array(['#4C9F70','#D6B656','#5B8DB8'])
    axes[0].add_collection(PolyCollection(triangles,facecolors=colors[mesh['labels']-1],edgecolors=(.1,.1,.1,.25),linewidths=.18))
    axes[1].add_collection(PolyCollection(triangles,facecolors=np.where((minimum<20)[:,None],np.array([.73,.18,.17,1]),np.array([.90,.92,.94,1])),edgecolors=(.1,.1,.1,.25),linewidths=.18))
    low=mesh['xy'].min(axis=0); high=mesh['xy'].max(axis=0)
    center=(low+high)/2; half=max(high-low)*.58
    for ax in axes[:2]:
        ax.set_xlim(center[0]-half,center[0]+half); ax.set_ylim(center[1]-half,center[1]+half)
        ax.set_aspect('equal')
        ax.set_xlabel('x / L'); ax.set_ylabel('y / L')
        for values,axis in [(ax.get_xlim(),ax.xaxis),(ax.get_ylim(),ax.yaxis)]:
            ticks=np.arange(np.ceil(values[0]),np.floor(values[1])+1)
            axis.set_major_locator(FixedLocator(ticks))
    anchors=mesh['anchors']
    axes[0].plot(*anchors[0],marker='s',color='#BA3E34',ms=7)
    axes[0].plot(*anchors[1],marker='^',color='#BA3E34',ms=7)
    for offset,label in [(0,'A'),(1,'B')]:
        axes[0].annotate(label,anchors[offset],xytext=(5,8),textcoords='offset points',fontsize=14)
    worst=triangles[report['worst_cell']].mean(axis=0)
    axes[1].plot(*worst,'o',mfc='none',mec='#681C19',ms=10,mew=1.3)
    for layer,color,label in zip([1,2,3],colors,['Endo (assumed)','ECM (assumed)','Myo (assumed)']):
        values=np.sort(minimum[mesh['labels']==layer])
        axes[2].plot(values,np.arange(1,len(values)+1)/len(values)*100,color=color,lw=1.5,label=label)
    axes[2].axvline(20,color='#BA3E34',ls='--',lw=1.5)
    axes[2].set(xlim=(0,65),ylim=(0,105),xlabel='Minimum angle (degrees)',ylabel='Cumulative elements (%)')
    axes[2].xaxis.set_major_locator(FixedLocator([0,20,40,60]))
    axes[2].yaxis.set_major_locator(FixedLocator([0,25,50,75,100]))
    # Region colors are identified in the footer, avoiding threshold/legend overlap.
    for ax,title in zip(axes,['Constructed three-layer mesh','45 / 1828 cells below 20 deg','Element-quality distribution']):
        style_module.apply_axes_style(ax,style=style)
        style_module.add_top_information(ax,title,style=style)
    fig.text(.055,.92,'F6-S1 geometry gate FAILED | 0 equilibrium solves | retained image-derived outer contour',fontsize=16)
    fig.text(.055,.17,'A: ux = uy = 0; B: uy = 0. Intended inner pressure: p / mu = 0 ... 0.08; outer wall free.',fontsize=13)
    fig.text(.055,.105,'Green / yellow / blue: assumed endocardium / ECM / myocardium. Red mesh: minimum angle below 20 degrees.',fontsize=13)
    fig.text(.055,.045,'Geometry only: no displacement, stress, pressure response or physiological time has been computed.',fontsize=13)
    exported=style_module.export_figure(fig,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    if Path(exported.svg)!=Path(svg_path):
        Path(exported.svg).replace(svg_path)
        manifest=json.loads(Path(exported.manifest).read_text(encoding='utf-8'))
        manifest['exports']['svg']=str(Path(svg_path).resolve())
        Path(exported.manifest).write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    plt.close(fig)
    return report


def draw_mesh_repair(data_paths,candidates_path,png_path,svg_path,style_module,
                     axis_box_size_in=(3.7,3.7),figure_size_in=(16.8,7.4)):
    """Compare retained meshes and planned storage; never generate a new mesh."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.ticker import FixedLocator

    meshes=[]
    for path in data_paths:
        with np.load(path,allow_pickle=False) as archive:
            meshes.append({key:archive[key] for key in archive.files})
    records=json.loads(Path(candidates_path).read_text(encoding='utf-8'))
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=16.,axis_label_size=18.,annotation_font_size=16.,sample_size_and_stat_font_size=14.,
        legend_font_size=14.,axes_line_width=1.5,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    default=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=key,reason='Established compact FEM engineering panels; spatial aspect equal, no biological groups.')
               for key,value in asdict(style).items() if value!=default[key]]
    fig=plt.figure(figsize=figure_size_in)
    side=axis_box_size_in[0]
    axes=[fig.add_axes((x/figure_size_in[0],2.3/figure_size_in[1],side/figure_size_in[0],side/figure_size_in[1])) for x in [1.05,6.15,11.25]]
    mesh=meshes[1]  # Smallest quality-qualified candidate, NOT storage-admitted.
    colors=np.array(['#4C9F70','#D6B656','#5B8DB8'])
    axes[0].add_collection(PolyCollection(mesh['xy'][mesh['triangles']],facecolors=colors[mesh['labels']-1],edgecolors=(.1,.1,.1,.3),linewidths=.18))
    low=mesh['xy'].min(axis=0); high=mesh['xy'].max(axis=0)
    center=(low+high)/2; half=max(high-low)*.58
    axes[0].set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),xlabel='x / L',ylabel='y / L')
    axes[0].set_aspect('equal')
    for values,axis in [(axes[0].get_xlim(),axes[0].xaxis),(axes[0].get_ylim(),axes[0].yaxis)]:
        axis.set_major_locator(FixedLocator(np.arange(np.ceil(values[0]),np.floor(values[1])+1)))
    for anchor,marker,label in zip(mesh['anchors'],['s','^'],['A','B']):
        axes[0].plot(*anchor,marker=marker,color='#BA3E34',ms=7)
        axes[0].annotate(label,anchor,xytext=(5,8),textcoords='offset points',fontsize=14)
    palette=['#777777','#4C9F70','#5B8DB8','#BA7034']
    labels=['Previous']+[f'c = {r["factor"]:g}' for r in records]
    reports=[]
    for item,color,label in zip(meshes,palette,labels):
        angles,report=diagnose(item); reports.append(report)
        axes[1].plot(np.sort(angles),np.arange(1,len(angles)+1)*100/len(angles),color=color,lw=1.5,label=label)
    axes[1].axvline(20,color='#BA3E34',ls='--',lw=1.5)
    axes[1].set(xlim=(0,65),ylim=(0,105),xlabel='Minimum angle (degrees)',ylabel='Cumulative elements (%)')
    axes[1].xaxis.set_major_locator(FixedLocator([0,20,40,60]))
    axes[1].yaxis.set_major_locator(FixedLocator([0,25,50,75,100]))
    axes[1].legend(loc='upper left',fontsize=14,frameon=True,facecolor='white',edgecolor='none',framealpha=1.)
    sizes=np.array([r['predicted_bytes'] for r in records])/1024**2
    for i,(size,color) in enumerate(zip(sizes,palette[1:])):
        axes[2].plot(i,size,'o',color=color,ms=8)
        axes[2].annotate(f'{size:.1f}',(i,size),xytext=(0,10),textcoords='offset points',ha='center',fontsize=14)
    axes[2].axhline(256,color='#BA3E34',ls='--',lw=1.5)
    axes[2].text(1.9,232,'256 MiB cap',ha='right',fontsize=14,color='#BA3E34')
    axes[2].set(xlim=(-.5,2.5),ylim=(0,650),xlabel='Mesh-size factor c',ylabel='Forecast stage output (MiB)')
    axes[2].xaxis.set_major_locator(FixedLocator([0,1,2]))
    axes[2].set_xticklabels([f'{r["factor"]:g}' for r in records])
    axes[2].yaxis.set_major_locator(FixedLocator([0,200,400,600]))
    for ax,title in zip(axes,[f'Smallest valid mesh: {len(mesh["triangles"])} cells','All three pass the 20 deg gate','Storage forecast exceeds cap']):
        style_module.apply_axes_style(ax,style=style)
        style_module.add_top_information(ax,title,style=style)
    fig.text(.055,.92,'F6-S1-M: geometry PASSED; storage admission BLOCKED; 0 equilibrium solves',fontsize=16)
    fig.text(.055,.17,'Green / yellow / blue regions: assumed endocardium / ECM / myocardium. Outer contour unchanged.',fontsize=13)
    fig.text(.055,.105,'Planned: A fixes ux, uy; B fixes uy; inner pressure p / mu = 0 ... 0.08; outer wall free.',fontsize=13)
    fig.text(.055,.045,'Forecast includes two mesh levels, 10 states and 48 MiB overhead; it is NOT measured file size or RAM.',fontsize=13)
    exported=style_module.export_figure(fig,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    if Path(exported.svg)!=Path(svg_path):
        Path(exported.svg).replace(svg_path)
        manifest=json.loads(Path(exported.manifest).read_text(encoding='utf-8'))
        manifest['exports']['svg']=str(Path(svg_path).resolve())
        Path(exported.manifest).write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    plt.close(fig)
    return {'mesh_reports':reports,'forecast_MiB':sizes.tolist(),'equilibrium_solves':0}


def render_contour(root):
    """Re-execute an unfrozen local Notebook; never launch a FEM calculation."""
    import os
    import nbformat
    from nbclient import NotebookClient

    root=Path(root)
    pattern='FigS1M_mesh_repair/FigS1M_mesh_repair_v*/03_*_plot.ipynb' if (root/'mesh_candidates.json').exists() else 'FigS1_mesh_gate/FigS1_mesh_gate_v*/03_*_plot.ipynb'
    candidates=list((root/'figures').glob(pattern))
    if len(candidates)!=1:
        raise RuntimeError('Initialize the frozen figure package first; no silent version creation')
    notebook_path=candidates[0]
    methods=next(notebook_path.parent.glob('02_*_methods.txt'))
    if '包状态: 最终包' in methods.read_text(encoding='utf-8'):
        return {'status':'blocked','reason':'Figure revision is frozen; create an explicitly scoped visual revision first',
                'notebook':str(notebook_path),'scientific_solves':0}
    runtime=(root/'figure_runtime').resolve()
    if not (runtime/'README.md').exists():
        raise RuntimeError('Project-local runtime ownership record required')
    keys={'JUPYTER_RUNTIME_DIR':runtime/'jupyter','IPYTHONDIR':runtime/'ipython',
          'JUPYTER_CONFIG_DIR':runtime/'config','MPLCONFIGDIR':runtime/'matplotlib','TEMP':runtime,'TMP':runtime}
    original={key:os.environ.get(key) for key in keys}
    try:
        os.environ.update({key:str(value) for key,value in keys.items()})
        notebook=nbformat.read(notebook_path,as_version=4)
        NotebookClient(notebook,timeout=180,kernel_name='python3').execute(cwd=str(notebook_path.parent.resolve()))
        nbformat.write(notebook,notebook_path)
    finally:
        for key,value in original.items():
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key]=value
    return {'status':'passed','notebook':str(notebook_path),'scientific_solves':0,
            'visual_acceptance':'not_run','note':'Revalidate methods hashes and inspect the new PNG before acceptance'}
