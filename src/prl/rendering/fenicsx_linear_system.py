"""Render a preserved mixed-tangent failure without running a solver.

The F6-S1-S diagnostic assembled and saved ``matrix_csr.npz`` before its
JSON report failed on a non-finite value.  This module deliberately limits
itself to read-only sparse-matrix summaries and figure export.  In
particular, it does not reconstruct or repeat the lost KSP/MUMPS solve.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import sparse


_REQUIRED_ARRAYS = {
    "indptr",
    "indices",
    "data",
    "rhs",
    "residual",
    "displacement",
    "pressure",
    "pressure_cells",
}


def prepare_workspace_figure(workspace,skill_root):
    """Create a self-contained notebook figure from already verified S3 data."""
    import re
    import subprocess
    import sys
    import nbformat
    from prl.result_store import result_path,result_admission
    from prl.runs.fenicsx_linear_system import WORKSPACE_RESULT

    workspace=Path(workspace).resolve(strict=True); skills=Path(skill_root)
    root=result_path(workspace,WORKSPACE_RESULT)
    if (root/'figures').exists():
        raise FileExistsError('Figure preparation is create-only')
    if not result_admission(workspace,32*1024**2)['can_start']:
        raise RuntimeError('Figure storage admission refused')
    report=json.loads((root/'post_verification.json').read_text())
    if report['verification_status']!='passed':
        raise ValueError('Saved evidence must pass independent verification first')
    with np.load(root/'source_f6s1r/M0_mesh.npz',allow_pickle=False) as mesh:
        data={key:mesh[key] for key in ['coordinates','cells','layers','fixed']}
    data.update(mumps_residual=np.array(report['metrics']['relative_residual'],dtype=float),
                superlu_residual=np.array(report['metrics']['reference_relative_residual']),
                solution_difference=np.array(report['metrics']['relative_solution_difference'],dtype=float),
                infog=np.array(report['mumps_infog_1']),margin=np.array(report['mumps_icntl_14']),
                linear_status=np.array(report['linear_solver_status']))
    np.savez_compressed(root/'figure_data.npz',**data)
    subprocess.run([sys.executable,'-B','-X','utf8',str(skills/'cb-paper-figure-workflow/scripts/init_figure_revision.py'),
        str(root/'figures'),'--main','S1S3','--analysis-key','workspace_check','--data',str(root/'figure_data.npz'),
        '--python','helper='+str(Path(__file__).resolve()),
        '--python','style='+str(skills/'cb-plot-unified-style/assets/cb_plot_unified_style.py'),
        '--model','verification='+str(root/'post_verification.json'),
        '--data-role','matrix='+str(root/'matrix_csr.npz'),
        '--data-role','mumps_solution='+str(root/'mumps_linear_solution.npz'),
        '--data-role','superlu_solution='+str(root/'reference_superlu_solution.npz')],check=True)
    revision=next((root/'figures/FigS1S3_workspace_check').glob('FigS1S3_*')); prefix=revision.name
    helper=next(revision.glob('*_helper.py')).name; style=next(revision.glob('*_style.py')).name
    notebook=nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell('# F6-S1-S3：同矩阵工作空间验证\n真实保留的初始网格及线性解；0次非线性求解、0个新平衡态。\n## 作图调整参数\n沿用项目紧凑FEM诊断风格；每轴3.7英寸方框，显式留白；不做统计推断。'),
        nbformat.v4.new_code_cell(f'''from pathlib import Path
import importlib.util
import sys
from IPython.display import Image, display
REVISION_DIR = Path.cwd().resolve()
PREFIX = {prefix!r}
DATA_PATH = REVISION_DIR / f"01_{{PREFIX}}_data.npz"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"
axis_box_size_in = (3.7, 3.7)
STYLE_SOURCE = 'Project compact FEM diagnostics with CB unified style'
FIGURE_SIZE_IN = (11.4, 7.0)
figure_size_in = FIGURE_SIZE_IN
DPI = 600
def load_snapshot(name, filename):
    spec = importlib.util.spec_from_file_location(name, REVISION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
helper = load_snapshot('workspace_plot_snapshot', {helper!r})
style = load_snapshot('workspace_style_snapshot', {style!r})
helper.draw_workspace_figure(DATA_PATH, OUTPUT_PNG, OUTPUT_SVG, style, axis_box_size_in, figure_size_in)'''),
        nbformat.v4.new_code_cell('display(Image(filename=str(OUTPUT_PNG), width=1000))')],
        metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
    nbformat.write(notebook,revision/f'03_{prefix}_plot.ipynb')
    methods=revision/f'02_{prefix}_methods.txt'; content=methods.read_text(encoding='utf-8')
    replacements={
        '风格来源':'沿用项目紧凑FEM诊断；CB统一风格，3.7英寸方轴、显式留白、中文微软雅黑；600 dpi PNG/可编辑SVG。',
        '用户提供的期刊规格':'未指定；用于阶段诊断，不是正式投稿版式。',
        '03_材料方法来源':'PRL src/prl/rendering/fenicsx_linear_system.py与独立verification审计；版本包保留helper/style/verification快照；未采用独立03_材料方法目录。',
        '数据/模型变换':'保存CSR和解的稀疏乘法独立残量；初始P2网格拆成4个显示子三角，不平滑。旧20%配置失败无有限残量，不伪造为0；图中SuperLU来自上轮，未新求解。',
        '统计方法与不确定性':'确定性单矩阵、每后端一次尝试；无生物重复、误差棒或显著性检验。标注线性门1e-8；两解相对差门1e-6。',
        '生物学分组颜色':'不适用；蓝/黄/绿为构造材料域，非生物实验分组。'}
    for key,value in replacements.items():
        content=re.sub(r'(?m)^- '+re.escape(key)+r':.*$',lambda match:'- '+key+': '+value,content)
    methods.write_text(content,encoding='utf-8')
    runtime=root/'figure_runtime'; runtime.mkdir(exist_ok=False)
    (runtime/'README.md').write_text('Owner: F6-S1-S3 figure preparation. Purpose: bounded Jupyter/Matplotlib runtime. No original data. Cleanup requires explicit path approval.\n',encoding='utf-8')
    return {'status':'passed','revision':str(revision),'runtime':str(runtime)}


def draw_workspace_figure(data_path,png_path,svg_path,style_module,axis_box_size_in=(3.7,3.7),figure_size_in=(11.4,7.0)):
    from dataclasses import asdict
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.ticker import FixedLocator,NullFormatter

    with np.load(data_path,allow_pickle=False) as archive:
        data={key:archive[key] for key in archive.files}
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,
        tick_label_size=16.,axis_label_size=18.,annotation_font_size=16.,sample_size_and_stat_font_size=14.,
        legend_font_size=14.,axes_line_width=1.5,major_tick_length_pt=5.,major_tick_width_pt=1.,
        minor_tick_length_pt=3.,minor_tick_width_pt=.8,data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.,
        font_candidates=('Microsoft YaHei','Calibri','DejaVu Sans'),show_minor_ticks=False)
    defaults=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=key,reason='Categorical solver labels have no intermediate numerical ticks; logarithmic y minors are explicit.' if key=='show_minor_ticks' else 'Established compact FEM diagnostic panels with Chinese labels and explicit margins.')
               for key,value in asdict(style).items() if value!=defaults[key]]
    width,height=figure_size_in; side=axis_box_size_in[0]
    fig=plt.figure(figsize=figure_size_in)
    axes=[fig.add_axes((left/width,1.65/height,side/width,side/height)) for left in (1.,6.5)]
    subtriangles=np.array([[0,5,4],[5,1,3],[4,3,2],[5,3,4]])
    polygons=data['coordinates'][data['cells'][:,subtriangles]].reshape(-1,3,2)
    colors=np.array(['#6FAACB','#E6C777','#83B499'])
    axes[0].add_collection(PolyCollection(polygons,facecolors=np.repeat(colors[data['layers']-1],4),
        edgecolors=(.1,.1,.1,.20),linewidths=.15))
    fixed_nodes=np.flatnonzero(np.any(data['fixed'],axis=1))
    axes[0].plot(*data['coordinates'][fixed_nodes].T,'o',color='#B23B37',ms=6)
    for angle in np.linspace(0,2*np.pi,8,endpoint=False):
        direction=np.array([np.cos(angle),np.sin(angle)])
        axes[0].annotate('',xy=.79*direction,xytext=.60*direction,
            arrowprops={'arrowstyle':'->','color':'#B23B37','lw':1.1})
    axes[0].set(xlim=(-1.15,1.15),ylim=(-1.15,1.15),xlabel='x / L',ylabel='y / L')
    axes[0].set_aspect('equal')
    axes[0].xaxis.set_major_locator(FixedLocator([-1,0,1])); axes[0].yaxis.set_major_locator(FixedLocator([-1,0,1]))
    axes[0].text(0,0,'初始构形\np / μ = 0.02\n主动张力 = 0',ha='center',va='center')
    style_module.apply_axes_style(axes[0],style=style)
    style_module.add_top_information(axes[0],'A  三层圆环及原边界条件',style=style)
    values=[float(data['mumps_residual']),float(data['superlu_residual'])]
    for index,value in enumerate(values):
        if np.isfinite(value) and value>0:
            axes[1].plot(index,value,'o',color=('#237857','#637B8A')[index],ms=9)
            axes[1].annotate(f'{value:.2e}',(index,value),xytext=(0,-25),textcoords='offset points',ha='center')
    axes[1].axhline(1e-8,color='#B23B37',linestyle='--',lw=1.5)
    axes[1].set(xlim=(-.65,1.65),ylim=(1e-15,1e-6),yscale='log',ylabel='相对线性残量')
    axes[1].set_xticks([0,1],['MUMPS\n100%余量','SuperLU\n上轮保留'])
    axes[1].yaxis.set_major_locator(FixedLocator([1e-15,1e-12,1e-9,1e-6]))
    style_module.apply_axes_style(axes[1],style=style)
    axes[1].xaxis.set_minor_locator(FixedLocator([]))
    axes[1].yaxis.set_minor_locator(FixedLocator([1e-14,1e-13,1e-11,1e-10,1e-8,1e-7]))
    axes[1].yaxis.set_minor_formatter(NullFormatter())
    style_module.add_top_information(axes[1],'B  同一矩阵的独立残量',style=style)
    axes[1].text(.03,.69,'验收线：1e-8',transform=axes[1].transAxes,color='#B23B37')
    status=str(data['linear_status']).upper()
    fig.text(.088,.925,f"20%余量：INFOG = -9（上轮）  →  100%余量：INFOG = {int(data['infog'])}，{status}",fontsize=15)
    fig.text(.088,.862,f"与保留SuperLU解的相对差 = {float(data['solution_difference']):.2e}；门限1e-6",fontsize=14)
    fig.text(.088,.080,'蓝：心内膜；黄：ECM；绿：心肌。外壁自由；红点为去刚体位移约束。',fontsize=12)
    fig.text(.088,.034,'本轮0次非线性求解、0个新平衡态；原1%局部体积门仍未通过。',fontsize=12)
    exported=style_module.export_figure(fig,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    if Path(exported.svg)!=Path(svg_path):
        Path(exported.svg).replace(svg_path)
        manifest=json.loads(Path(exported.manifest).read_text())
        manifest['exports']['svg']=str(Path(svg_path).resolve())
        Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.close(fig)
    return {'linear_solver_status':status,'new_equilibria':0,'source':'preserved matrices and vectors only'}


def load_saved_matrix(path: str | Path) -> tuple[sparse.csr_matrix, dict[str, np.ndarray]]:
    """Load and validate the create-only CSR evidence package."""

    source = Path(path)
    with np.load(source, allow_pickle=False) as archive:
        missing = _REQUIRED_ARRAYS.difference(archive.files)
        if missing:
            raise ValueError(f"Saved tangent is missing arrays: {sorted(missing)}")
        arrays = {name: np.asarray(archive[name]) for name in archive.files}

    residual = np.asarray(arrays["residual"], dtype=float)
    size = residual.size
    matrix = sparse.csr_matrix(
        (
            np.asarray(arrays["data"], dtype=float),
            np.asarray(arrays["indices"], dtype=np.int64),
            np.asarray(arrays["indptr"], dtype=np.int64),
        ),
        shape=(size, size),
    )
    if arrays["rhs"].shape != residual.shape:
        raise ValueError("Saved right-hand side and residual have different shapes")
    if not np.all(np.isfinite(matrix.data)) or not np.all(np.isfinite(residual)):
        raise ValueError("Saved tangent or residual contains a non-finite value")
    return matrix, arrays


def matrix_diagnostics(
    matrix: sparse.csr_matrix,
    displacement: np.ndarray,
    pressure: np.ndarray,
    pressure_cells: np.ndarray,
    *,
    sparsity_bins: int = 256,
) -> dict[str, object]:
    """Compute plotting summaries only; no global solve or factorization."""

    matrix = sparse.csr_matrix(matrix)
    displacement = np.asarray(displacement, dtype=np.int64).ravel()
    pressure = np.asarray(pressure, dtype=np.int64).ravel()
    pressure_cells = np.asarray(pressure_cells, dtype=np.int64)
    size = matrix.shape[0]
    if matrix.shape != (size, size):
        raise ValueError("Expected a square mixed tangent")
    ordering = np.concatenate((displacement, pressure))
    if ordering.size != size or not np.array_equal(np.sort(ordering), np.arange(size)):
        raise ValueError("Displacement and pressure maps must partition the tangent")
    if pressure_cells.ndim != 2 or pressure_cells.shape[0] == 0:
        raise ValueError("Expected a non-empty two-dimensional pressure-cell map")
    if not np.all(np.isin(pressure_cells, pressure)):
        raise ValueError("Pressure-cell map contains a non-pressure degree of freedom")

    inverse_order = np.empty(size, dtype=np.int64)
    inverse_order[ordering] = np.arange(size, dtype=np.int64)
    coo = matrix.tocoo(copy=False)
    nonzero = np.asarray(coo.data) != 0
    bin_count = min(max(int(sparsity_bins), 8), size)
    rows = inverse_order[np.asarray(coo.row)[nonzero]] * bin_count // size
    columns = inverse_order[np.asarray(coo.col)[nonzero]] * bin_count // size
    occupancy = np.zeros((bin_count, bin_count), dtype=np.int64)
    np.add.at(occupancy, (rows, columns), 1)

    row_norms = np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=1)).ravel())
    diagonal = np.abs(matrix.diagonal())
    cell_singular_values = np.empty(pressure_cells.shape, dtype=float)
    for index, cell_dofs in enumerate(pressure_cells):
        local = matrix[cell_dofs][:, cell_dofs].toarray()
        cell_singular_values[index] = np.linalg.svd(local, compute_uv=False)

    if not np.all(np.isfinite(cell_singular_values)):
        raise ValueError("A pressure-cell singular value is non-finite")
    return {
        "occupancy": occupancy,
        "row_norms": row_norms,
        "diagonal": diagonal,
        "pressure_cell_singular_values": cell_singular_values,
        "size": int(size),
        "stored_terms": int(matrix.nnz),
        "numerical_nonzeros": int(np.count_nonzero(matrix.data)),
        "displacement_dofs": int(displacement.size),
        "pressure_dofs": int(pressure.size),
        "pressure_cells": int(pressure_cells.shape[0]),
        "pressure_modes_per_cell": int(pressure_cells.shape[1]),
        "zero_rows": int(np.count_nonzero(row_norms == 0)),
        "zero_diagonal_entries": int(np.count_nonzero(diagonal == 0)),
    }


def _load_failure_status(root: Path) -> tuple[dict[str, object], dict[str, object]]:
    failure = json.loads((root / "failure.json").read_text(encoding="utf-8"))
    execution = json.loads((root / "execution.json").read_text(encoding="utf-8"))
    error = failure.get("error", {})
    serialization_failure = (
        failure.get("status") == "failed"
        and error.get("type") == "ValueError"
        and "Out of range float values are not JSON compliant: inf"
        in str(error.get("message", ""))
    )
    if not serialization_failure:
        raise ValueError("This renderer is specific to the retained JSON-inf failure")
    if execution.get("nonlinear_equilibrium_solves") != 0:
        raise ValueError("Execution record does not certify zero equilibrium solves")
    return failure, execution


def _positive_sorted(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    positive = np.sort(np.asarray(values, dtype=float)[np.asarray(values) > 0])
    if positive.size == 0:
        raise ValueError("Expected at least one positive matrix scale")
    percentile = np.linspace(0.0, 100.0, positive.size)
    return percentile, positive


def render(
    result_root: str | Path,
    png_path: str | Path | None = None,
    svg_path: str | Path | None = None,
    *,
    dpi: int = 300,
) -> dict[str, object]:
    """Export the honest 2x2 F6-S1-S diagnostic from saved evidence only."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    root = Path(result_root).resolve(strict=True)
    _failure, execution = _load_failure_status(root)
    matrix, arrays = load_saved_matrix(root / "matrix_csr.npz")
    diagnostics = matrix_diagnostics(
        matrix,
        arrays["displacement"],
        arrays["pressure"],
        arrays["pressure_cells"],
    )

    if png_path is None:
        png_path = root / "figures" / "FigS1S_linear_system_diagnosis_v02_20260918.png"
    if svg_path is None:
        svg_path = root / "figures" / "FigS1S_linear_system_diagnosis_v02_20260918.svg"
    png = Path(png_path)
    svg = Path(svg_path)
    if png.exists() or svg.exists():
        raise FileExistsError("Diagnostic figure export is create-only")
    png.parent.mkdir(parents=True, exist_ok=True)
    svg.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(2, 2, figsize=(13.2, 10.2), constrained_layout=True)
    panel_a, panel_b, panel_c, panel_d = axes.ravel()

    occupancy = np.asarray(diagnostics["occupancy"])
    occupied_values = occupancy[occupancy > 0]
    upper = int(occupied_values.max()) if occupied_values.size else 1
    panel_a.imshow(
        np.ma.masked_equal(occupancy, 0),
        origin="upper",
        interpolation="nearest",
        cmap="magma",
        norm=LogNorm(vmin=1, vmax=max(upper, 1)),
        aspect="equal",
    )
    boundary = (
        diagnostics["displacement_dofs"] / diagnostics["size"] * occupancy.shape[0]
        - 0.5
    )
    panel_a.axhline(boundary, color="#1F78B4", linewidth=1.3, linestyle="--")
    panel_a.axvline(boundary, color="#1F78B4", linewidth=1.3, linestyle="--")
    ticks = [0, boundary, occupancy.shape[0] - 1]
    labels = ["0", f"u={diagnostics['displacement_dofs']}", f"n={diagnostics['size']}"]
    panel_a.set_xticks(ticks, labels)
    panel_a.set_yticks(ticks, labels)
    panel_a.set_xlabel("column DOF after [u, p] reordering")
    panel_a.set_ylabel("row DOF after [u, p] reordering")
    panel_a.set_title("A  Downsampled mixed-tangent sparsity")
    panel_a.text(
        0.02,
        0.02,
        "color = log-scaled stored terms per bin",
        transform=panel_a.transAxes,
        fontsize=9,
        color="#333333",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85},
    )

    row_x, row_y = _positive_sorted(np.asarray(diagnostics["row_norms"]))
    diagonal_x, diagonal_y = _positive_sorted(np.asarray(diagnostics["diagonal"]))
    panel_b.plot(row_x, row_y, color="#1F78B4", linewidth=2.0, label=r"row $\ell_2$ norm")
    panel_b.plot(
        diagonal_x,
        diagonal_y,
        color="#E66101",
        linewidth=2.0,
        label=r"$|A_{ii}|$ (nonzero)",
    )
    panel_b.set_yscale("log")
    panel_b.set_xlabel("empirical percentile (%)")
    panel_b.set_ylabel("matrix scale")
    panel_b.set_title("B  Row and diagonal scales")
    panel_b.legend(frameon=False, loc="best")
    panel_b.text(
        0.03,
        0.05,
        f"zero rows = {diagnostics['zero_rows']}\n"
        f"zero diagonals = {diagnostics['zero_diagonal_entries']}",
        transform=panel_b.transAxes,
        fontsize=10,
        va="bottom",
    )

    singular_values = np.asarray(diagnostics["pressure_cell_singular_values"])
    mode = np.arange(1, singular_values.shape[1] + 1)
    q05, median, q95 = np.percentile(singular_values, [5, 50, 95], axis=0)
    panel_c.fill_between(mode, q05, q95, color="#7FCDBB", alpha=0.55, label="cellwise 5-95%")
    panel_c.plot(mode, median, "o-", color="#006D5B", linewidth=2.0, label="cellwise median")
    panel_c.set_yscale("log")
    panel_c.set_xticks(mode)
    panel_c.set_xlabel("local DG2 pressure mode (largest to smallest)")
    panel_c.set_ylabel("singular value of local p-p block")
    panel_c.set_title("C  Finite-bulk pressure-block spectrum")
    panel_c.legend(frameon=False, loc="best")
    panel_c.text(
        0.03,
        0.05,
        f"{diagnostics['pressure_cells']} cells; "
        f"min = {singular_values.min():.3e}\n"
        "Local spectra do not establish global stability.",
        transform=panel_c.transAxes,
        fontsize=10,
        va="bottom",
    )

    residual_norm = float(np.linalg.norm(np.asarray(arrays["residual"], dtype=float)))
    status_lines = [
        "F6-S1-S STATUS",
        "",
        "Engineering package: FAILED",
        "Failure stage: diagnosis.json serialization",
        "Saved tangent: AVAILABLE",
        f"Shape / stored terms: {diagnostics['size']:,} x {diagnostics['size']:,}",
        f"                         {diagnostics['stored_terms']:,}",
        f"Saved residual norm: {residual_norm:.6e}",
        "",
        "Nonlinear equilibrium solves: 0",
        "Newton state updates: 0",
        "MUMPS/KSP details: NOT RETAINED",
        "Reason: non-finite `inf` rejected by JSON",
        "",
        "Scientific status: DG2 equilibrium remains FAILED",
        "Root cause: UNKNOWN from this preserved package",
    ]
    panel_d.axis("off")
    panel_d.set_title("D  Evidence boundary")
    panel_d.text(
        0.03,
        0.97,
        "\n".join(status_lines),
        transform=panel_d.transAxes,
        va="top",
        ha="left",
        fontsize=11.5,
        family="monospace",
        linespacing=1.35,
        bbox={"boxstyle": "round,pad=0.8", "facecolor": "#F5F5F5", "edgecolor": "#888888"},
    )

    for axis in (panel_a, panel_b, panel_c):
        axis.tick_params(direction="out", width=1.0, length=4)
        for spine in axis.spines.values():
            spine.set_linewidth(1.0)
    figure.suptitle(
        "Saved P2/DG2 mixed tangent at the first pressured initial state",
        fontsize=17,
    )
    figure.savefig(png, dpi=dpi, facecolor="white", edgecolor="white")
    figure.savefig(svg, format="svg", facecolor="white", edgecolor="white")
    plt.close(figure)

    return {
        "status": "passed",
        "scientific_status": "failed",
        "root_cause": "unknown_due_to_unretained_mumps_details",
        "png": str(png.resolve()),
        "svg": str(svg.resolve()),
        "matrix_shape": [diagnostics["size"], diagnostics["size"]],
        "stored_terms": diagnostics["stored_terms"],
        "pressure_cell_minimum_singular_value": float(singular_values.min()),
        "nonlinear_equilibrium_solves": int(execution["nonlinear_equilibrium_solves"]),
        "newton_state_updates": 0,
        "global_solver_or_factorization_during_rendering": 0,
        "local_pressure_block_svd_count": diagnostics["pressure_cells"],
        "mumps_details": "not_retained_due_to_json_inf_serialization_failure",
    }


