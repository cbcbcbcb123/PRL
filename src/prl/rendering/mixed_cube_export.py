"""Actual initial mesh and per-cell export errors; no simulated solution."""
from dataclasses import asdict
from pathlib import Path
import json
import numpy as np


def draw_export_diagnosis(report, arrays, style_module, output_png, output_svg,
                          axis_box_size_in=(5., 5.), export_dpi=160):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    output_png, output_svg = Path(output_png), Path(output_svg)
    style = style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=14., axis_label_size=17., annotation_font_size=14.,
        sample_size_and_stat_font_size=14., legend_font_size=12., axes_line_width=1.4,
        major_tick_length_pt=5., major_tick_width_pt=1., minor_tick_length_pt=3.,
        minor_tick_width_pt=.8, data_line_width=1.5, tick_label_pad_pt=4.,
        axis_label_pad_pt=8., export_dpi=export_dpi)
    defaults = asdict(style_module.DEFAULT_STYLE)
    overrides = [style_module.StyleOverride(field=key,
        reason='Existing compact 160dpi exploration specification; export-interface diagnostic, not publication final.')
        for key, value in asdict(style).items() if value != defaults[key]]
    width, height = 15., 8.4
    figure = plt.figure(figsize=(width, height))
    axes = [figure.add_axes([x/width, 2./height, axis_box_size_in[0]/width,
                             axis_box_size_in[1]/height]) for x in (1.25, 8.4)]
    view = np.array([-1.8, -2.4, 1.6]); view /= np.linalg.norm(view)
    horizontal = np.cross([0., 0., 1.], view); horizontal /= np.linalg.norm(horizontal)
    projection = np.stack((horizontal, np.cross(view, horizontal)), axis=1)
    triangles = arrays['coordinates'][arrays['boundary_faces'][:, :3]]
    order = np.argsort(triangles.mean(axis=1) @ view)
    colors = np.array(['#CE817A' if tag == 1 else '#9CC5D5' for tag in arrays['boundary_tags']])
    axes[0].add_collection(PolyCollection((triangles @ projection)[order], facecolors=colors[order],
                                         edgecolors='#324B54', linewidths=.6))
    xy = arrays['coordinates'] @ projection; center = (xy.min(0) + xy.max(0))/2
    axes[0].set(xlim=(center[0]-1., center[0]+1.), ylim=(center[1]-1., center[1]+1.),
                aspect='equal', xlabel='Projected X / L', ylabel='Projected height / L')
    for key, label, color, marker in [('mismatch_before', 'Original export', '#B54742', 'o'),
                                     ('mismatch_after', 'Offline corrected map', '#207052', 'x')]:
        axes[1].scatter(arrays['cell_index'], arrays[key], label=label, color=color,
                        marker=marker, s=22, linewidths=1)
    axes[1].set(xlim=(-2, 50), ylim=(-.015, .24), xlabel='Native cell index',
                ylabel='Maximum nodal-coordinate mismatch / L')
    axes[1].legend(loc='upper right')
    for axis, title in zip(axes, ['A  Actual n=2 reference mesh\n48 tetrahedra; no solved state',
                                 'B  Independent export audit\n22 of 48 cell maps affected']):
        style_module.apply_axes_style(axis, style=style)
        style_module.add_top_information(axis, title, style=style)
    figure.text(.083, .145, 'A: X=0 exact displacement (red); other faces exact reference traction, with compatible body force.', fontsize=12)
    figure.text(.083, .105, 'B: same saved coordinates; only the exported P3 local index map is reordered. No nodes or geometry moved.', fontsize=12)
    figure.text(.083, .065, 'Batch stopped before SNES: 1 container, 0 solves, 0 retries. Corrected native assembly is NOT RUN.', fontsize=12)
    exported = style_module.export_figure(figure, axes, output_png.with_suffix(''), style=style, overrides=overrides)
    exported.svg.replace(output_svg)
    manifest = json.loads(exported.manifest.read_text(encoding='utf-8'))
    manifest['exports']['svg'] = str(output_svg.resolve())
    exported.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    plt.close(figure)
    return {'png':str(exported.png), 'svg':str(output_svg), 'manifest':str(exported.manifest)}
