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
