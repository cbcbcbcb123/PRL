from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "figures" / "theory"
PNG_PATH = OUT_DIR / "efe_node0_figure1_fast_slow_framework_v01.png"
SVG_PATH = OUT_DIR / "efe_node0_figure1_fast_slow_framework_v01.svg"


COL = {
    "ink": "#26323D",
    "muted": "#71808D",
    "panel": "#F5F8FA",
    "panel_edge": "#D8E0E5",
    "lumen": "#E5F4FA",
    "pressure": "#3979B8",
    "wss": "#00A6C8",
    "endo": "#58BEC0",
    "endo_edge": "#258C90",
    "jelly": "#9FC9DA",
    "jelly_edge": "#3D839C",
    "myo": "#CC4B4C",
    "myo_edge": "#963336",
    "active": "#E99C1F",
    "slow": "#7755A6",
    "collagen": "#B74655",
    "elastin": "#7A5AA6",
    "healthy": "#3AA66A",
    "warning": "#E79028",
    "path": "#C83C44",
    "white": "#FFFFFF",
}


mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "axes.linewidth": 0.0,
        "svg.fonttype": "none",
    }
)


def setup_ax(fig: plt.Figure, rect: tuple[float, float, float, float], letter: str, title: str):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    card = FancyBboxPatch(
        (0.005, 0.005),
        0.99,
        0.99,
        boxstyle="round,pad=0.008,rounding_size=0.025",
        facecolor=COL["panel"],
        edgecolor=COL["panel_edge"],
        linewidth=1.2,
        zorder=-10,
    )
    ax.add_patch(card)
    ax.text(0.035, 0.94, letter, fontsize=18, fontweight="bold", color=COL["ink"], va="top")
    ax.text(0.105, 0.94, title, fontsize=13.5, fontweight="bold", color=COL["ink"], va="top")
    return ax


def draw_polygon_cells(ax, x0, x1, y0, y1, n, face, edge, jitter=0.012, seed=1):
    rng = np.random.default_rng(seed)
    gap = (x1 - x0) * 0.012
    width = (x1 - x0 - gap * (n - 1)) / n
    for i in range(n):
        left = x0 + i * (width + gap)
        right = left + width
        dy = rng.uniform(-jitter, jitter, size=4)
        poly = Polygon(
            [
                (left, y0 + dy[0]),
                (right, y0 + dy[1]),
                (right - 0.003, y1 + dy[2]),
                (left + 0.005, y1 + dy[3]),
            ],
            closed=True,
            facecolor=face,
            edgecolor=edge,
            linewidth=1.2,
        )
        ax.add_patch(poly)


def draw_fem_mesh(ax, x0, x1, y0, y1, line_alpha=0.55):
    ax.add_patch(
        Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=COL["jelly"], edgecolor=COL["jelly_edge"], lw=1.2)
    )
    xs = np.linspace(x0, x1, 8)
    for i, x in enumerate(xs):
        ax.plot([x, min(x + 0.09, x1)], [y0, y1], color=COL["white"], lw=1.0, alpha=line_alpha)
        if i < len(xs) - 1:
            ax.plot([x, min(x + 0.06, x1)], [y1, y0], color=COL["jelly_edge"], lw=0.8, alpha=0.35)


def draw_fibers(ax, x0, x1, y, count, thickness=1.5, alpha=0.9):
    xs = np.linspace(x0, x1, 120)
    for i in range(count):
        yy = y + 0.012 * i + 0.004 * np.sin(10 * np.pi * (xs - x0) / max(x1 - x0, 1e-9) + 0.7 * i)
        ax.plot(xs, yy, color=COL["collagen"], lw=thickness, alpha=alpha)
    if count:
        for x in np.linspace(x0 + 0.03, x1 - 0.03, max(2, count)):
            ax.plot([x - 0.012, x + 0.012], [y - 0.003, y + 0.013 * count], color=COL["elastin"], lw=1.0, alpha=0.75)


