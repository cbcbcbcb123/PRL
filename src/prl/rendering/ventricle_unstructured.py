"""Saved-candidate structure and quality distributions; never fabricates FEM states."""
from dataclasses import asdict
from pathlib import Path
import json
import numpy as np


def exposed_faces(data):
    cells = data['tetrahedra']; xyz = data['xyz']; faces = {}
    visible = xyz[cells].mean(axis=1)[:, 1] >= 0
    for index in np.where(visible)[0]:
        for order in [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]]:
            face = tuple(sorted(cells[index, order]))
            faces.setdefault(face, []).append(index)
    exposed = [(face, owners[0]) for face, owners in faces.items() if len(owners) == 1]
    return np.asarray([x[0] for x in exposed]), np.asarray([x[1] for x in exposed])


def draw(data_path, png_path, svg_path, style_module, quality):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    with np.load(data_path, allow_pickle=False) as stored:
        data = {k: stored[k] for k in stored.files}
    meshes = {name: {k[len(name)+1:]: v for k, v in data.items() if k.startswith(name+'_')}
              for name in ['M1', 'U1']}
    measured = {name: quality.tetra_quality(mesh['xyz'][mesh['tetrahedra']]) for name, mesh in meshes.items()}
    style = style_module.StyleSpec(axis_box_size_in=(3.6, 3.6), tick_label_size=16., axis_label_size=18.,
        annotation_font_size=16., sample_size_and_stat_font_size=14., legend_font_size=14., axes_line_width=1.5,
        major_tick_length_pt=5., major_tick_width_pt=1., minor_tick_length_pt=3., minor_tick_width_pt=.8,
        data_line_width=1.5, tick_label_pad_pt=4., axis_label_pad_pt=8.)
    default = asdict(style_module.DEFAULT_STYLE)
    overrides = [style_module.StyleOverride(field=k, reason='Established compact FEM diagnostic style; equal-scale mesh maps.')
                 for k, v in asdict(style).items() if v != default[k]]
    width, height = 14.2, 13.1
    figure = plt.figure(figsize=(width, height)); axes = []
    view = np.array([1.8, -2.4, 1.6]); view /= np.linalg.norm(view)
    horizontal = np.cross([0., 0., 1.], view); horizontal /= np.linalg.norm(horizontal)
    projection = np.stack([horizontal, np.cross(view, horizontal)], axis=1)
    projected = meshes['M1']['xyz'] @ projection
    center = (projected.min(axis=0)+projected.max(axis=0))/2
    half = np.ptp(projected, axis=0).max()*.57
    colors = {'M1': '#557C98', 'U1': '#B4483F'}
    for column, name in enumerate(['M1', 'U1']):
        mesh = meshes[name]; metric = measured[name]
        axis = figure.add_axes(([1.25, 8.0][column]/width, 7.9/height, 3.6/width, 3.6/height)); axes.append(axis)
        axis.set(xlim=(center[0]-half, center[0]+half), ylim=(center[1]-half, center[1]+half),
                 xticks=[-1, 0, 1], yticks=[-1, 0, 1], xlabel='Projected x / L', ylabel='Projected height / L', aspect='equal')
        faces, owners = exposed_faces(mesh); surface = mesh['xyz'][faces]
        order = np.argsort(surface.mean(axis=1) @ view)
        artist = PolyCollection((surface @ projection)[order], array=metric['q_radius'][owners][order],
            norm=Normalize(0, 1), cmap='viridis', edgecolors=(.1, .15, .2, .6), linewidths=.18)
        axis.add_collection(artist)
        basal = (np.abs(mesh['xyz'][:, 2]) < 1e-12) & (mesh['xyz'][:, 1] >= 0)
        axis.plot(*(mesh['xyz'][basal] @ projection).T, '.', color='#D44234', ms=2.8)
        style_module.apply_axes_style(axis, style=style)
        style_module.add_top_information(axis, chr(65+column)+f'  {name}: {len(mesh["tetrahedra"])} tetrahedra', style=style)
        color_axis = figure.add_axes(([5.15, 11.9][column]/width, 7.9/height, .18/width, 3.6/height))
        bar = figure.colorbar(artist, cax=color_axis); bar.set_label('Shape q = 3r/R', fontsize=16, labelpad=8)
        color_axis.tick_params(labelsize=14, direction='out')
    for column, key in enumerate(['q_radius', 'min_dihedral_deg']):
        axis = figure.add_axes(([1.25, 8.0][column]/width, 2.85/height, 3.6/width, 3.6/height)); axes.append(axis)
        for name in ['M1', 'U1']:
            values = np.sort(measured[name][key])
            axis.step(values, np.arange(1, len(values)+1)/len(values), where='post', color=colors[name],
                      lw=1.6, ls='-' if name == 'M1' else '--', label=name)
        axis.set(xlim=(0, 1) if column == 0 else (0, 60), ylim=(0, 1),
                 xticks=[0, .25, .5, .75, 1] if column == 0 else [0, 20, 40, 60],
                 yticks=[0, .25, .5, .75, 1], ylabel='Cumulative fraction of cells',
                 xlabel='Shape q = 3r/R' if column == 0 else 'Minimum dihedral (degrees)')
        style_module.apply_axes_style(axis, style=style)
        style_module.add_top_information(axis, 'C  All-cell shape distribution' if column == 0 else 'D  All-cell angle distribution', style=style)
        axis.legend(loc='lower right', frameon=False)
        if column == 0:
            axis.axhline(.05, color='#444444', lw=.9, ls=':')
    figure.text(.088, .946, 'Same faceted geometry and interfaces. Reference coordinates; cutaway for display only.', fontsize=14)
    figure.text(.088, .525, 'Global q05: 0.23827 -> 0.24886 (+4.44%); required +5%: FAILED.', fontsize=14)
    figure.text(.088, .151, 'Min q: 0.2220 -> 0.0292 (worst cells in ECM). Min dihedral: 6.638 -> 6.811 degrees.', fontsize=13)
    figure.text(.088, .111, 'All cells included in the curves. Red mesh points: fixed basal ring. No biological replicates.', fontsize=12)
    figure.text(.088, .071, 'One saved Gmsh candidate; original output adapter failed after node renumbering.', fontsize=12)
    figure.text(.088, .036, 'Offline exact-coordinate readback only. New FEM solves: 0. No new stress or deformation fields.', fontsize=12)
    exported = style_module.export_figure(figure, axes, Path(png_path).with_suffix(''), style=style, overrides=overrides)
    Path(exported.svg).replace(svg_path)
    manifest = json.loads(Path(exported.manifest).read_text()); manifest['exports']['svg'] = str(Path(svg_path).resolve())
    Path(exported.manifest).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    plt.close(figure)


