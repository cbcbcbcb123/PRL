"""Portable retained-mesh quality figure, no synthesized state or FEM invocation."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def draw(data_path, png_path, svg_path, style_module, mechanics, geometry, quality, probe):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    data = mechanics.load_arrays(data_path)
    config = json.loads(str(data['configuration'].item()))
    meshes = {name: {k[8:]: v for k, v in data.items() if k.startswith('mesh_'+name+'_')} for name in ['M0', 'M1']}
    fields = {}
    for name, mesh in meshes.items():
        prefix = 'state_'+name+'_'
        state = {k[len(prefix):]: v for k, v in data.items() if k.startswith(prefix)}
        fields[name], _ = quality.analyze(mesh, state, config, mechanics, probe)
    style = style_module.StyleSpec(axis_box_size_in=(3.6, 3.6), tick_label_size=16., axis_label_size=18.,
        annotation_font_size=16., sample_size_and_stat_font_size=14., legend_font_size=14., axes_line_width=1.5,
        major_tick_length_pt=5., major_tick_width_pt=1., minor_tick_length_pt=3., minor_tick_width_pt=.8,
        data_line_width=1.5, tick_label_pad_pt=4., axis_label_pad_pt=8.)
    defaults = asdict(style_module.DEFAULT_STYLE)
    overrides = [style_module.StyleOverride(field=k, reason='Reuse approved compact FEM diagnostic style with equal-scale cutaways.')
                 for k, v in asdict(style).items() if v != defaults[k]]
    width, height = 19.8, 12.8
    figure = plt.figure(figsize=(width, height))
    axes = []
    view = np.array([1.8, -2.4, 1.6]); view /= np.linalg.norm(view)
    horizontal = np.cross([0., 0., 1.], view); horizontal /= np.linalg.norm(horizontal)
    projection = np.stack([horizontal, np.cross(view, horizontal)], axis=1)
    coordinates = np.concatenate([m['coordinates'] for m in meshes.values()]) @ projection
    center = (coordinates.min(axis=0)+coordinates.max(axis=0))/2
    half = np.ptp(coordinates, axis=0).max()*.57
    pieces = np.array([[0, 5, 4], [5, 1, 3], [4, 3, 2], [5, 3, 4]])
    normalizers = {'q_radius': Normalize(0, .6), 'max_abs_J_minus_one': Normalize(0, 1.6)}
    for row, name in enumerate(['M0', 'M1']):
        mesh = meshes[name]; values = fields[name]; y = 7.6 if row == 0 else 2.8
        faces, owners = geometry.boundary_faces(mesh)
        surface = mesh['coordinates'][faces[:, pieces]].reshape(-1, 3, 3)
        order = np.argsort(surface.mean(axis=1) @ view)
        for column, field in enumerate(['q_radius', 'max_abs_J_minus_one']):
            axis = figure.add_axes(([1.25, 7.35][column]/width, y/height, 3.6/width, 3.6/height)); axes.append(axis)
            axis.set(xlim=(center[0]-half, center[0]+half), ylim=(center[1]-half, center[1]+half),
                xticks=[-1, 0, 1], yticks=[-1, 0, 1], xlabel='Projected x / L', ylabel='Projected height / L', aspect='equal')
            title = chr(65+row*3+column)+'  '+name+(' reference: shape' if column == 0 else ' retained: volume')
            style_module.apply_axes_style(axis, style=style); style_module.add_top_information(axis, title, style=style)
            scalar = values[field]*(100 if column else 1.)
            artist = PolyCollection((surface @ projection)[order], array=np.repeat(scalar[owners], 4)[order],
                norm=normalizers[field], cmap='viridis' if column == 0 else 'magma', edgecolors=(.1, .15, .2, .4), linewidths=.12)
            axis.add_collection(artist)
            if column == 0:
                basal = (np.abs(mesh['coordinates'][:, 2]) < 1e-12) & (mesh['coordinates'][:, 1] >= 0)
                axis.plot(*(mesh['coordinates'][basal] @ projection).T, '.', color='#C23B37', ms=2)
            if row == 0:
                color_axis = figure.add_axes(([5.25, 11.35][column]/width, y/height, .2/width, 3.6/height))
                bar = figure.colorbar(artist, cax=color_axis)
                bar.set_label('Shape q = 3r/R (1 is best)' if column == 0 else 'Cell max |J - 1| (%)', fontsize=16, labelpad=8)
                color_axis.tick_params(labelsize=14, direction='out')
        axis = figure.add_axes((14.3/width, y/height, 3.6/width, 3.6/height)); axes.append(axis)
        for mask, color, marker in [(~values['clamp_adjacent'], '#537B9B', '.'), (values['clamp_adjacent'], '#B13B38', 'o')]:
            axis.scatter(values['q_radius'][mask], values['max_abs_J_minus_one'][mask]*100, s=7,
                c=color, marker=marker, alpha=.55, linewidths=0)
        axis.axhline(1., color='#222222', ls='--', lw=1.4)
        axis.set(xlim=(.1, .6), ylim=(0, 1.7), xticks=[.2, .4, .6], yticks=[0, .5, 1., 1.5],
                 xlabel='Reference shape q', ylabel='Cell max |J - 1| (%)')
        style_module.apply_axes_style(axis, style=style)
        style_module.add_top_information(axis, chr(67+row*3)+'  '+name+f' all {len(mesh["cells"])} cells', style=style)
    figure.text(.065, .958, 'Retained reference meshes and same-pressure states: p/mu = 0.01, Ta = 0. No new FEM solves.', fontsize=15)
    figure.text(.065, .143, 'Maps use reference coordinates for exact cell alignment. Left: mesh shape; middle: retained pressure-state local J error.', fontsize=12)
    figure.text(.065, .11, 'Red points: cells touching the fixed basal ring. Blue: away from base. Dashed line: unchanged 1% local volume gate.', fontsize=12)
    figure.text(.065, .077, 'Display cutaway only; all cells included in scatter. No nodal smoothing, no omitted outliers, no independent biological samples.', fontsize=12)
    figure.text(.065, .044, 'Both original pressure states FAILED. Shape-quality correlation does not establish causation; geometry/materials are uncalibrated.', fontsize=12)
    exported = style_module.export_figure(figure, axes, Path(png_path).with_suffix(''), style=style, overrides=overrides)
    Path(exported.svg).replace(svg_path)
    manifest = json.loads(Path(exported.manifest).read_text())
    manifest['exports']['svg'] = str(Path(svg_path).resolve())
    Path(exported.manifest).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    plt.close(figure)


def prepare(workspace, skills):
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path, result_admission
    from prl.runs.ventricle_mesh_quality import RESULT, verify
    from prl.runs.fenicsx_runtime import save_json
    from prl.verification.ventricle_3d import load_arrays
    root = result_path(workspace, RESULT); skills = Path(skills)
    if (root/'figures').exists():
        raise FileExistsError('Figure preparation is create-only')
    if not result_admission(workspace, 96*1024**2)['can_start'] or verify(root)['status'] != 'passed':
        raise RuntimeError('Verification or storage refused')
    data = {'configuration': np.array((root/'input/configuration.json').read_text()),
            'source_identities': np.array((root/'copied_identities.json').read_text())}
    for name in ['M0', 'M1']:
        data.update({'mesh_'+name+'_'+k: v for k, v in load_arrays(root/'input'/f'{name}_mesh.npz').items()})
        data.update({'state_'+name+'_'+k: v for k, v in load_arrays(root/'input'/f'{name}_state_pressure_1.npz').items()
                     if k in ['u', 'pressure', 'load', 'activation']})
    np.savez_compressed(root/'figure_data.npz', **data)
    snapshots = {'helper': Path(__file__).resolve(), 'quality': Path(workspace)/'src/prl/verification/tetra_quality.py',
        'mechanics': Path(workspace)/'src/prl/verification/ventricle_3d.py',
        'geometry': Path(workspace)/'src/prl/rendering/ventricle_3d.py',
        'probe': Path(workspace)/'src/prl/verification/ventricle_mesh_probe.py',
        'style': skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'}
    command = [sys.executable, '-B', '-X', 'utf8', str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
               str(root/'figures'), '--main', 'S2D2A', '--analysis-key', 'mesh_quality', '--data', str(root/'figure_data.npz')]
    for name, path in snapshots.items():
        command.extend(['--python', name+'='+str(path)])
    command.extend(['--model', 'report='+str(root/'quality_report.json')])
    subprocess.run(command, check=True)
    revision = next((root/'figures/FigS2D2A_mesh_quality').glob('FigS2D2A_*')); prefix = revision.name
    files = {key: next(revision.glob('*_'+key+'.py')).name for key in snapshots}
    code = f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 作图调整参数：沿用项目紧凑FEM风格；原始网格坐标，不放大形变。
axis_box_size_in = (3.6, 3.6)
FIGURE_SIZE_IN = (19.8, 12.8)
DPI = 600
STYLE_SOURCE = 'Existing compact FEM style; explicit per-field overrides'
# 所有单元参与散点；空间相关单元不是独立生物样本，不提供p值。
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
snapshots = {{key: load_snapshot('mesh_quality_'+key, file) for key, file in {files!r}.items()}}
snapshots['helper'].draw(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, *[snapshots[k] for k in ['style','mechanics','geometry','quality','probe']])'''
    notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(
        '# 已有网格质量与体积误差\n从物理复制的网格和u/p独立重算；无新求解，不把相关性当因果。两压力态原failed不变。'),
        nbformat.v4.new_code_cell(code), nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=1100))')],
        metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}})
    nbformat.write(notebook, revision/f'03_{prefix}_plot.ipynb')
    methods = revision/f'02_{prefix}_methods.txt'; content = methods.read_text(encoding='utf-8')
    details = {'风格来源': '继承项目紧凑FEM风格；3.6英寸方轴，显式字段例外；600dpi PNG及可编辑SVG。',
        '用户提供的期刊规格': '未指定；按内部网格诊断用途执行。',
        '03_材料方法来源': '本项目以src/prl作为稳定方法库；数据包含原始u/p/网格物理副本及source_identities；独立力学、质量公式、几何和样式均为03辅助快照。',
        '数据/模型变换': 'q=3r/R，以正四面体为1；内部二面角。J误差由实存u/p在积分点及额外56点重算。所有空间场映射到参考坐标，显示y>0单元剖面；无节点平滑，无新状态。',
        '统计方法与不确定性': '描述性逐单元散点；M0=1344、M1=3960，全部保留。单元非独立生物样本，无p值/CI。红色基底相邻，蓝色远区。两压力态failed不改写；相关性非因果。',
        '生物学分组颜色': '不适用；颜色编码几何质量、场量或约束邻接，而非生物学分组。'}
    for key, value in details.items():
        content = re.sub(r'(?m)^- '+re.escape(key)+r':.*$', lambda match: '- '+key+': '+value, content)
    methods.write_text(content, encoding='utf-8')
    report = {'status': 'passed', 'revision': str(revision), 'new_FEM_solves': 0, 'scientific_pressure_gate': 'failed'}
    save_json(root/'render_preparation.json', report)
    return report