def draw_panel_a(ax):
    ax.add_patch(Rectangle((0.07, 0.72), 0.86, 0.12, facecolor=COL["lumen"], edgecolor="none"))
    xs = np.linspace(0.08, 0.92, 150)
    ax.plot(xs, 0.78 + 0.012 * np.sin(5 * np.pi * xs), color=COL["pressure"], lw=1.2, alpha=0.45)
    for x in np.linspace(0.13, 0.87, 5):
        ax.add_patch(Circle((x, 0.78), 0.012, facecolor="#E48072", edgecolor="#B85248", lw=0.8, alpha=0.9))
    ax.text(0.08, 0.86, "lumen", color=COL["pressure"], fontsize=10.5, fontweight="bold")

    draw_polygon_cells(ax, 0.08, 0.92, 0.61, 0.69, 8, COL["endo"], COL["endo_edge"], seed=4)
    ax.text(0.50, 0.635, "endocardial DCM", color="#176E73", ha="center", va="center", fontsize=9.5, fontweight="bold")
    draw_fem_mesh(ax, 0.08, 0.92, 0.32, 0.57)
    ax.text(0.50, 0.445, "cardiac-jelly + fibrous ECM FEM", color="#255F73", ha="center", fontsize=9.5, fontweight="bold")
    draw_fibers(ax, 0.11, 0.89, 0.535, 2, thickness=1.2, alpha=0.75)
    draw_polygon_cells(ax, 0.08, 0.92, 0.13, 0.26, 7, COL["myo"], COL["myo_edge"], seed=8)
    ax.text(0.50, 0.18, "active myocardial DCM", color=COL["white"], ha="center", va="center", fontsize=9.5, fontweight="bold")

    for x in (0.30, 0.52, 0.74):
        ax.annotate("", xy=(x, 0.675), xytext=(x, 0.745), arrowprops=dict(arrowstyle="-|>", color=COL["pressure"], lw=1.8))
    ax.text(0.80, 0.72, r"pressure $p(s,t)$", color=COL["pressure"], fontsize=8.8, ha="right")
    ax.annotate("", xy=(0.42, 0.715), xytext=(0.20, 0.715), arrowprops=dict(arrowstyle="-|>", color=COL["wss"], lw=2.0))
    ax.text(0.205, 0.735, r"WSS $\tau_w(s,t)$", color=COL["wss"], fontsize=8.8)
    ax.annotate("", xy=(0.40, 0.285), xytext=(0.26, 0.285), arrowprops=dict(arrowstyle="-|>", color=COL["active"], lw=2.4))
    ax.annotate("", xy=(0.60, 0.285), xytext=(0.74, 0.285), arrowprops=dict(arrowstyle="-|>", color=COL["active"], lw=2.4))
    ax.text(0.50, 0.285, "active input", color=COL["active"], fontsize=8.7, fontweight="bold", ha="center", va="center")
    ax.text(0.10, 0.585, r"$\Gamma_{Je}$", color=COL["muted"], fontsize=8.5)
    ax.text(0.10, 0.285, r"$\Gamma_{mJ}$", color=COL["muted"], fontsize=8.5)
    ax.text(0.50, 0.055, "prescribed loads, not two-way FSI", color=COL["muted"], fontsize=9, ha="center", fontweight="bold")


