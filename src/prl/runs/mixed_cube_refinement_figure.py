"""Prepare the portable FigR3 refinement Notebook without rendering or solving."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def _sha256(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _notebook_payload(prefix, hashes):
    """Generate editable cells in memory; creation does not execute any cell."""
    notebook = {"cells": [], "nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": sys.version.split()[0]}}}

    def add(kind, identifier, source):
        cell = {"cell_type": kind, "id": identifier, "metadata": {}, "source": source}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        notebook["cells"].append(cell)

    add("markdown", "purpose", """# 原制造解定向加密：4/8/12真实保存态探索图

只使用本版本包的真实数值结果、保存态和绘图代码快照，不启动FEM或Docker。
固定比较序列为n=4、8、12；唯一主要阶次为8→12，分母ln(12/8)，原门3.5/2.5/2.5保持。
4→8阶次完整披露；原2/4/8位移L2阶失败及原心室失败保留。n16未登记为本批运行工况。
真实n12参考结构与边界、三误差、主阶次、初/中/末已保存Newton态合并为一页。

## 作图调整参数

每主轴固定4×4英寸；其余边距显式扩展。几何显示×30、色值不放大；160dpi为项目已批准探索例外，
不是600dpi投稿终稿。所有非默认风格字段由renderer的StyleOverride和导出manifest记录。
""")
    add("code", "parameters", f'''from pathlib import Path
import os
import sys
from IPython.display import Image, Markdown, display

PREFIX = {prefix!r}
REVISION_DIR = Path.cwd().resolve()
if REVISION_DIR.name != PREFIX:
    raise RuntimeError("请在对应图版本目录执行，保持PREFIX与目录一致")
STYLE_SOURCE = "cb-plot-unified-style；项目160dpi紧凑探索例外"
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

# 缓存是结果根下的过程材料，正式图包的数据依赖全部来自包内副本。
RUNTIME_DIR = REVISION_DIR.parents[2] / "07_ai_files" / f"{{PREFIX}}_runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
ownership = RUNTIME_DIR / "README.md"
if not ownership.exists():
    ownership.write_text("本目录由FigR3 Notebook创建，只保存绘图运行缓存。\\n"
                         "所有权：mixed_cube_refinement_figure；不自动删除。\\n", encoding="utf-8")
os.environ["MPLCONFIGDIR"] = str(RUNTIME_DIR)
sys.dont_write_bytecode = True
''')
    add("markdown", "data-explanation", """## 真实数据及完整性

下方逐项核验物理复制的数据和代码SHA-256；NPZ禁止pickle。
误差直接使用保存结果的relative_u_L2、relative_u_H1、relative_pressure_L2。
renderer从同一组真实误差复算ln(E8/E12)/ln(1.5)，并检查报告中的primary_EOC一致。
结果状态读取convergence.status，不由图的外观推断；缺失状态保持不可用，不插值补造。
""")
    add("code", "read-data", f'''import hashlib
import json
import numpy as np

EXPECTED_SHA256 = {hashes!r}
for role, path in {{"report": PRIMARY_DATA, "states": STATE_DATA,
                   "renderer": RENDERER_SOURCE, "style": STYLE_SOURCE_FILE}}.items():
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    if checksum.hexdigest() != EXPECTED_SHA256[role]:
        raise RuntimeError(f"包内{{role}}哈希改变，请核对版本与记录")
REPORT = json.loads(PRIMARY_DATA.read_text(encoding="utf-8"))
with np.load(STATE_DATA, allow_pickle=False) as saved:
    ARRAYS = {{key: saved[key] for key in saved.files}}
print("4/8/12资格状态：", REPORT.get("convergence", {{}}).get("status", "unknown"))
''')
    add("markdown", "render-explanation", """## 绘图、固定主阶次与算法状态

