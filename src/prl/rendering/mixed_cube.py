"""Actual reference mesh and execution accounting; no unsolved mechanical fields."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def draw(root, style_module):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    root=Path(root)
    with np.load(root/'raw/patch_affine_mesh.npz',allow_pickle=False) as data:
        coordinates=data['coordinates']; faces=data['boundary_faces']; tags=data['boundary_tags']
    report=json.loads((root/'delivery_interpretation.json').read_text(encoding='utf-8'))
    style=style_module.StyleSpec(axis_box_size_in=(4.2,4.2),tick_label_size=14.,axis_label_size=17.,
        annotation_font_size=14.,sample_size_and_stat_font_size=14.,legend_font_size=12.,
        axes_line_width=1.4,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,
        tick_label_pad_pt=4.,axis_label_pad_pt=8.,export_dpi=160)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=key,
        reason='Approved exploratory engineering page, 160dpi; actual mesh and execution counts, not publication results.')
        for key,value in asdict(style).items() if value!=defaults[key]]
    width,height=13.8,7.7
    figure=plt.figure(figsize=(width,height))
    left=figure.add_axes([1.1/width,2.1/height,4.2/width,4.2/height])
    right=figure.add_axes([8.0/width,2.1/height,4.2/width,4.2/height])
    view=np.array([-1.8,-2.4,1.6]); view/=np.linalg.norm(view)
    horizontal=np.cross([0.,0.,1.],view); horizontal/=np.linalg.norm(horizontal)
    projection=np.stack([horizontal,np.cross(view,horizontal)],axis=1)
    surface=coordinates[faces[:,:3]]
    order=np.argsort(surface.mean(axis=1)@view)
    colors=np.array(['#CE817A' if tag==1 else '#9CC5D5' for tag in tags])
    left.add_collection(PolyCollection((surface@projection)[order],facecolors=colors[order],
        edgecolors='#2F4B52',linewidths=.6))
    xy=coordinates@projection; center=(xy.max(axis=0)+xy.min(axis=0))/2
    left.set(xlim=(center[0]-.95,center[0]+.95),ylim=(center[1]-.95,center[1]+.95),
        aspect='equal',xlabel='Projected X / L',ylabel='Projected height / L')
    values=[8,1,report['SNES_calls'],report['evaluated_equilibrium_states']]
    right.bar(range(4),values,color=['#86AEBB','#D49567','#A0A0A0','#A0A0A0'],width=.62)
    right.set(xlim=(-.6,3.6),ylim=(0,9.5),yticks=[0,2,4,6,8],
        xlabel='Authorized scope vs actual execution',ylabel='Count')
    right.set_xticks(range(4),['Planned\ncases','Built\nmeshes','SNES\ncalls','Solved\nstates'])
    for index,value in enumerate(values):
        right.text(index,value+.25,str(value),ha='center',va='bottom')
    for axis,title in [(left,'A  Actual n=2 reference mesh: 48 tetrahedra'),
                       (right,'B  Interface failed before first solve')]:
        style_module.apply_axes_style(axis,style=style)
        style_module.add_top_information(axis,title,style=style)
    figure.text(.08,.955,'Engineering stop: all eight equilibrium cases NOT_RUN; no material verdict.',fontsize=15)
    figure.text(.08,.14,'A: red X=0 prescribed-displacement face; blue faces carry analytical reference traction.',fontsize=12)
    figure.text(.08,.095,'Saved failure vector is an interpolated precheck, NOT an equilibrium or a contraction state.',fontsize=12)
    figure.text(.08,.05,'One container, one CPU, zero GPU, zero retries. Structure and execution evidence only; 160 dpi.',fontsize=12)
    exports=style_module.export_figure(figure,[left,right],root/'diagnostic',style=style,overrides=overrides)
    plt.close(figure)
    return {'png':str(exports.png),'svg':str(exports.svg),'manifest':str(exports.manifest)}


def draw_batch(root,style_module):
    """A native mesh, actual error sequence, and saved Newton/safety diagnostics."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    root=Path(root)
    report=json.loads((root/'delivery_analysis.json').read_text())
    config=json.loads((root/'configuration.json').read_text())
    guarded='path_audit_status' in report
    with np.load(root/'raw/patch_affine_mesh.npz',allow_pickle=False) as data:
        coordinates=data['coordinates']; faces=data['boundary_faces']; tags=data['boundary_tags']
    with np.load(root/'delivery_arrays.npz',allow_pickle=False) as data:
        arrays={key:data[key] for key in data.files}
    style=style_module.StyleSpec(axis_box_size_in=(3.6,3.6),tick_label_size=14.,axis_label_size=17.,
        annotation_font_size=14.,sample_size_and_stat_font_size=14.,legend_font_size=12.,
        axes_line_width=1.4,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,
        tick_label_pad_pt=4.,axis_label_pad_pt=8.,export_dpi=160)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=key,
        reason='Approved compact exploratory benchmark page; 160dpi, actual states and error data; not publication final.')
        for key,value in asdict(style).items() if value!=defaults[key]]
    width,height=14.2,13.4
    figure=plt.figure(figsize=(width,height))
    axes=[figure.add_axes([x/width,y/height,3.6/width,3.6/height]) for x,y in [(1.25,7.9),(8.6,7.9),(1.25,2.7),(8.6,2.7)]]
    view=np.array([-1.8,-2.4,1.6]); view/=np.linalg.norm(view)
    horizontal=np.cross([0.,0.,1.],view); horizontal/=np.linalg.norm(horizontal)
    projection=np.stack([horizontal,np.cross(view,horizontal)],axis=1)
    surface=coordinates[faces[:,:3]]; order=np.argsort(surface.mean(axis=1)@view)
    colors=np.array(['#CE817A' if tag==1 else '#9CC5D5' for tag in tags])
    axes[0].add_collection(PolyCollection((surface@projection)[order],facecolors=colors[order],
        edgecolors='#2F4B52',linewidths=.6))
    xy=coordinates@projection; center=(xy.max(axis=0)+xy.min(axis=0))/2
    axes[0].set(xlim=(center[0]-.95,center[0]+.95),ylim=(center[1]-.95,center[1]+.95),
        aspect='equal',xlabel='Projected X / L',ylabel='Projected height / L')
    rows=[row for row in report['cases'] if row['kind']=='mms' and row['kappa']==100 and 'metrics' in row]
    for label,metric,gate,color,marker in [
        ('u L2','relative_u_L2','fine_relative_u_L2','#207052','o'),
        ('u H1','relative_u_H1','fine_relative_u_H1','#AC6D25','s'),
        ('p L2','relative_pressure_L2','fine_relative_pressure_L2','#397DA6','^'),
        ('J RMS','J_error_RMS','fine_J_error_RMS','#A44850','D')]:
        axes[1].plot([row['n'] for row in rows],[row['metrics'][metric]/config['mms_gates'][gate] for row in rows],
            marker=marker,color=color,ms=5,lw=1.5,label=label)
    axes[1].axhline(1.,color='#555555',ls='--',lw=1.)
    axes[1].set(xscale='log',yscale='log',xlim=(1.7,9.5),ylim=(.07,2000),
        xlabel='Grid divisions n (2, 4, 8)',ylabel='Error / fine-grid limit')
    axes[1].set_xticks([2,4,8],['2','4','8']); axes[1].legend(loc='upper right')
    if guarded:
        history=report['iterate_diagnostics']['mms_k1000_n2']
        axes[2].plot([x['iteration'] for x in history],[x['minimum_sampled_J'] for x in history],'o-',color='#207052',lw=1.5)
        last=history[-1]['iteration']
        axes[2].set(yscale='log',xlim=(-.4,last+.4),ylim=(1e-8,2),xticks=[0,last//2,last],
            xlabel='Newton iteration (not time)',ylabel='Accepted minimum sampled J')
        precision=[item for item in report['precision'] if item['kappa']==100]
        for key,label,color,marker in [('finite_element','FEM equilibrium','#A44850','o'),
                ('interpolated_exact_field','Exact-field interpolant','#397DA6','s')]:
            axes[3].plot([item['n'] for item in precision],[item[key]['relative_u_H1'] for item in precision],
                marker=marker,color=color,ms=5,lw=1.5,label=label)
        axes[3].axhline(config['mms_gates']['fine_relative_u_H1'],color='#555555',ls='--',lw=1.)
        axes[3].set(xscale='log',yscale='log',xlim=(1.7,9.5),ylim=(.005,30),
            xlabel='Grid divisions n (2, 4, 8)',ylabel='Relative displacement H1 error')
        axes[3].set_xticks([2,4,8],['2','4','8']); axes[3].legend(loc='upper right')
        final_titles=['C  kappa=1000: positive, but collapsing','D  kappa=100: interpolation comparison']
    else:
        history=report['iterate_diagnostics']['mms_k100_n8']
        axes[2].plot([x['iteration'] for x in history],[x['residual'] for x in history],'o-',color='#207052',lw=1.5)
        axes[2].set(yscale='log',xlim=(-.2,3.2),ylim=(1e-16,1),xticks=[0,1,2,3],
            xlabel='Newton iteration (not time)',ylabel='Native SNES residual norm')
        for label,color,marker in [('production','#397DA6','o'),('extra','#A44850','x')]:
            value=arrays[f'mms_k1000_n2_1_{label}_cell_minimum_J']
            axes[3].plot(np.arange(len(value)),value,marker=marker,ls='none',color=color,ms=4,label=label)
        axes[3].axhline(0,color='#555555',ls='--',lw=1.)
        axes[3].set(xlim=(-2,49),ylim=(-.3,1.35),xticks=[0,12,24,36,48],yticks=[-.25,0,.25,.5,.75,1.,1.25],
            xlabel='Tetrahedron index',ylabel='Cell minimum sampled J')
        axes[3].legend(loc='upper center')
        final_titles=['C  kappa=100, n=8: saved states','D  kappa=1000, n=2: STOP at step 1']
    for axis,title in zip(axes,['A  Actual n=2 cube, 48 tetrahedra','B  kappa=100: fine-grid limit = 1',*final_titles]):
        style_module.apply_axes_style(axis,style=style); style_module.add_top_information(axis,title,style=style)
    # Sixteen residual decades make Matplotlib's default minor locator empty.
    axes[2].yaxis.set_minor_locator(matplotlib.ticker.LogLocator(base=10,subs=[2,5],numticks=100))
    heading=('Positive-J admission works; high-kappa equilibrium and field accuracy still fail.' if guarded
        else 'Two patches pass; field accuracy and high-kappa safety do not. No automatic retries.')
    figure.text(.075,.963,heading,fontsize=14)
    figure.text(.075,.930,'Six attempted solves / five equilibria / two cases not run. Engineering consistency is not field qualification.',fontsize=12)
    figure.text(.075,.110,'A: red X=0 exact displacement; other faces exact reference traction. MMS also uses compatible body force.',fontsize=11)
    if guarded:
        figure.text(.075,.078,'B: v02 errors are unchanged. C: all 15 accepted states stay positive; next candidate is refused after 20 halvings.',fontsize=11)
        figure.text(.075,.046,'D: interpolation is neither equilibrium nor a best-error bound. No new mesh, relaxed gate, or ventricular solve.',fontsize=11)
    else:
        figure.text(.075,.078,'B: errors decrease, but three n=8 metrics remain above their gates. C: four real saved Newton states.',fontsize=11)
        figure.text(.075,.046,'D: production-point min J is positive; extra points detect six inverted cells. Failed iterate is not equilibrium.',fontsize=11)
    outputs=style_module.export_figure(figure,axes,root/'diagnostic',style=style,overrides=overrides)
    plt.close(figure)
    return {'png':str(outputs.png),'svg':str(outputs.svg),'manifest':str(outputs.manifest)}
