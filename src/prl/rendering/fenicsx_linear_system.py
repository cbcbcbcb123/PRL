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
