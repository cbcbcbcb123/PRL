"""One lightweight, reproducible exploratory page from saved-state diagnostics."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def draw(root, style_module, geometry):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import to_rgba
    root = Path(root)
    with np.load(root/'derived_cells.npz', allow_pickle=False) as payload:
        arrays = {k:payload[k] for k in payload.files}
    report = json.loads((root/'summary.json').read_text(encoding='utf-8'))
    values = {name:item['projection'] for name,item in report['states'].items()}
    colors = {'M0':'#207052', 'M1':'#397DA6'}
    style = style_module.StyleSpec(axis_box_size_in=(3.6,3.6), tick_label_size=14., axis_label_size=17.,
        annotation_font_size=14., sample_size_and_stat_font_size=14., legend_font_size=12.,
        axes_line_width=1.4, major_tick_length_pt=5., major_tick_width_pt=1.,
        minor_tick_length_pt=3., minor_tick_width_pt=.8, data_line_width=1.5,
        tick_label_pad_pt=4., axis_label_pad_pt=8., export_dpi=160)
    defaults = asdict(style_module.DEFAULT_STYLE)
    overrides = [style_module.StyleOverride(field=key,
        reason='Exploratory diagnostic page per accepted expert workflow; compact existing FEM axes, 160dpi not publication final.')
        for key,value in asdict(style).items() if value != defaults[key]]
    width,height = 13.8,13.4
    figure = plt.figure(figsize=(width,height))
    axes = [figure.add_axes((x/width,y/height,3.6/width,3.6/height))
            for x,y in [(1.25,7.9),(8.0,7.9),(1.25,2.7),(8.0,2.7)]]
    mesh = {key:arrays['M1_'+key] for key in ['coordinates','cells','layers']}
    faces, owners = geometry.boundary_faces(mesh)
    triangles = np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    view = np.array([1.8,-2.4,1.6]); view /= np.linalg.norm(view)
    horizontal = np.cross([0.,0.,1.],view); horizontal /= np.linalg.norm(horizontal)
    projection = np.stack([horizontal,np.cross(view,horizontal)],axis=1)
    surface = mesh['coordinates'][faces[:,triangles]].reshape(-1,3,3)
    order = np.argsort(surface.mean(axis=1)@view)
    poly = surface@projection
    center = (poly.reshape(-1,2).max(axis=0)+poly.reshape(-1,2).min(axis=0))/2
    half = np.ptp(poly.reshape(-1,2),axis=0).max()*.60
    palette = np.array([to_rgba(c) for c in ['#4C9F70','#D6B656','#5B8DB8']])
    rgba = np.repeat(palette[mesh['layers'][owners]-1],4,axis=0)
    axes[0].add_collection(PolyCollection(poly[order],facecolors=rgba[order],edgecolors=(.1,.2,.3,.3),linewidths=.12))
    base = (abs(mesh['coordinates'][:,2])<1e-12)&(mesh['coordinates'][:,1]>=0)
    axes[0].plot(*(mesh['coordinates'][base]@projection).T,'.',color='#B63E35',ms=2)
    axes[0].set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),
        xlabel='Projected x / L',ylabel='Projected height / L',xticks=[-1,0,1],yticks=[-1,0,1],aspect='equal')
    for name in ['M0','M1']:
        axes[1].scatter(arrays[name+'_cell_peak_distance'],arrays[name+'_cell_max_abs_J_minus_one']*100,
            c=colors[name],s=7,marker='o' if name=='M0' else 'x',alpha=.50,linewidths=.6,rasterized=True)
    axes[1].axhline(1.,color='#B13B38',lw=1.3,ls='--')
    for edge in [.15,.30,.45]:
        axes[1].axvline(edge,color='#777777',lw=.8,ls=':')
    axes[1].set(xlim=(0,1.5),ylim=(0,1.65),xticks=[0,.3,.6,.9,1.2,1.5],
        xlabel='Distance of cell peak from base / L',ylabel='Cell sampled max |J - 1| (%)')
    for name in ['M0','M1']:
        rms = [values[name]['regions']['all/band_'+str(i)]['projection_defect']['rms']*100 for i in range(4)]
        axes[2].plot(range(4),rms,'o-' if name=='M0' else 's--',color=colors[name],lw=1.5,ms=5)
    axes[2].set(xlim=(-.35,3.35),ylim=(0,None),xlabel='Fixed physical distance bands / L',
        ylabel='Volume-weighted RMS of r (%)')
    axes[2].set_xticks(range(4),['0–.15','.15–.30','.30–.45','≥.45'])
    for offset,name in [(-.09,'M0'),(.09,'M1')]:
        item = values[name]
        magnitudes = [item['max_abs_J_minus_one'],item['max_abs_p_over_kappa_at_q_and_extra'],
                      item['rms_J_minus_one'],item['rms_projection_defect']]
        axes[3].plot(np.arange(4)+offset,np.array(magnitudes)*100,'o' if name=='M0' else 's',
            color=colors[name],ms=6,label=name)
    axes[3].set(xlim=(-.5,3.5),yscale='log',ylim=(.0005,3.),xlabel='Global magnitude diagnostic',ylabel='Dimensionless magnitude (%)')
    axes[3].set_xticks(range(4),['max\n|J−1|','max\n|p/κ|','RMS\n(J−1)','RMS\nr'])
    axes[3].legend(loc='upper right')
    for axis,title in zip(axes,['A  Actual M1 reference structure','B  All cells; original 1% line',
                               'C  Same distance bands in both meshes','D  Local defect vs material scale']):
        style_module.apply_axes_style(axis,style=style)
        style_module.add_top_information(axis,title,style=style)
    figure.text(.075,.96,'Saved-state diagnosis only: r = J - 1 - p_m / kappa; no new FEM solves.',fontsize=14)
    figure.text(.075,.922,f"M0: {values['M0']['tetrahedra']} cells (green circles); M1: {values['M1']['tetrahedra']} (blue squares/crosses). Both original gates FAILED.",fontsize=12)
    figure.text(.075,.102,'A: endo green / ECM yellow / myo blue; fixed base red. Cutaway is display-only; outer wall free.',fontsize=11)
    figure.text(.075,.074,'B: peak coordinate for each cell, not a centroid. C: quadrature-weighted band integrals; no data excluded.',fontsize=11)
    figure.text(.075,.046,'p_lumen/mu=0.01, Ta=0, kappa/mu=1000. Not pure h-convergence, biological time, or an instability proof.',fontsize=11)
    exports = style_module.export_figure(figure,axes,root/'diagnostic',style=style,overrides=overrides)
    plt.close(figure)
    return {'png':str(exports.png),'svg':str(exports.svg),'manifest':str(exports.manifest)}


if __name__ == '__main__':
    import argparse
    import importlib.util
    import os
    import sys
    sys.dont_write_bytecode=True
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    args=parser.parse_args()
    os.environ['MPLCONFIGDIR']=str(args.root/'.plot_cache')
    def load(name, path):
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec); sys.modules[name]=module
        spec.loader.exec_module(module)
        return module
    print(draw(args.root,load('snapshot_style',args.root/'sources/style.py'),
               load('snapshot_geometry',args.root/'sources/geometry_view.py')))
