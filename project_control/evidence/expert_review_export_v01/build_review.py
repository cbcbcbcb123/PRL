"""Create-only desktop export for the user's 2026-09-18 expert-review request.

Default is a read-only export plan. --build copies the selected sources, verifies
them and creates one ZIP. No deletion, network, solver, mesher or Notebook calls.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import quote
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / 'src'
RESULTS = REPO.parent / 'PRL-results' / 'ventricle_fem'
DESKTOP = Path(r'C:\Users\chenb\Desktop')
PACKAGE = 'PRL_FEM_Expert_Review_20260918_v01'
TARGET = DESKTOP / PACKAGE
BASE_HEAD = '1913bfb'
STAGES = {
    'f6s1s9_contour_active_v01_20260918': '80b0ecbe6bd35e6d00479fbeb1e424c89969e862a01bdb0885bb43dab9734c2b',
    'f6s2d1_3d_fine_pressure_v01_20260918': '7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4',
    'f6s2d2a_mesh_quality_v01_20260918': 'c3df60d71c49de891d41e5c20b3fb01eddd922ef4ba3f8591a912b77a0cb24da',
    'f6s2d2b_unstructured_v01_20260918': 'c6528c6a25ca3affdef4fe15a9af6288ad121fb79aef57873a0d3a4f1df23282',
}
SEEDS = [
    'prl.fem.fenicsx_ventricle', 'prl.fem.ventricle_geometry', 'prl.fem.ventricle_protocol',
    'prl.fem.unstructured_geometry', 'prl.fem.ventricle_unstructured',
    'prl.verification.ventricle_3d', 'prl.verification.mesh_equivalence',
    'prl.verification.saved_gmsh', 'prl.verification.tetra_quality',
    'prl.verification.ventricle_mesh_probe', 'prl.fem.fenicsx_pressure',
    'prl.fem.fenicsx_contour_pressure', 'prl.fem.fenicsx_contour',
    'prl.verification.fenicsx_contour_active',
]
NAMESPACE_ADAPTERS = {'prl.fem', 'prl.runs', 'prl.verification'}
DOCUMENTS = [
    'docs/adr/0002-fenicsx-primary-fem-backend.md',
    'project_control/ventricle_fem_only_measured_contour_decision_v01.md',
    'project_control/ventricle_development_fsg_idealized_public_data_decision_v01.md',
    'project_control/ventricle_3d_before_growth_decision_v01.md',
    'project_control/ventricle_fem_idealized_3d_contract_v01.md',
    'project_control/ventricle_fem_idealized_3d_execution_v01.md',
    'project_control/ventricle_fem_idealized_3d_resume_contract_v01.md',
    'project_control/ventricle_fem_idealized_3d_resume_execution_v01.md',
    'project_control/ventricle_fem_3d_fine_pressure_contract_v01.md',
    'project_control/ventricle_fem_3d_fine_pressure_execution_v01.md',
    'project_control/ventricle_fem_3d_mesh_quality_contract_v01.md',
    'project_control/ventricle_fem_3d_mesh_quality_execution_v01.md',
    'project_control/ventricle_fem_3d_unstructured_adoption_v01.md',
    'project_control/ventricle_fem_3d_unstructured_comparison_contract_v01.md',
    'project_control/ventricle_fem_3d_unstructured_execution_v01.md',
    'project_control/ventricle_fem_contour_active_contract_v01.md',
    'project_control/ventricle_fem_contour_active_execution_v01.md',
]
ROOT_FILES = set('''configuration.json summary.json verification.json post_verification.json
delivery_audit.json execution.json command.json docker_version.json source_hashes.json
delivery_source_hashes.json delivery_environment.json tests.json tests_after_rendering.json
visual_qa.json geometry_source.npz input_identities.json mechanical_identity.json
stdout.log stderr.log failure.json failure_history.json failure_state.npz
mesh_diagnostic.json quality_report.json cell_metrics.npz copied_identities.json
audit_input_manifest.json cross_platform_agreement.json boundary_observations.json
continuation_ledger.json last_valid.json solver_trace.jsonl candidate_execution.json
fixed_surfaces.msh before_optimization.msh candidate.msh gmsh_environment.json
gmsh_log.json gmsh_options.opt'''.split())
PREFIXES = {'figures', 'input', 'sources_at_execution', 'sources_at_delivery', 'prerequisite'}
DUPLICATES = {
    'f6s2d2a_mesh_quality_v01_20260918': {
        'input/M0_mesh.npz': 'retained/M0_mesh.npz',
        'input/M0_state_pressure_1.npz': 'retained/M0_state_pressure_1.npz',
        'input/M1_mesh.npz': 'raw/M1_mesh.npz',
        'input/M1_state_pressure_1.npz': 'raw/M1_state_pressure_1.npz',
    },
    'f6s2d2b_unstructured_v01_20260918': {
        'retained/M1_mesh.npz': 'raw/M1_mesh.npz',
        'retained/M1_state_pressure_1.npz': 'raw/M1_state_pressure_1.npz',
    },
}
FIGURES = [
    (list(STAGES)[0], 'FigS1S9_active_overview', '二维：主动加载资格',
     'p/μ=0.02，8个新增平衡态通过本阶段数值门；最大激活缩腔约1.85%。非实验验证。'),
    (list(STAGES)[0], 'FigS1S9_active_states', '二维：5个真实载荷状态',
     'Ta/μ=0、0.025、0.05、0.075、0.1。实际1倍形变；这些不是生理时间帧。'),
    (list(STAGES)[1], 'FigS2D1_3d_mesh_comparison', '三维：结构、应力及局部体积',
     '首压力平衡已收敛；M0/M1局部体积门仍failed。固定基底、外壁自由、内壁随动压力。'),
    (list(STAGES)[2], 'FigS2D2A_mesh_quality', '三维：形状质量与体积误差',
     '保存状态只读诊断；不能从相关性认定网格形状为唯一原因。未增加FEM求解。'),
    (list(STAGES)[3], 'FigS2D2B_unstructured', '最新：同边界非结构化候选',
     'q05改善4.44%未达5%门；最差q下降。原读取错误与候选均保留；候选FEM not_run。'),
]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(path, boundary):
    path = Path(path).absolute()
    boundary = Path(boundary).absolute()
    if not path.is_relative_to(boundary) or path == boundary:
        raise ValueError('Path outside exact source boundary: ' + str(path))
    for current in [path, *path.parents]:
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            raise ValueError('Reparse/link excluded: ' + str(current))
        if current == boundary:
            break
    return path


def source_module(name):
    base = SOURCE.joinpath(*name.split('.'))
    for path in [base.with_suffix('.py'), base / '__init__.py']:
        if path.is_file():
            return path
    return None


def dependency_closure():
    pending = list(SEEDS)
    found, graph, external = {}, {}, set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        path = source_module(name)
        if path is None:
            raise ValueError('Missing local module: ' + name)
        safe_path(path, REPO)
        found[name] = path
        parents = ['.'.join(name.split('.')[:i]) for i in range(1, len(name.split('.')))]
        references = set(parents)
        if name in NAMESPACE_ADAPTERS:
            # Keep the unmodified eager-export original separately. The exported
            # review namespace must not pull retired DCM runners into FEM imports.
            graph[name] = parents
            pending.extend(parents)
            continue
        package = name if path.name == '__init__.py' else name.rsplit('.', 1)[0]
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            imports = []
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = importlib.util.resolve_name('.' * node.level + (node.module or ''), package) if node.level else node.module
                if base:
                    imports.append(base)
                    imports.extend(base + '.' + alias.name for alias in node.names
                                   if source_module(base + '.' + alias.name) is not None)
            for module in imports:
                if module == 'prl' or module.startswith('prl.'):
                    if source_module(module) is None:
                        raise ValueError('Unresolved local import: ' + name + ' -> ' + module)
                    references.add(module)
                else:
                    external.add(module.split('.')[0])
        graph[name] = sorted(references)
        pending.extend(references)
    if any(any(word in name for word in ['simucell', 'myocardial', 'dcm']) for name in found):
        raise ValueError('Unexpected retired-route dependency; inspect before exporting')
    return found, {'seeds': SEEDS, 'modules': sorted(found), 'local_import_graph': graph,
        'external_import_roots': sorted(external), 'static_import_closure': 'passed',
        'namespace_adapters': sorted(NAMESPACE_ADAPTERS),
        'adapter_scope': 'Export-only __init__.py files remove eager legacy imports; scientific modules unchanged. Original initializers saved in PRL/packaging_originals.',
        'limits': 'Core review subset, not the complete prl CLI. Dynamic imports and production solves were not executed.',
        'production_runtime': {'tag': 'dolfinx/dolfinx:v0.11.0',
            'image': 'sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8',
            'gmsh_saved_candidate': '4.15.2', 'meshio_readback': '5.3.5'}}


def evidence_selection(name, expected_hash):
    root = RESULTS / name
    manifest = safe_path(root / 'manifest.json', RESULTS)
    if digest(manifest) != expected_hash:
        raise ValueError('Frozen manifest changed: ' + name)
    entries = json.loads(manifest.read_text(encoding='utf-8'))['files']
    selected, omitted = [], []
    for entry in entries:
        relative = Path(entry['path'])
        source = safe_path(root / relative, RESULTS)
        if source.stat().st_size != entry['bytes'] or digest(source) != entry['sha256']:
            raise ValueError('Original frozen evidence changed: ' + str(source))
        first = relative.parts[0]
        keep = entry['path'] in ROOT_FILES or first in PREFIXES
        if not name.startswith('f6s1s9_') and first in {'raw', 'retained', 'iterates', 'offline'}:
            keep = True
        if '__pycache__' in relative.parts:
            keep = False
        duplicate = DUPLICATES.get(name, {}).get(relative.as_posix())
        if duplicate:
            canonical = RESULTS / 'f6s2d1_3d_fine_pressure_v01_20260918' / duplicate
            if digest(canonical) != entry['sha256']:
                raise ValueError('Purported duplicate differs: ' + str(source))
            keep = False
        if keep:
            selected.append({**entry, 'original_path': entry['path'], 'package_path': entry['path']})
        else:
            reason = ('Large 2D full-field/iteration data omitted; complete plotted source data retained'
                      if name.startswith('f6s1s9_') and first in {'raw', 'retained', 'iterates'}
                      else 'Nonessential host/storage bookkeeping, duplicate preview/data, or historical portal omitted')
            omission = {**entry, 'reason': reason}
            if duplicate:
                omission.update(reason='Identical bytes retained once in the D1 evidence; no source deletion',
                    identical_copy_in_package='PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/' + duplicate)
            omitted.append(omission)
    if not selected or not any(x['path'] == 'summary.json' for x in selected):
        raise ValueError('Incomplete evidence selection: ' + name)
    return {'name': name, 'root': root, 'manifest_sha256': expected_hash,
        'selected': selected, 'omitted': omitted, 'source_manifest': manifest}


def plan():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    if not head.startswith(BASE_HEAD):
        raise ValueError('Code snapshot moved; update the review scope before exporting: ' + head)
    modules, dependencies = dependency_closure()
    copies = []
    for name, path in sorted(modules.items()):
        relative = path.relative_to(REPO)
        destination = Path('PRL') / ('packaging_originals' if name in NAMESPACE_ADAPTERS else '') / relative
        copies.append((path, destination, 'original eager initializer' if name in NAMESPACE_ADAPTERS else 'current core: ' + name))
    for relative in DOCUMENTS:
        copies.append((safe_path(REPO / relative, REPO), Path('PRL') / relative, 'original project record'))
    for filename, destination in [('brief.md', '01_项目进展与模型.md'),
            ('questions.md', '02_专家问题.md'), ('reading.md', '03_代码导读与复核.md'),
            ('review_check.py', 'review_check.py')]:
        copies.append((HERE / filename, Path(destination), 'new review document/checker'))
    stages = [evidence_selection(name, frozen) for name, frozen in STAGES.items()]
    for stage in stages:
        destination = Path('PRL-results') / 'ventricle_fem' / stage['name']
        for entry in stage['selected']:
            copies.append((stage['root'] / entry['path'], destination / entry['path'], 'frozen result evidence'))
        copies.append((stage['source_manifest'], destination / 'SOURCE_MANIFEST.json', 'original full-stage manifest; package is a subset'))
    if len({str(destination).lower() for _, destination, _ in copies}) != len(copies):
        raise ValueError('Export destination collision')
    records = []
    for source, destination, role in copies:
        safe_path(source, REPO if source.is_relative_to(REPO) else RESULTS)
        records.append({'source': str(source), 'destination': destination.as_posix(),
            'bytes': source.stat().st_size, 'source_sha256': digest(source), 'role': role})
    return head, copies, records, dependencies, stages


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def write_json(path, value):
    write_new(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def markdown_html(text):
    """Small escaped renderer for these controlled local review templates only."""
    output, paragraph, code = [], [], None
    lines = text.splitlines()

    def inline(value):
        value = html.escape(value)
        value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)

    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith('```'):
            flush()
            if code is None:
                code = []
            else:
                output.append('<pre>' + html.escape('\n'.join(code)) + '</pre>')
                code = None
        elif code is not None:
            code.append(line)
        elif line.startswith('|'):
            flush()
            table = []
            while index < len(lines) and lines[index].startswith('|'):
                cells = [x.strip() for x in lines[index].strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+', cell) for cell in cells):
                    tag = 'th' if not table else 'td'
                    table.append('<tr>' + ''.join(f'<{tag}>{inline(cell)}</{tag}>' for cell in cells) + '</tr>')
                index += 1
            output.append('<div class="table-wrap"><table>' + ''.join(table) + '</table></div>')
            continue
        elif line.startswith('#'):
            flush()
            level = min(len(line) - len(line.lstrip('#')) + 1, 4)
            output.append(f'<h{level}>' + inline(line.lstrip('# ')) + f'</h{level}>')
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
        index += 1
    flush()
    return '\n'.join(output)


def portal(head, dependencies):
    cards = []
    for stage, fig, title, caption in FIGURES:
        prefix = fig + '_v01_20260918'
        base = Path('PRL-results/ventricle_fem') / stage / 'figures' / fig / prefix
        png = (base / ('04_' + prefix + '.png')).as_posix()
        buttons = []
        for label, file in [('PNG', '04_' + prefix + '.png'), ('SVG', '05_' + prefix + '.svg'),
                            ('Notebook', '03_' + prefix + '_plot.ipynb'), ('方法', '02_' + prefix + '_methods.txt')]:
            buttons.append(f'<a href="{quote((base / file).as_posix())}">{label}</a>')
        cards.append(f'<article><h3>{title}</h3><p>{caption}</p><a href="{quote(png)}">'
                     f'<img loading="lazy" src="{quote(png)}" alt="{title}"></a><nav>{" · ".join(buttons)}</nav></article>')
    docs = ''.join(f'<li><a href="{quote("PRL/" + name)}">{html.escape(Path(name).name)}</a></li>' for name in DOCUMENTS)
    code = ''.join(f'<li><a href="{quote("PRL/" + source_module(name).relative_to(REPO).as_posix())}">{name}</a></li>' for name in SEEDS)
    evidence = ''.join(f'<li>{name}: <a href="PRL-results/ventricle_fem/{name}/summary.json">裁决</a> · '
                      f'<a href="PRL-results/ventricle_fem/{name}/SELECTION.json">保留/省略清单</a></li>' for name in STAGES)
    body = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PRL · FEM专家评审 · 2026-09-18</title><style>
:root{{color-scheme:light;--ink:#18313c;--green:#14584d;--line:#d7e2e3}}
*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f5;color:var(--ink);font:16px/1.8 "Microsoft YaHei",system-ui,sans-serif}}
main{{max-width:1140px;margin:auto;padding:40px 28px 80px}}header{{padding:30px;background:var(--green);color:white;border-radius:14px}}
h1{{font-size:32px;line-height:1.35;margin:10px 0}}h2{{font-size:25px;margin-top:30px}}h3{{font-size:20px}}h4{{font-size:18px}}
a{{color:#076665;text-underline-offset:3px}}header a{{color:white}}nav{{display:flex;gap:18px;flex-wrap:wrap}}section,article{{background:white;padding:26px;margin:22px 0;border:1px solid var(--line);border-radius:12px}}
article img{{display:block;width:100%;height:auto;border:1px solid #e5eded}}.alert{{border-left:5px solid #b74536;background:#fff7f3;padding:18px}}
.status{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}.status div{{background:white;padding:18px;border:1px solid var(--line);border-radius:10px}}
.small{{font-size:14px;color:#52656d}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border:1px solid var(--line);padding:8px 12px;text-align:left}}th{{background:#eaf3f1}}.table-wrap{{overflow:auto}}
pre{{background:#edf3f5;padding:18px;overflow:auto;font-size:13px}}code{{font-family:Consolas,monospace}}li{{margin-bottom:7px;overflow-wrap:anywhere}}details summary{{cursor:pointer;font-weight:600}}
@media(max-width:700px){{main{{padding:16px}}.status{{grid-template-columns:1fr}}section,article{{padding:14px}}h1{{font-size:26px}}}}
@media print{{body{{background:white}}main{{padding:0}}section,article{{break-inside:avoid}}details{{display:block}}}}
</style><main><header><div>PRL / FEM-only / INVITED EXPERT REVIEW / 2026-09-18</div>
<h1>斑马鱼心室：核心模型、当前证据与关键卡点</h1><p>先让三维固体可信，再研究收缩—血流—发育—ECM反馈。</p>
<nav><a href="#brief">模型与进展</a><a href="#figures">五套原始图包</a><a href="#questions">专家问题</a><a href="#code">代码与复核</a></nav></header>
<div class="status"><div><b>二维低压主动加载：passed</b><br>约1.85%缩腔；数值资格，不是生物验证。</div>
<div><b>三维首压力：failed</b><br>平衡收敛，局部体积偏离1.45%仍超1%门。</div>
<div><b>三维FSI / 生长：not_run</b><br>尚无流体、周期生长或实验校准。</div></div>
<p class="alert">本包保留原失败，不放宽门限。最新非结构化候选质量门failed，候选FEM未运行。请勿把工程复核passed解读为科学通过。</p>
<p class="small">当前源码 main / {head[:12]}；精选 {len(dependencies['modules'])} 个本地模块。无.git、DCM、求解器二进制或大批历史输出。解压后离线浏览，不需安装或启动服务。</p>
<section id="brief">{markdown_html((HERE / 'brief.md').read_text(encoding='utf-8'))}</section>
<h2 id="figures">原始结构图与结果图</h2><p>点击看原图；每个目录同时保留source data、方法、Notebook和辅助代码。未在本次执行Notebook。</p>{''.join(cards)}
<section id="questions">{markdown_html((HERE / 'questions.md').read_text(encoding='utf-8'))}</section>
<section id="code">{markdown_html((HERE / 'reading.md').read_text(encoding='utf-8'))}<h3>核心入口</h3><ol>{code}</ol>
<details><summary>原始合同、执行记录及路线决定（历史链接可能指向原仓）</summary><ul>{docs}</ul></details>
<h3>正式裁决与选择范围</h3><ul>{evidence}</ul>
<nav><a href="review_check.py">只读复核脚本</a><a href="DEPENDENCIES.json">依赖闭包</a><a href="MANIFEST.json">文件哈希</a><a href="PROVENANCE.json">复制来源</a><a href="PACKAGE_CHECK.json">交付检查</a></nav></section>
<section><h3>可编辑文字稿</h3><nav><a href="{quote('01_项目进展与模型.md')}">项目进展与模型</a><a href="{quote('02_专家问题.md')}">专家问题</a><a href="{quote('03_代码导读与复核.md')}">代码导读与复核</a></nav>
<p class="small">不上传外部服务、不代替用户发送专家；原始结果与原图未改动。专家返回意见将作为外部指导另行登记，不自动变为执行授权。</p></section></main></html>'''
    return body


def build(head, copies, records, dependencies, stages):
    archive = DESKTOP / (PACKAGE + '.zip')
    receipt_path = HERE / 'export_receipt.json'
    if TARGET.exists() or archive.exists() or receipt_path.exists():
        raise FileExistsError('Create-only export already exists; do not overwrite')
    if not DESKTOP.is_dir() or DESKTOP.is_symlink() or TARGET.parent != DESKTOP:
        raise ValueError('Unexpected desktop target')
    total = sum(item['bytes'] for item in records)
    if total > 256 * 1024**2:
        raise ValueError('Review selection unexpectedly exceeds 256 MiB; inspect before copying')
    if shutil.disk_usage(DESKTOP).free < 2 * total + 1024**3:
        raise ValueError('Insufficient desktop disk headroom')
    TARGET.mkdir()
    for (source, relative, role), record in zip(copies, records):
        destination = TARGET / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        shutil.copy2(source, destination)
        if digest(destination) != record['source_sha256'] or digest(source) != record['source_sha256']:
            raise ValueError('Source/copy changed during export: ' + str(source))
    adapters = []
    for name in sorted(NAMESPACE_ADAPTERS):
        path = TARGET / 'PRL' / source_module(name).relative_to(REPO)
        write_new(path, '"""Review-export namespace adapter, not a scientific implementation.\n'
                  'Only removes eager legacy exports. Original initializer is preserved under\n'
                  'PRL/packaging_originals/. Production source was not edited.\n"""\n')
        adapters.append({'module': name, 'destination': path.relative_to(TARGET).as_posix(),
                         'reason': 'Prevent package initialization from importing retired DCM routes'})
    for stage in stages:
        folder = TARGET / 'PRL-results' / 'ventricle_fem' / stage['name']
        write_json(folder / 'SELECTION.json', {'source_root': str(stage['root']),
            'source_manifest_sha256': stage['manifest_sha256'], 'selected': stage['selected'],
            'omitted': stage['omitted'], 'source_files_deleted': 0,
            'note': 'This review subset is not the original full run package; omissions remain at source.'})
    provenance = {'created_utc': datetime.now(timezone.utc).isoformat(), 'code_head': head,
        'scientific_head': '69d2d47', 'source_workspace': str(REPO),
        'authorization': 'User requested the current core code and progress packaged on desktop for expert review.',
        'copied_files': records, 'generated_namespace_adapters': adapters, 'stages': [{'name': s['name'],
            'destination': 'PRL-results/ventricle_fem/' + s['name'],
            'original_manifest_sha256': s['manifest_sha256']} for s in stages],
        'scientific_results_modified': False, 'new_FEM_solves': 0, 'notebooks_executed': 0,
        'external_uploads': 0, 'originals_deleted': 0, 'copy_policy': 'byte-identical, selected paths only'}
    write_json(TARGET / 'PROVENANCE.json', provenance)
    write_json(TARGET / 'DEPENDENCIES.json', dependencies)
    write_new(TARGET / '00_评审入口.html', portal(head, dependencies))
    # All validators run against the exported location, not absolute source paths.
    spec = importlib.util.spec_from_file_location('exported_review_check', TARGET / 'review_check.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    # PACKAGE_CHECK and MANIFEST are written immediately below; link placeholders
    # are not created. A full strict-link check runs after both files exist.
    numerical = checker.check_numerics(TARGET)
    write_json(TARGET / 'PACKAGE_CHECK.json', {'status': 'passed',
        'scope': 'source-copy and saved-evidence numerical reproduction; no new scientific solve',
        'copies_hash_identical': True, 'source_manifests_verified': len(stages),
        'static_core_import_closure': 'passed', 'numerics': numerical,
        'notebook_reexecution': 'not_run',
        'final_manifest_zip_and_portal_check': 'Recorded in project export receipt after archive verification'})
    files = [{'path': p.relative_to(TARGET).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}
             for p in sorted(TARGET.rglob('*')) if p.is_file()]
    write_json(TARGET / 'MANIFEST.json', {'format': 'PRL-review-sha256-v1', 'files': files,
        'note': 'Covers every package file except this manifest itself; ZIP SHA is in the project receipt.'})
    verification = checker.check_integrity(TARGET)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(TARGET.rglob('*')):
            if path.is_file():
                bundle.write(path, arcname=PACKAGE + '/' + path.relative_to(TARGET).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        expected = {PACKAGE + '/' + p.relative_to(TARGET).as_posix(): p for p in TARGET.rglob('*') if p.is_file()}
        if set(bundle.namelist()) != set(expected):
            raise ValueError('ZIP file set mismatch')
        for name, path in expected.items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != digest(path):
                raise ValueError('ZIP content differs: ' + name)
    # Recheck original scientific files after all packaging operations.
    for record in records:
        if digest(Path(record['source'])) != record['source_sha256']:
            raise ValueError('Original source changed: ' + record['source'])
    receipt = {'status': 'passed', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'folder': str(TARGET), 'zip': str(archive), 'source_head': head,
        'files': len(expected), 'folder_bytes': sum(path.stat().st_size for path in expected.values()),
        'zip_bytes': archive.stat().st_size, 'zip_sha256': digest(archive),
        'package_manifest_sha256': digest(TARGET / 'MANIFEST.json'),
        'core_modules': len(dependencies['modules']), 'full_figure_packages': len(FIGURES),
        'copied_files': len(records), 'integrity': verification, 'numerics': numerical,
        'zip_crc_and_all_file_hashes': 'passed', 'original_source_postcheck': 'passed',
        'scientific_scope_changed': False, 'new_FEM_solves': 0, 'new_mesher_calls': 0,
        'new_Docker_launches': 0, 'notebook_execution': 'not_run', 'deletions': 0,
        'temporary_export_folders': [], 'push': 'not_run'}
    write_json(receipt_path, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    head, copies, records, dependencies, stages = plan()
    summary = {'mode': 'build' if args.build else 'read-only plan', 'target': str(TARGET),
        'head': head, 'core_modules': dependencies['modules'], 'copy_files': len(records),
        'copy_bytes': sum(r['bytes'] for r in records), 'frozen_manifests_verified': len(stages),
        'stages': [{'name': s['name'], 'selected': len(s['selected']), 'omitted': len(s['omitted']),
                    'selected_bytes': sum(x['bytes'] for x in s['selected'])} for s in stages]}
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if args.build:
        build(head, copies, records, dependencies, stages)


if __name__ == '__main__':
    main()