def draw_panel_b(ax):
    ymid = 0.55
    boxes = [(0.055, 0.31), (0.37, 0.60), (0.66, 0.945)]
    titles = ["one representative beat", r"cycle statistics $\mathcal{M}(s,T)$", "slow cell state + ECM growth"]
    fills = ["#FFF3DD", "#E8F3F7", "#F0EAF7"]
    edges = [COL["active"], COL["jelly_edge"], COL["slow"]]
    for (xa, xb), title, fill, edge in zip(boxes, titles, fills, edges):
        ax.add_patch(FancyBboxPatch((xa, 0.31), xb - xa, 0.43, boxstyle="round,pad=0.012,rounding_size=0.025", fc=fill, ec=edge, lw=1.3))
        ax.text((xa + xb) / 2, 0.70, title, color=edge, fontsize=9.2, fontweight="bold", ha="center")

    tx = np.linspace(0.085, 0.28, 160)
    wave = 0.51 + 0.09 * (np.sin(2 * np.pi * (tx - tx.min()) / (tx.max() - tx.min()) - np.pi / 2) + 1) / 2
    ax.plot(tx, wave, color=COL["myo"], lw=2.2)
    ax.plot([0.085, 0.28], [0.43, 0.43], color=COL["muted"], lw=0.8)
    ax.text(0.182, 0.37, r"$t/T_b$", color=COL["muted"], fontsize=8.5, ha="center")

    stat_x = [0.415, 0.48, 0.545]
    stat_labels = [r"$\Delta\varepsilon_1$", r"$t_{n,rms}$", "OSI"]
    for x, lab in zip(stat_x, stat_labels):
        ax.add_patch(Circle((x, ymid), 0.034, fc=COL["white"], ec=COL["jelly_edge"], lw=1.2))
        ax.text(x, ymid, lab, fontsize=8.0, color=COL["ink"], ha="center", va="center")
    ax.text(0.485, 0.41, r"$\overline{W}_J,\ \phi_{me},\ D_J^{cycle}$", fontsize=8.6, color=COL["muted"], ha="center")

    slow_items = [("qE", 0.71, 0.58), ("qM", 0.79, 0.58), (r"$\rho_c$", 0.87, 0.58), (r"$\rho_{el}$", 0.75, 0.44), (r"$\mathbf{A}_c$", 0.83, 0.44), (r"$\mathbf{F}_g$", 0.91, 0.44)]
    for text, x, y in slow_items:
        ax.add_patch(Circle((x, y), 0.03, fc=COL["white"], ec=COL["slow"], lw=1.1))
        ax.text(x, y, text, fontsize=8.4, color=COL["slow"], ha="center", va="center", fontweight="bold")

    for start, end in [((0.31, ymid), (0.37, ymid)), ((0.60, ymid), (0.66, ymid))]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13, lw=1.8, color=COL["ink"]))
    ax.text(0.34, 0.59, "fast", fontsize=8.5, color=COL["ink"], ha="center")
    ax.text(0.63, 0.59, "slow", fontsize=8.5, color=COL["slow"], ha="center")
    feedback = FancyArrowPatch((0.91, 0.30), (0.15, 0.30), connectionstyle="arc3,rad=-0.28", arrowstyle="-|>", mutation_scale=14, lw=2.2, color=COL["path"])
    ax.add_patch(feedback)
    ax.text(0.53, 0.16, "remodelled ECM changes the next beat", color=COL["path"], fontsize=9.0, ha="center", fontweight="bold")
    ax.text(0.53, 0.075, r"$\epsilon_t=T_b/\tau_r\ll1$", color=COL["ink"], fontsize=10.0, ha="center")


