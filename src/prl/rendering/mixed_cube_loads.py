"""One lightweight diagnostic page from saved-state force data; no synthetic solutions."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def draw(root, style):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    root = Path(root)
    report = json.loads((root / 'summary.json').read_text(encoding='utf-8'))
    source = Path(json.loads((root / 'sources.json').read_text(encoding='utf-8'))['source'])
    with np.load(source / 'raw/mms_k100_n2_mesh.npz', allow_pickle=False) as saved:
        coordinates, faces, tags = saved['coordinates'], saved['boundary_faces'], saved['boundary_tags']
    rows = report['rows']
    # 作图参数：沿用项目已采纳的160dpi探索版；非论文终稿，无生物学分组颜色。
    settings = style.StyleSpec(axis_box_size_in=(3.6, 3.6), tick_label_size=13., axis_label_size=16.,
        annotation_font_size=13., sample_size_and_stat_font_size=13., legend_font_size=11.,
        axes_line_width=1.4, major_tick_length_pt=5., major_tick_width_pt=1.,
        minor_tick_length_pt=3., minor_tick_width_pt=.8, data_line_width=1.5,
        tick_label_pad_pt=4., axis_label_pad_pt=8., export_dpi=160)
    defaults = asdict(style.DEFAULT_STYLE)
    overrides = [style.StyleOverride(field=key, reason='Approved lightweight exploratory diagnostic page; not a publication figure.')
                 for key, value in asdict(settings).items() if value != defaults[key]]
    width, height = 18.7, 6.8
    figure = plt.figure(figsize=(width, height))
    axes = [figure.add_axes([x / width, 2.0 / height, 3.6 / width, 3.6 / height]) for x in [1.2, 7.3, 13.7]]
    view = np.array([-1.8, -2.4, 1.6]); view /= np.linalg.norm(view)
    horizontal = np.cross([0., 0., 1.], view); horizontal /= np.linalg.norm(horizontal)
    projection = np.stack([horizontal, np.cross(view, horizontal)], axis=1)
    surface = coordinates[faces[:, :3]]; order = np.argsort(surface.mean(axis=1) @ view)
    colors = np.array(['#CE817A' if tag == 1 else '#9CC5D5' for tag in tags])
    axes[0].add_collection(PolyCollection((surface @ projection)[order], facecolors=colors[order],
                                       edgecolors='#2F4B52', linewidths=.6))
    projected = coordinates @ projection
    center = (projected.max(axis=0) + projected.min(axis=0)) / 2
    axes[0].set(xlim=(center[0] - .95, center[0] + .95), ylim=(center[1] - .95, center[1] + .95),
                aspect='equal', xlabel='Projected X / L', ylabel='Projected height / L')
    divisions = [row['n'] for row in rows]
    axes[1].plot(divisions, [row['leakage_to_iso_force_norm_ratio'] for row in rows],
                 'o-', color='#A44850', label='Unrepresented pressure / isochoric')
    axes[1].axhline(1, color='#555555', ls='--', lw=1.)
    axes[1].set(xscale='log', yscale='log', xlim=(1.7, 9.5), ylim=(.7, 25),
                xlabel='Grid divisions n', ylabel='Nodal force norm ratio')
    for key, label, color, marker in [('unrepresented', 'Pressure-force remainder', '#A44850', 'o'),
                                       ('integration', 'Production quadrature difference', '#397DA6', 's')]:
        values = [(row['pressure_certificate']['unrepresented_force_norm'] if key == 'unrepresented'
                   else row['production_load_difference']) / row['pressure_certificate']['pressure_force_norm']
                  for row in rows]
        axes[2].plot(divisions, values, marker=marker, color=color, label=label)
    axes[2].set(xscale='log', yscale='log', xlim=(1.7, 9.5), ylim=(1e-8, 1),
                xlabel='Grid divisions n', ylabel='Fraction of exact pressure-force norm')
    axes[2].legend(loc='upper right')
    for axis in axes[1:]:
        axis.set_xticks([2, 4, 8], ['2', '4', '8'])
    for axis, title in zip(axes, ['A  Saved n=2 mesh; 48 tetrahedra',
                                 'B  Pressure remainder is mechanically large',
                                 'C  Quadrature difference is much smaller']):
        style.apply_axes_style(axis, style=settings)
        style.add_top_information(axis, title, style=settings)
    # Only place ticks inside the visible domain; out-of-range log ticks otherwise
    # appear visible to the layout checker despite not belonging to the panel.
    for axis in axes[1:]:
        axis.xaxis.set_minor_locator(matplotlib.ticker.FixedLocator([3, 5, 6, 7, 9]))
        axis.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axes[1].set_yticks([1, 10])
    axes[1].yaxis.set_minor_locator(matplotlib.ticker.FixedLocator([.8, .9, 2, 3, 4, 5, 6, 7, 8, 9, 20]))
    axes[2].set_yticks([1e-8, 1e-6, 1e-4, 1e-2, 1])
    axes[2].yaxis.set_minor_locator(matplotlib.ticker.FixedLocator([factor * 10. ** exponent
        for exponent in range(-8, 0) for factor in [2, 5]]))
    for axis in axes[1:]:
        axis.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    figure.text(.06, .14, 'All three meshes: kappa/mu=100. Analysis uses saved equilibria and exact manufactured fields; ZERO new solves.', fontsize=12)
    figure.text(.06, .085, 'B/C: Euclidean nodal-force projection at exact F*. It is not an inf-sup proof, a new equilibrium, or a ventricular validation.', fontsize=12)
    figure.text(.06, .03, 'A: X=0 exact displacement (red); five faces carry exact traction. Original accuracy failures remain. Exploratory 160 dpi.', fontsize=12)
    output = style.export_figure(figure, axes, root / 'diagnostic', style=settings, overrides=overrides)
    plt.close(figure)
    return {'png': str(output.png), 'svg': str(output.svg), 'manifest': str(output.manifest)}