def render_replay(result_root):
    """Model structure and saved solve diagnostics; no assembly or factorization."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Patch

    root=Path(result_root).resolve(strict=True)
    report=json.loads((root/'post_verification.json').read_text(encoding='utf-8'))
    if report['status']!='passed':
        raise ValueError('Independent replay verification must pass before rendering')
    with np.load(root/'assembly/raw/M0_mesh.npz',allow_pickle=False) as mesh:
        coords=mesh['coordinates']; cells=mesh['cells']; layers=mesh['layers']; fixed=mesh['fixed']
    mumps=json.loads((root/'mumps_diagnosis.json').read_text())
    superlu=json.loads((root/'superlu_diagnosis.json').read_text())
    target=root/'figures/FigS1S2_report_replay_v02_20260918'
    if target.with_suffix('.png').exists() or target.with_suffix('.svg').exists():
        raise FileExistsError('Replay figure is create-only')
    target.parent.mkdir(parents=True,exist_ok=True)
    with plt.rc_context({'font.family':'Microsoft YaHei','font.size':11,
                         'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'}):
        fig,axes=plt.subplots(2,2,figsize=(12.8,9.8),layout='constrained')
        ax=axes[0,0]
        palette={1:'#77add0',2:'#e4c884',3:'#8fba9e'}
        patches=PolyCollection(coords[cells[:,:3]],facecolors=[palette[int(k)] for k in layers],
                               edgecolors='#52655b',linewidths=.22)
        ax.add_collection(patches)
        ax.scatter(coords[fixed.any(axis=1),0],coords[fixed.any(axis=1),1],c='#972d35',s=35,zorder=4)
        for angle in np.linspace(0,2*np.pi,12,endpoint=False):
            direction=np.array([np.cos(angle),np.sin(angle)])
            ax.annotate('',xy=direction*.82,xytext=direction*.60,
                        arrowprops={'arrowstyle':'->','color':'#b64040','lw':1.2})
        ax.text(0,0,'保留初始构形\np/μ = 0.02\n主动张力 = 0',ha='center',va='center',fontsize=11)
        ax.set(xlim=(-1.17,1.17),ylim=(-1.17,1.17),aspect='equal',xlabel='X（无量纲）',ylabel='Y（无量纲）')
        ax.set_title('A  三层圆环与原始边界条件',loc='left',fontweight='bold')
        ax.legend(handles=[Patch(color=palette[k],label=label) for k,label in [(1,'心内膜'),(2,'ECM'),(3,'心肌')]],
                  loc='upper right',fontsize=9,frameon=False)
        ax.text(.01,.015,'外壁自由；红点为3个位移约束',transform=ax.transAxes,fontsize=9)

        ax=axes[0,1]; ax.axis('off')
        ax.set_title('B  MUMPS直接失败原因已定位',loc='left',fontweight='bold')
        rows=[['KSP reason',str(mumps['converged_reason'])+'  (PC failed)'],
              ['MUMPS INFOG(1)',str(report['mumps_infog_1'])+'  工作数组过小'],
              ['INFOG(2)',str(report['mumps_infog_2'])+' 个缺少的数值条目'],
              ['ICNTL(14)',str(report['mumps_icntl_14'])+'% 工作空间余量'],
              ['容器OOM退出','否'],['矩阵、右端、DOF映射','与上轮逐项相同']]
        table=ax.table(cellText=rows,colLabels=['保存指标','本次观察'],cellLoc='left',
                       colLoc='left',colWidths=[.38,.62],bbox=[0,.30,1,.62])
        table.auto_set_font_size(False); table.set_fontsize(10)
        for (row,_),cell in table.get_celld().items():
            cell.set_edgecolor('#d7e1dc'); cell.set_facecolor('#e6f0ea' if row==0 else 'white')
        ax.text(0,.19,'-9：内部工作数组不足\n-10才是数值奇异/零主元错误码',va='top',color='#9d3b31',fontsize=12)

        ax=axes[1,0]
        relative=report['superlu_independent_relative_residual']
        values=[1.,relative]
        bars=ax.bar([0,1],values,color=['#aab7b0','#2d8464'],width=.52)
        ax.set_yscale('log'); ax.set_ylim(1e-15,1e2)
        ax.set_xticks([0,1],['初始残量','SuperLU线性解残量'])
        ax.set_ylabel('相对残量 ||Ax − b|| / ||b||')
        for bar,value in zip(bars,values):
            ax.text(bar.get_x()+bar.get_width()/2,value*2.2,f'{value:.2e}',ha='center',fontsize=11)
        ax.axhline(1e-8,color='#9d3b31',ls='--',lw=1)
        ax.text(.04,1.5e-8,'线性诊断检查阈值',color='#9d3b31',fontsize=9)
        ax.set_title('C  同矩阵SuperLU解通过独立残量检查',loc='left',fontweight='bold')
        ax.text(.03,.04,'这是线性诊断向量，未施加到FEM状态。',transform=ax.transAxes,fontsize=9)

        ax=axes[1,1]; ax.axis('off')
        ax.set_title('D  本轮裁决与下一步',loc='left',fontweight='bold')
        lines=['诊断交付：PASSED；DG2受压平衡：仍FAILED',
               '', '保存CSR：9,216阶；245,760个存储项',
               '独立复核：前后状态逐字节相同',
               '估计1-范数条件数：约 1.09e9',
               '尺度风险仍在；不是已确认的奇异矩阵',
               '', '已确认：MUMPS内部工作空间不足',
               '下一步：先验证工作空间余量20% → 100%',
               '', '本轮0个新平衡态，0次自动重跑，0 GPU',
               '材料、几何、压力和1%体积门保持',
               '轮廓、三维、FSI和生长：未运行']
        ax.text(0,.96,'\n'.join(lines),va='top',fontsize=11,linespacing=1.55,
                bbox={'boxstyle':'round,pad=.8','fc':'#f0f5f2','ec':'#c9d8cf'})
        fig.suptitle('F6-S1-S2｜同一初值诊断重放：MUMPS工作空间不足',fontsize=17,fontweight='bold')
        for extension in ['png','svg']:
            fig.savefig(target.with_suffix('.'+extension),dpi=220,facecolor='white')
        plt.close(fig)
    return {'status':'passed','scientific_status':'failed','postprocess_factorizations':0,
            'new_equilibria':0,'png':target.with_suffix('.png').relative_to(root).as_posix(),
            'svg':target.with_suffix('.svg').relative_to(root).as_posix(),
            'source_files':['assembly/raw/M0_mesh.npz','post_verification.json','mumps_diagnosis.json','superlu_diagnosis.json']}