def mini_tissue(ax, x0, x1, title, variant):
    ax.add_patch(FancyBboxPatch((x0, 0.18), x1 - x0, 0.60, boxstyle="round,pad=0.01,rounding_size=0.018", fc=COL["white"], ec=COL["panel_edge"], lw=1.0))
    ax.text((x0 + x1) / 2, 0.74, title, ha="center", va="center", fontsize=9.2, fontweight="bold", color=COL["ink"])
    ax.add_patch(Rectangle((x0 + 0.025, 0.57), x1 - x0 - 0.05, 0.07, fc=COL["endo"], ec=COL["endo_edge"], lw=0.9))
    ax.add_patch(Rectangle((x0 + 0.025, 0.31), x1 - x0 - 0.05, 0.23, fc="#D5E9F0", ec=COL["jelly_edge"], lw=0.8))
    ax.add_patch(Rectangle((x0 + 0.025, 0.22), x1 - x0 - 0.05, 0.065, fc=COL["myo"], ec=COL["myo_edge"], lw=0.8))
    cx = (x0 + x1) / 2
    if variant in ("endo", "mixed"):
        ax.add_patch(Circle((cx - 0.025, 0.53), 0.018, fc=COL["endo"], ec=COL["endo_edge"], lw=0.8))
        ax.add_patch(Circle((cx + 0.015, 0.47), 0.018, fc=COL["collagen"], ec=COL["myo_edge"], lw=0.8))
        ax.add_patch(FancyArrowPatch((cx - 0.015, 0.56), (cx + 0.012, 0.49), arrowstyle="-|>", mutation_scale=10, lw=1.3, color=COL["slow"]))
    if variant in ("mes", "mixed"):
        start = (x0 + 0.05, 0.34)
        end = (cx + 0.045, 0.49)
        ax.add_patch(Circle(start, 0.018, fc=COL["slow"], ec="#5E3C86", lw=0.8))
        ax.add_patch(FancyArrowPatch(start, end, connectionstyle="arc3,rad=-0.15", arrowstyle="-|>", mutation_scale=10, lw=1.3, linestyle="--", color=COL["slow"]))
    fibers = 1 if variant != "mixed" else 2
    draw_fibers(ax, x0 + 0.055, x1 - 0.055, 0.42, fibers, thickness=1.0)


def draw_panel_c(ax):
    mini_tissue(ax, 0.04, 0.32, "H1  Endocardial / EndMT-like", "endo")
    mini_tissue(ax, 0.36, 0.64, "H2  Mesenchymal-derived", "mes")
    mini_tissue(ax, 0.68, 0.96, "H3  Mixed", "mixed")
    ax.add_patch(FancyArrowPatch((0.31, 0.13), (0.70, 0.13), connectionstyle="arc3,rad=0.25", arrowstyle="-|>", mutation_scale=12, lw=1.3, linestyle="--", color=COL["muted"]))
    ax.add_patch(FancyArrowPatch((0.64, 0.13), (0.70, 0.13), connectionstyle="arc3,rad=-0.15", arrowstyle="-|>", mutation_scale=12, lw=1.3, linestyle="--", color=COL["muted"]))
    ax.text(0.50, 0.055, "lineage hypotheses require time-resolved tracing", color=COL["muted"], fontsize=9.0, ha="center", fontweight="bold")


def draw_state(ax, x0, x1, label, fiber_count, state_color):
    ax.add_patch(FancyBboxPatch((x0, 0.30), x1 - x0, 0.45, boxstyle="round,pad=0.008,rounding_size=0.02", fc=COL["white"], ec=state_color, lw=1.3))
    ax.add_patch(Rectangle((x0 + 0.025, 0.62), x1 - x0 - 0.05, 0.065, fc=COL["endo"], ec=COL["endo_edge"], lw=0.8))
    ax.add_patch(Rectangle((x0 + 0.025, 0.39), x1 - x0 - 0.05, 0.20, fc="#D7EAF1", ec=COL["jelly_edge"], lw=0.8))
    ax.add_patch(Rectangle((x0 + 0.025, 0.32), x1 - x0 - 0.05, 0.055, fc=COL["myo"], ec=COL["myo_edge"], lw=0.8))
    if fiber_count:
        draw_fibers(ax, x0 + 0.04, x1 - 0.04, 0.55, fiber_count, thickness=1.1)
    ax.text((x0 + x1) / 2, 0.72, label, ha="center", va="center", fontsize=9.0, fontweight="bold", color=state_color)


