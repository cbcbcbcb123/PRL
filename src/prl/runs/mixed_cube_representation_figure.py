"""Prepare a self-contained mixed-cube figure package; never solve or render.

The official paper-figure initializer owns version allocation and copying.
Notebook execution, visual review and freezing remain separate explicit steps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def _sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _notebook_payload(prefix: str, hashes: dict[str, str]) -> dict:
    """Build editable notebook content entirely in memory."""
    notebook = {
        "cells": [],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": sys.version.split()[0]},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    def cell(kind: str, identifier: str, source: str) -> None:
        content = {"cell_type": kind, "id": identifier, "metadata": {}, "source": source}
        if kind == "code":
            content.update(execution_count=None, outputs=[])
        notebook["cells"].append(content)

    cell("markdown", "purpose", """# 同载混合离散表示对照：真实保存态探索图

本图只读取本版本包物理复制的数值结果和实际保存态，不运行 FEM、Docker 或新求解。
结构面板为真实参考网格及边界标签；误差来自独立读回；状态面板采用最细 P3/P2 的真实初/中/末 Newton 保存态。
Newton 序号是算法迭代，不是生理时间。候选资格和旧心室失败分别报告，失败或未运行不补造数据。

## 作图调整参数

以下参数可编辑：每个主轴框固定 4×4 英寸，显式增加多面板边距；几何显示放大 30 倍，颜色值不放大。
采用项目已批准的 160 dpi 紧凑探索例外，不是 600 dpi 投稿终稿；无生物学分组或推断统计。
非默认字体、线宽、轴框和分辨率由 renderer 的 StyleOverride 与导出 manifest 完整记录。
""")
    cell("code", "parameters", f'''from pathlib import Path
import os
import sys
from IPython.display import Image, Markdown, display

PREFIX = {prefix!r}
REVISION_DIR = Path.cwd().resolve()
if REVISION_DIR.name != PREFIX:
    raise RuntimeError("请在当前版本包目录执行 Notebook；PREFIX 与目录不匹配")
STYLE_SOURCE = "cb-plot-unified-style；项目已批准160dpi紧凑探索例外"
axis_box_size_in = (4.0, 4.0)
deformation_scale = 30.0
export_dpi = 160
DPI = export_dpi
FIGURE_SIZE_IN = (1.25 + 3*axis_box_size_in[0] + 2*2.25 + 2.25,
                  3.0 + 2*axis_box_size_in[1] + 1.4 + 1.7)
PRIMARY_DATA = REVISION_DIR / f"01_{{PREFIX}}_data.json"
STATE_DATA = REVISION_DIR / f"01a_{{PREFIX}}_data_states.npz"
RENDERER_SOURCE = REVISION_DIR / f"03a_{{PREFIX}}_renderer.py"
STYLE_SOURCE_FILE = REVISION_DIR / f"03c_{{PREFIX}}_style.py"
OUTPUT_PNG = REVISION_DIR / f"04_{{PREFIX}}.png"
OUTPUT_SVG = REVISION_DIR / f"05_{{PREFIX}}.svg"

# 运行缓存属于结果根下的AI过程目录，不放入正式图版本包；数据依赖全部在包内。
RUNTIME_DIR = REVISION_DIR.parents[2] / "07_ai_files" / f"{{PREFIX}}_runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
ownership = RUNTIME_DIR / "README.md"
if not ownership.exists():
    ownership.write_text("本目录由本图Notebook创建，仅含Matplotlib运行缓存。\\n"
                         "所有权：mixed_cube_representation_figure；不得自动删除。\\n", encoding="utf-8")
os.environ["MPLCONFIGDIR"] = str(RUNTIME_DIR)
sys.dont_write_bytecode = True
''')
    cell("markdown", "data-explanation", """## 数据读取、完整性与证据边界

输入为实际求解后的离线汇总 JSON 与 NPZ；下面核对物理副本哈希。各工况保留实际混合自由度和误差，
未运行/失败不会补齐成通过。状态直接取已保存的 iteration，参考切面只选已有 Z/L=0.5 节点。
图中形变采用节点间分片线性显示，不声称额外运行了高阶场插值或新的平衡求解。