只有包内renderer和style被动态导入，不依赖仓库模块或外部结果路径。
A为真实n12参考网格及边界；B为实际三误差对n；C为8→12主阶次与原门；D-F为n12真实初/中/末保存迭代态。
状态面板选参考Z/L=0.5的已有节点作分片线性显示，几何乘30、颜色保持原值。
Newton序号是算法进度，不是生理时间。没有生物学样本量、误差条、p值或生物学推断。
统一风格export_figure导出固定轴框与显式边距，所有视觉例外记录于manifest。
""")
    add("code", "draw", '''import importlib.util

def load_local_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module

STYLE = load_local_module("refinement_style_snapshot", STYLE_SOURCE_FILE)
RENDERER = load_local_module("refinement_renderer_snapshot", RENDERER_SOURCE)
OUTPUTS = RENDERER.draw_refinement(REPORT, ARRAYS, STYLE, OUTPUT_PNG, OUTPUT_SVG,
    axis_box_size_in=axis_box_size_in, deformation_scale=deformation_scale, export_dpi=export_dpi)
print(json.dumps(OUTPUTS, ensure_ascii=False, indent=2))
''')
    add("markdown", "preview-explanation", """## 当前PNG预览及分步验收

执行后目检裁切、重叠和证据表述，再分别运行视觉验收与冻结命令。
绘图执行通过不代表科学资格通过；600dpi投稿检查不得因探索图合格而标记通过。
""")
    add("code", "preview", '''if not OUTPUT_PNG.is_file() or OUTPUT_PNG.stat().st_size == 0:
    raise FileNotFoundError(f"缺少当前版本PNG：{OUTPUT_PNG}")
if not OUTPUT_SVG.is_file() or OUTPUT_SVG.stat().st_size == 0:
    raise FileNotFoundError(f"缺少当前版本SVG：{OUTPUT_SVG}")
display(Markdown(f"当前预览：{OUTPUT_PNG.name}"))
display(Image(filename=str(OUTPUT_PNG)))
''')
    return notebook


def prepare(result_root, workspace, figure_skill, style_source):
    result_root, workspace = Path(result_root).resolve(), Path(workspace).resolve()
    figure_skill, style_source = Path(figure_skill).resolve(), Path(style_source).resolve()
    sources = {"report": result_root / "delivery_analysis.json", "states": result_root / "figure_states.npz",
               "renderer": workspace / "src/prl/rendering/mixed_cube_refinement.py", "style": style_source}
    initializer = figure_skill / "scripts/init_figure_revision.py"
    validator = figure_skill / "scripts/validate_figure_revision.py"
    for source in [*sources.values(), initializer, validator]:
        if not source.is_file():
            raise FileNotFoundError(source)
    report = json.loads(sources["report"].read_text(encoding="utf-8"))
    if not isinstance(report.get("cases"), list):
        raise ValueError("Expected a retained refinement report with a cases list")
    if report.get("convergence", {}).get("primary_pair", [8, 12]) != [8, 12]:
        raise ValueError("Only the frozen primary n8 to n12 refinement may be packaged")
    hashes = {role: _sha256(path) for role, path in sources.items()}
    command = [sys.executable, "-B", "-X", "utf8", str(initializer), str(result_root / "Figures"),
               "--main", "R3", "--analysis-key", "mixed_cube_refinement", "--data", str(sources["report"]),
               "--data-role", f"states={sources['states']}", "--python", f"renderer={sources['renderer']}",
               "--python", f"style={sources['style']}"]
    environment = os.environ.copy(); environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False,
                               env=environment, timeout=120)
    if completed.returncode:
        raise RuntimeError(f"Initializer failed; preserve created files.\n{completed.stdout}\n{completed.stderr}")
    created = [line.partition("已创建版本包：")[2].strip() for line in completed.stdout.splitlines()
               if line.startswith("已创建版本包：")]
    if len(created) != 1:
        raise RuntimeError("Cannot identify one initialized package; preserve output: " + completed.stdout)
    revision = Path(created[0]).resolve()
    if revision.parent != result_root / "Figures/FigR3_mixed_cube_refinement" or not revision.is_dir():
        raise ValueError("Initializer destination is outside the requested FigR3 parent")
    prefix = revision.name
    copies = {"report": revision / f"01_{prefix}_data.json", "states": revision / f"01a_{prefix}_data_states.npz",
              "renderer": revision / f"03a_{prefix}_renderer.py", "style": revision / f"03c_{prefix}_style.py"}
    for role, source in sources.items():
        if _sha256(source) != hashes[role] or _sha256(copies[role]) != hashes[role]:
            raise ValueError(f"Source/copy drift for {role}; preserve incomplete package")
    notebook = revision / f"03_{prefix}_plot.ipynb"
    notebook.write_text(json.dumps(_notebook_payload(prefix, hashes), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    methods = revision / f"02_{prefix}_methods.txt"
    original = methods.read_text(encoding="utf-8")
    automatic = original[original.index("## 自动记录"):]
    source_lines = "\n".join(f"- 来源 {role}: {source.as_posix()}；SHA-256={hashes[role]}；物理副本={copies[role].name}"
                             for role, source in sources.items())
    methods.write_text(f"""# 图件方法与验证记录