def draw_panel_d(ax):
    draw_state(ax, 0.04, 0.29, "healthy", 0, COL["healthy"])
    draw_state(ax, 0.375, 0.625, "reversible remodelling", 2, COL["warning"])
    draw_state(ax, 0.71, 0.96, "persistent EFE candidate", 6, COL["path"])
    ax.add_patch(FancyArrowPatch((0.29, 0.525), (0.375, 0.525), arrowstyle="<|-|>", mutation_scale=12, lw=1.5, color=COL["healthy"]))
    ax.add_patch(FancyArrowPatch((0.625, 0.525), (0.71, 0.525), arrowstyle="-|>", mutation_scale=12, lw=1.8, linestyle="--", color=COL["warning"]))
    ax.text(0.667, 0.565, "unverified\ntransition", ha="center", va="bottom", fontsize=8.0, color=COL["warning"], fontweight="bold")
    ax.plot([0.667, 0.667], [0.28, 0.77], color=COL["warning"], lw=1.2, ls="--", alpha=0.8)
    ax.text(0.835, 0.23, r"$\Lambda_{enc}=E_{EFE}h_{EFE}/(E_mh_m)$", color=COL["path"], fontsize=9.5, ha="center", fontweight="bold")
    outcomes = ["shortening", "relaxation", "growth"]
    for i, text in enumerate(outcomes):
        x = 0.75 + i * 0.085
        ax.add_patch(Circle((x, 0.12), 0.028, fc="#F9E4E4", ec=COL["path"], lw=1.0))
        ax.text(x, 0.12, "↓", ha="center", va="center", fontsize=12, color=COL["path"], fontweight="bold")
        ax.text(x, 0.064, text, ha="center", va="center", fontsize=7.4, color=COL["muted"])
    ax.add_patch(FancyArrowPatch((0.84, 0.22), (0.84, 0.155), arrowstyle="-|>", mutation_scale=12, lw=1.6, color=COL["path"]))
    ax.text(0.33, 0.12, "same load, different history?", color=COL["slow"], fontsize=8.8, ha="center", fontweight="bold")
    ax.text(0.33, 0.055, "bistability / memory require Node 2 proof", color=COL["muted"], fontsize=8.5, ha="center")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(18, 12), facecolor="white")
    fig.text(0.5, 0.965, "Figure 1 v01 | Minimal fast–slow theory for endocardial fibroelastosis", ha="center", va="top", fontsize=21, fontweight="bold", color=COL["ink"])
    fig.text(0.5, 0.93, "Active trilayer mechanics generates cycle statistics; cell-state and ECM remodelling feed back on the next beat", ha="center", va="top", fontsize=11.5, color=COL["muted"])

    ax_a = setup_ax(fig, (0.035, 0.515, 0.455, 0.38), "A", "Trilayer fast mechanics")
    ax_b = setup_ax(fig, (0.51, 0.515, 0.455, 0.38), "B", "Beat-to-remodelling map")
    ax_c = setup_ax(fig, (0.035, 0.105, 0.455, 0.38), "C", "Competing cellular origins")
    ax_d = setup_ax(fig, (0.51, 0.105, 0.455, 0.38), "D", "Candidate tissue states and functional feedback")

    draw_panel_a(ax_a)
    draw_panel_b(ax_b)
    draw_panel_c(ax_c)
    draw_panel_d(ax_d)

    fig.text(0.5, 0.047, "Theory schematic, not simulation or experimental data. Cell origin, state transitions, bistability, mechanical memory and EFE causality remain unverified.", ha="center", fontsize=10.2, color="#805716", fontweight="bold")
    fig.text(0.5, 0.022, "Fast mechanical power ledger and nonmatching DCM–FEM interfaces inherit the previously reviewed T0 contract; slow chemical/remodelling energetics require a separate Node 2 ledger.", ha="center", fontsize=8.8, color=COL["muted"])

    fig.savefig(PNG_PATH, dpi=220)
    fig.savefig(SVG_PATH)
    plt.close(fig)
    print(PNG_PATH)
    print(SVG_PATH)


if __name__ == "__main__":
    main()