原注册门在原 JSON 的 `convergence` 中保持；图示候选资格采用
`candidate_k100_qualification`，使额外八点积分/J安全复核失败同样可见。
此显示用副本不会改写原数据文件、原门或历史失败。
""")
    cell("code", "read-data", f'''import hashlib
import json
from copy import deepcopy
import numpy as np

EXPECTED_SHA256 = {hashes!r}
for role, path in {{"report": PRIMARY_DATA, "states": STATE_DATA,
                   "renderer": RENDERER_SOURCE, "style": STYLE_SOURCE_FILE}}.items():
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    if checksum.hexdigest() != EXPECTED_SHA256[role]:
        raise RuntimeError(f"包内{{role}}物理副本哈希改变；请确认版本及记录，不跳过检查")

REPORT = json.loads(PRIMARY_DATA.read_text(encoding="utf-8"))
with np.load(STATE_DATA, allow_pickle=False) as saved:
    ARRAYS = {{key: saved[key] for key in saved.files}}
PLOT_REPORT = deepcopy(REPORT)
qualified = REPORT.get("candidate_k100_qualification", {{}})
if "status" in qualified:
    PLOT_REPORT.setdefault("convergence", {{}}).setdefault("groups", {{}}).setdefault(
        "candidate_p3p2", {{}})["status"] = qualified["status"]
print("图示候选资格：", qualified.get("status", "unknown"))
print("保存态字段数：", len(ARRAYS))
''')
    cell("markdown", "render-explanation", """## 绘图与导出

只导入当前包内 renderer/style 快照。误差图横轴为实际混合 DOF，并非等 DOF 对照；
缺失网格仅显示存在的点，不跨缺失点连线；对数图不能显示零误差，明确记录而不加伪小量。
初/中/末均选真实保存态；不足三个则保留空面板。色标不乘几何放大倍数。
导出使用统一风格 `export_figure`，固定主轴框和显式边距，不使用 tight_layout 或自动裁剪。
""")
    cell("code", "draw", '''import importlib.util

def load_local_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module

STYLE = load_local_module("representation_style_snapshot", STYLE_SOURCE_FILE)
RENDERER = load_local_module("representation_renderer_snapshot", RENDERER_SOURCE)
OUTPUTS = RENDERER.draw_representation(
    PLOT_REPORT, ARRAYS, STYLE, OUTPUT_PNG, OUTPUT_SVG,
    axis_box_size_in=axis_box_size_in,
    deformation_scale=deformation_scale,
    export_dpi=export_dpi,
)
print(json.dumps(OUTPUTS, ensure_ascii=False, indent=2))
''')
    cell("markdown", "preview-explanation", """## 当前版本 PNG 预览

执行成功不代表视觉验收或科学通过。执行后检查本预览，无裁切、重叠或证据误读后，
再单独运行技能的视觉验收及冻结命令；未经目检不得标记通过。
""")
    cell("code", "preview", '''if not OUTPUT_PNG.is_file() or OUTPUT_PNG.stat().st_size == 0:
    raise FileNotFoundError(f"缺少当前版本PNG：{OUTPUT_PNG}")
if not OUTPUT_SVG.is_file() or OUTPUT_SVG.stat().st_size == 0:
    raise FileNotFoundError(f"缺少当前版本SVG：{OUTPUT_SVG}")
display(Markdown(f"当前预览：{OUTPUT_PNG.name}"))
display(Image(filename=str(OUTPUT_PNG)))
''')
    return notebook


def prepare(result_root: Path, workspace: Path, figure_skill: Path, style_source: Path) -> dict:
    """Create a fresh revision using the official initializer, without executing it."""
    result_root, workspace = result_root.resolve(), workspace.resolve()
    figure_skill, style_source = figure_skill.resolve(), style_source.resolve()
    sources = {
        "report": result_root / "delivery_analysis.json",
        "states": result_root / "figure_states.npz",
        "renderer": workspace / "src/prl/rendering/mixed_cube_representation.py",
        "style": style_source,
    }
    initializer = figure_skill / "scripts/init_figure_revision.py"
    validator = figure_skill / "scripts/validate_figure_revision.py"
    for source in [*sources.values(), initializer, validator]:
        if not source.is_file():
            raise FileNotFoundError(source)
    report = json.loads(sources["report"].read_text(encoding="utf-8"))
    if not isinstance(report.get("cases"), list):
        raise ValueError("Expected persisted representation delivery report with cases list")
    hashes = {role: _sha256(path) for role, path in sources.items()}
    command = [sys.executable, "-B", "-X", "utf8", str(initializer),
               str(result_root / "Figures"), "--main", "R2", "--analysis-key", "mixed_cube_representation",
               "--data", str(sources["report"]), "--data-role", f"states={sources['states']}",
               "--python", f"renderer={sources['renderer']}", "--python", f"style={sources['style']}"]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                               check=False, env=environment, timeout=120)
    if completed.returncode:
        raise RuntimeError(f"Figure initializer failed; preserve any created files.\n"
                           f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
    created = [line.partition("已创建版本包：")[2].strip() for line in completed.stdout.splitlines()
               if line.startswith("已创建版本包：")]
    if len(created) != 1:
        raise RuntimeError("Initializer did not return one identifiable new package; inspect retained output: "
                           + completed.stdout)
    revision = Path(created[0]).resolve()
    parent = result_root / "Figures" / "FigR2_mixed_cube_representation"
    if revision.parent != parent or not revision.is_dir():
        raise ValueError("Initializer destination does not match the requested figure parent")
    prefix = revision.name
    copies = {
        "report": revision / f"01_{prefix}_data.json",
        "states": revision / f"01a_{prefix}_data_states.npz",
        "renderer": revision / f"03a_{prefix}_renderer.py",
        "style": revision / f"03c_{prefix}_style.py",
    }
    for role, source in sources.items():
        if _sha256(source) != hashes[role] or _sha256(copies[role]) != hashes[role]:
            raise ValueError(f"Input or physical copy drift for {role}; preserve the incomplete package")
    notebook = revision / f"03_{prefix}_plot.ipynb"
    notebook.write_text(json.dumps(_notebook_payload(prefix, hashes), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    methods = revision / f"02_{prefix}_methods.txt"
    initial_methods = methods.read_text(encoding="utf-8")
    automatic = initial_methods[initial_methods.index("## 自动记录"):]
    source_lines = "\n".join(f"- 来源 {role}: {source.as_posix()}；SHA-256={hashes[role]}；"
                             f"包内物理副本={copies[role].name}" for role, source in sources.items())
    methods.write_text(f"""# 图件方法与验证记录