## 人工填写内容
- 风格来源: cb-plot-unified-style；项目批准的160dpi紧凑探索例外，每主轴4×4英寸、显式边距、可编辑SVG。所有非默认字段由StyleOverride记录。
- 用户提供的期刊规格: 未指定；按项目探索用途执行，不是600dpi投稿终稿。
- 03_材料方法来源: 项目稳定绘图实现src/prl/rendering/mixed_cube_refinement.py；未采用03_材料方法及理论模型目录，当前包保存renderer/style物理快照及下列哈希。原始数值状态来源由JSON登记；Notebook不调用求解器。
- 数据/模型变换: 固定P3/P2、kappa=100、原MMS/Q8；序列4/8/12，主阶次ln(E8/E12)/ln(1.5)，历史4→8另列。三误差和实际保存态来自JSON/NPZ，缺失不合成。A为真实n12网格及BC；D-F只取实际n12初/中/末状态和参考Z/L=0.5已有节点，分片线性显示，几何×30、色值不放大。
- 统计方法与不确定性: 确定性数值资格，无生物学样本或推断统计；不生成p值/置信区间。原阶次门3.5/2.5/2.5及绝对门保持；convergence.status直接显示。原2/4/8 L2阶及原心室failed保留；算法Newton迭代不是生理时间。
- 生物学分组颜色: 不适用；颜色只区分数值误差、边界类型和未放大位移。
- 人工/代理视觉验收: 待检查
- 执行边界: 本helper仅准备输入/Notebook，未执行绘图、未生成PNG/SVG，不标记视觉或科学通过。执行、目检、冻结分步完成。
- 运行缓存: Notebook只在结果根07_ai_files/<PREFIX>_runtime建立过程缓存及所有权README；Jupyter启动临时目录由调用方限定到已批准结果根；不自动删除。
{source_lines}
- 初始化器来源: {initializer.as_posix()}；SHA-256={_sha256(initializer)}
- 打包helper来源: {Path(__file__).resolve().as_posix()}；SHA-256={_sha256(Path(__file__))}

{automatic}""", encoding="utf-8", newline="\n")
    return {"status": "prepared_not_executed", "revision_dir": str(revision), "prefix": prefix,
            "notebook": str(notebook), "methods": str(methods), "source_sha256": hashes,
            "initializer_stdout": completed.stdout, "initializer_stderr": completed.stderr,
            "next_commands_run_separately_with_visual_review_between": [
                [sys.executable, "-B", "-X", "utf8", str(validator), str(revision), option]
                for option in ("--execute", "--visual-qa-pass", "--mark-final")],
            "additional_FEM_solves": 0, "PNG_SVG_generated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_root", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--figure-skill", type=Path, default=Path.home() / ".codex/skills/cb-paper-figure-workflow")
    parser.add_argument("--style-source", type=Path,
                        default=Path.home() / ".codex/skills/cb-plot-unified-style/assets/cb_plot_unified_style.py")
    parser.add_argument("--prepare-only", action="store_true", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.result_root, args.workspace, args.figure_skill, args.style_source),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
