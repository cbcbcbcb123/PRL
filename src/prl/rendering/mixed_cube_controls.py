"""Portable render-only control page from copied persisted-state data."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def draw_controls(report, arrays, style_module, output_png, output_svg,
                  axis_box_size_in=(4.,4.), deformation_scale=30., export_dpi=160):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    output_png,output_svg=Path(output_png),Path(output_svg)
    if output_png.parent != output_svg.parent:
        raise ValueError('PNG and SVG must belong to the same figure package')
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=14.,axis_label_size=17.,annotation_font_size=14.,
        sample_size_and_stat_font_size=14.,legend_font_size=12.,axes_line_width=1.4,
        major_tick_length_pt=5.,major_tick_width_pt=1.,minor_tick_length_pt=3.,
        minor_tick_width_pt=.8,data_line_width=1.5,tick_label_pad_pt=4.,
        axis_label_pad_pt=8.,export_dpi=export_dpi)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=key,
        reason='Approved compact exploratory control page; true saved states, 160dpi preview, not publication final.')
        for key,value in asdict(style).items() if value!=defaults[key]]
    width,height=20.,13.6
    figure=plt.figure(figsize=(width,height))
    positions=[(x,y) for y in [7.9,2.5] for x in [1.25,7.5,13.75]]
    axes=[figure.add_axes([x/width,y/height,axis_box_size_in[0]/width,axis_box_size_in[1]/height]) for x,y in positions]
    view=np.array([-1.8,-2.4,1.6]); view/=np.linalg.norm(view)
    horizontal=np.cross([0.,0.,1.],view); horizontal/=np.linalg.norm(horizontal)
    projection=np.stack([horizontal,np.cross(view,horizontal)],axis=1)

    def surface(axis, label, displacement, colors):
        coordinates=arrays[f'{label}_coordinates']
        faces=arrays[f'{label}_boundary_faces'][:,:3]
        current=coordinates+deformation_scale*displacement
        triangles=current[faces]; order=np.argsort(triangles.mean(axis=1)@view)
        axis.add_collection(PolyCollection((triangles@projection)[order],
            facecolors=colors[order],edgecolors='#324B54',linewidths=.25 if label=='fine' else .6))
        xy=coordinates@projection; center=(xy.max(axis=0)+xy.min(axis=0))/2
        axis.set(xlim=(center[0]-1.,center[0]+1.),ylim=(center[1]-1.,center[1]+1.),
            aspect='equal',xlabel='Projected X / L',ylabel='Projected height / L')

    tags=arrays['patch_boundary_tags']
    colors=np.array(['#CE817A' if tag==1 else '#9CC5D5' for tag in tags])
    surface(axes[0],'patch',np.zeros_like(arrays['patch_coordinates']),colors)
    rows=[row for row in report['cases'] if row['kind']=='isochoric_mms' and 'metrics' in row]
    for label,key,gate,color,marker in [
        ('u L2','relative_u_L2','fine_relative_u_L2','#207052','o'),
        ('u H1','relative_u_H1','fine_relative_u_H1','#AC6D25','s'),
        ('J RMS','J_error_RMS','fine_J_error_RMS','#397DA6','^')]:
        axes[1].plot([row['n'] for row in rows],
            [row['metrics'][key]/report['config']['mms_gates'][gate] for row in rows],
            marker=marker,color=color,lw=1.5,ms=5,label=label)
    axes[1].axhline(1.,color='#666666',ls='--',lw=1)
    axes[1].set(xscale='log',yscale='log',xlim=(1.7,9.5),ylim=(.002,10),
        xlabel='Grid divisions n (2, 4, 8)',ylabel='Error / fine-grid limit')
    axes[1].set_xticks([2,4,8],['2','4','8']); axes[1].legend(loc='upper right')
    patch_last=int(arrays['patch_iterations'][-1])
    pressure_norm=Normalize(0.,4.)
    surface(axes[2],'patch',arrays[f'patch_u_{patch_last}'],
        plt.colormaps['viridis'](pressure_norm(arrays['patch_terminal_face_pressure'])))
    color_axis=figure.add_axes([18.15/width,7.9/height,.16/width,4./height])
    color_bar=figure.colorbar(matplotlib.cm.ScalarMappable(norm=pressure_norm,cmap='viridis'),cax=color_axis)
    color_bar.set_label('Numerical face-mean p / mu',fontsize=14,labelpad=8)
    color_bar.ax.tick_params(labelsize=12)
    iterations=arrays['fine_iterations'].tolist()
    if len(iterations)!=3:
        raise ValueError('Page expects three actual saved states; do not synthesize extra states')
    history=report['iterate_diagnostics']['isochoric_k1000_n8']
    displacement_norm=Normalize(0.,.002)
    titles=['A  Actual n=2 reference mesh\n48 tetrahedra; boundary tags',
        'B  Three-mesh shear control\nDashed line: fine-grid limit',
        'C  Nonuniform volume patch\nNumerical pressure; deformation x30']
    for axis,index,entry in zip(axes[3:],iterations,history):
        u=arrays[f'fine_u_{index}']; faces=arrays['fine_boundary_faces'][:,:3]
        face_u=u[faces,0].mean(axis=1)
        surface(axis,'fine',u,plt.colormaps['viridis'](displacement_norm(face_u)))
        titles.append(f'{chr(68+index)}  n=8: Newton iteration {index}\nResidual = {entry["residual"]:.2e}')
    color_axis2=figure.add_axes([18.15/width,2.5/height,.16/width,4./height])
    color_bar2=figure.colorbar(matplotlib.cm.ScalarMappable(norm=displacement_norm,cmap='viridis'),cax=color_axis2)
    color_bar2.set_label('Numerical face-mean u_x / L',fontsize=14,labelpad=8)
    color_bar2.ax.tick_params(labelsize=12)
    for axis,title in zip(axes,titles):
        style_module.apply_axes_style(axis,style=style)
        style_module.add_top_information(axis,title,style=style)
    figure.text(.065,.975,'Four diagnostic controls pass their defined gates; original ventricular qualification remains FAILED.',fontsize=15)
    figure.text(.065,.129,'A: red X=0 exact displacement; other faces exact reference traction. Compatible analytic body forces are included.',fontsize=12)
    figure.text(.065,.099,'B: mu=1, kappa=1000, unchanged P2/P1 and gates. Exact shear pressure is zero: relative pressure error is undefined.',fontsize=12)
    figure.text(.065,.069,'C-F: geometry displacement magnified 30x; colors show unscaled face-mean numerical fields, not exact-field substitutes.',fontsize=12)
    figure.text(.065,.039,'D-F: all three real saved finest-mesh Newton states. Algorithm iterations, NOT physiological time; 160dpi exploratory page.',fontsize=12)
    exported=style_module.export_figure(figure,axes,output_png.with_suffix(''),style=style,overrides=overrides)
    # Match the figure workflow's distinct 04 PNG / 05 SVG naming inside this working package.
    exported.svg.replace(output_svg)
    manifest=json.loads(exported.manifest.read_text(encoding='utf-8'))
    manifest['exports']['svg']=str(output_svg.resolve())
    exported.manifest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    plt.close(figure)
    return {'png':str(exported.png),'svg':str(output_svg),'manifest':str(exported.manifest)}