## 人工填写内容
- 风格来源: cb-plot-unified-style；项目已批准的紧凑探索图例外：每轴4×4英寸、160dpi；固定主轴框、显式边距、可编辑SVG。所有非默认字段由StyleOverride记录。
- 用户提供的期刊规格: 未指定；按项目探索用途执行。不是600dpi投稿终稿，通用投稿检查失败不得隐去。
- 03_材料方法来源: 项目稳定绘图实现为src/prl/rendering/mixed_cube_representation.py；本项目未采用03_材料方法及理论模型目录。本图只调用下列包内renderer/style快照，不运行求解器。数值原始状态与离线读回来源由JSON保留。
- 数据/模型变换: JSON与NPZ物理复制且SHA-256核验。P3/P1与P3/P2同载误差对实际混合DOF作图；not_run/失败保留。几何显示乘30，位移颜色不放大；最细P3/P2参考Z/L=0.5切面取已有节点、分片线性显示。初/中/末仅选真实保存iteration，不合成状态；算法迭代不是生理时间。
- 统计方法与不确定性: 确定性制造解/有限元验证，无生物学样本、统计检验、p值或置信区间。误差及资格门来自独立读回；不以图件或工程通过替代科学资格。图示candidate_k100_qualification额外包含八点积分/J安全复核，原convergence门在数据中保持。
- 生物学分组颜色: 不适用；颜色区分数值单元空间、边界类型和未放大的位移值。
- 人工/代理视觉验收: 待检查
- 执行边界: 本helper只准备包与Notebook，未执行Notebook、未生成PNG/SVG；待执行、目检及分别标记。原心室资格failed不因此改变。
- 运行缓存: Notebook执行时只在结果根07_ai_files/<PREFIX>_runtime写入Matplotlib缓存及所有权README，不属于正式图包；不自动删除。执行器启动前的Jupyter临时目录由调用方限定到已批准结果根。
{source_lines}
- 初始化器来源: {initializer.as_posix()}；SHA-256={_sha256(initializer)}
- 打包helper来源: {Path(__file__).resolve().as_posix()}；SHA-256={_sha256(Path(__file__))}

{automatic}""", encoding="utf-8", newline="\n")
    next_commands = [[sys.executable, "-B", "-X", "utf8", str(validator), str(revision), option]
                     for option in ("--execute", "--visual-qa-pass", "--mark-final")]
    return {"status": "prepared_not_executed", "revision_dir": str(revision), "prefix": prefix,
            "notebook": str(notebook), "methods": str(methods), "source_sha256": hashes,
            "initializer_stdout": completed.stdout, "initializer_stderr": completed.stderr,
            "next_commands_run_separately_with_visual_review_between": next_commands,
            "additional_FEM_solves": 0, "PNG_SVG_generated": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_root", type=Path, help="Approved result root with delivery_analysis.json and figure_states.npz")
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--figure-skill", type=Path,
                        default=Path.home() / ".codex/skills/cb-paper-figure-workflow")
    parser.add_argument("--style-source", type=Path,
                        default=Path.home() / ".codex/skills/cb-plot-unified-style/assets/cb_plot_unified_style.py")
    parser.add_argument("--prepare-only", action="store_true", required=True,
                        help="Prepare inputs/Notebook only; never execute, review or freeze automatically")
    args = parser.parse_args()
    print(json.dumps(prepare(args.result_root, args.workspace, args.figure_skill, args.style_source),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