def prepare(workspace, skills):
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path, result_admission
    from prl.runs.ventricle_unstructured import RESULT, verify
    from prl.runs.fenicsx_runtime import save_json
    from prl.verification.ventricle_3d import load_arrays
    root = result_path(workspace, RESULT); skills = Path(skills)
    if (root/'figures').exists():
        raise FileExistsError('Figure already prepared')
    if not result_admission(workspace, 96*1024**2)['can_start'] or verify(root)['status'] != 'passed':
        raise ValueError('Storage or independent readback refused')
    data = {'source_identities': np.array((root/'copied_identities.json').read_text()),
            'comparison': np.array((root/'offline/mesh_comparison.json').read_text())}
    for name, source in [('M1', root/'input/M1_geometry.npz'), ('U1', root/'offline/candidate_geometry.npz')]:
        data.update({name+'_'+key: value for key, value in load_arrays(source).items()})
    np.savez_compressed(root/'figure_data.npz', **data)
    snapshots = {'helper': Path(__file__).resolve(), 'quality': Path(workspace)/'src/prl/verification/tetra_quality.py',
                 'style': skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'}
    command = [sys.executable, '-B', '-X', 'utf8', str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
               str(root/'figures'), '--main', 'S2D2B', '--analysis-key', 'unstructured', '--data', str(root/'figure_data.npz')]
    for key, path in snapshots.items():
        command.extend(['--python', key+'='+str(path)])
    command.extend(['--model', 'report='+str(root/'offline/mesh_comparison.json')])
    subprocess.run(command, check=True)
    revision = next((root/'figures/FigS2D2B_unstructured').glob('FigS2D2B_*')); prefix = revision.name
    files = {key: next(revision.glob('*_'+key+'.py')).name for key in snapshots}
    code = f'''from pathlib import Path
import importlib.util
import sys
import numpy, scipy, matplotlib
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
# 作图调整参数：沿用紧凑FEM诊断风格，每轴3.6英寸正方形。
axis_box_size_in = (3.6, 3.6)
FIGURE_SIZE_IN = (14.2, 13.1)
DPI = 600
STYLE_SOURCE = 'Existing compact FEM diagnostic style; explicit overrides'
# 所有单元经验分布；无筛除、无生物学推断、无新求解。
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
snapshots = {{key: load_snapshot('unstructured_'+key, filename) for key, filename in {files!r}.items()}}
snapshots['helper'].draw(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, snapshots['style'], snapshots['quality'])'''
    notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(
        '# 原/非结构化候选真实结构与质量\n只读重算真实四面体质量。输出适配器失败及5%改善门失败保留；FEM未运行。'),
        nbformat.v4.new_code_cell(code), nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=1000))')],
        metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}})
    nbformat.write(notebook, revision/f'03_{prefix}_plot.ipynb')
    methods = revision/f'02_{prefix}_methods.txt'; content = methods.read_text(encoding='utf-8')
    details = {'风格来源': '继承既有紧凑FEM诊断风格；3.6英寸方轴、显式字段例外；600dpi PNG及可编辑SVG。',
        '用户提供的期刊规格': '未指定；内部候选网格工程验收。',
        '03_材料方法来源': '稳定方法位于src/prl/verification/tetra_quality.py、src/prl/rendering/ventricle_unstructured.py；03辅助快照与自动哈希记录版本。数据物理复制原/新xyz和tetrahedra，非外部路径占位。',
        '数据/模型变换': '从两套真实参考网格重算q=3r/R及最小内二面角；上排y>=0单元剖面仅用于显示，共同色标0至1；下排所有单元经验分布，未剔除极端值。',
        '统计方法与不确定性': '描述性单元分布；原3960、候选2611单元，非独立生物样本，无p值/CI。q05改善4.4423%未达5%，不是力学计算结果；新增FEM为0。',
        '生物学分组颜色': '不适用；颜色为工程网格身份/质量/夹持标记。'}
    for key, value in details.items():
        content = re.sub(r'(?m)^- '+re.escape(key)+r':.*$', lambda match: '- '+key+': '+value, content)
    methods.write_text(content, encoding='utf-8')
    result = {'status': 'passed', 'revision': str(revision), 'FEM': 'not_run', 'new_FEM_solves': 0}
    save_json(root/'render_preparation.json', result)
    return result
