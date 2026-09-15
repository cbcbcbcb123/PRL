"""Render and strictly validate the project-local PRL cockpit.

The authoritative inputs are memory/project_cockpit/status.json and the
append-only memory/project_cockpit/task_log.jsonl.  This renderer writes only
memory/project_cockpit/index.html inside the project root.
"""

from __future__ import annotations

import argparse
import html
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COCKPIT_DIR = PROJECT_ROOT / "memory" / "project_cockpit"
STATUS_PATH = COCKPIT_DIR / "status.json"
TASK_LOG_PATH = COCKPIT_DIR / "task_log.jsonl"
INDEX_PATH = COCKPIT_DIR / "index.html"
RETIRED_PATHS_PATH = (
    PROJECT_ROOT
    / "project_control"
    / "evidence"
    / "repository_cleanup_v01"
    / "retired_paths_v01.json"
)


def escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def project_href(reference: str) -> str:
    normalized = effective_evidence_reference(reference)
    prefix = "memory/project_cockpit/"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :]
    return f"../../{normalized}"


def load_retired_paths() -> tuple[tuple[str, ...], str | None]:
    if not RETIRED_PATHS_PATH.exists():
        return (), None
    payload = json.loads(RETIRED_PATHS_PATH.read_text(encoding="utf-8"))
    prefixes = tuple(str(item).replace("\\", "/").rstrip("/") for item in payload.get("retired_prefixes", []))
    mapping = payload.get("mapping_document")
    return prefixes, str(mapping).replace("\\", "/") if mapping else None


def effective_evidence_reference(reference: str) -> str:
    normalized = reference.replace("\\", "/")
    if (PROJECT_ROOT / normalized).exists():
        return normalized
    prefixes, mapping = load_retired_paths()
    if mapping and any(normalized == prefix or normalized.startswith(prefix + "/") for prefix in prefixes):
        return mapping
    return normalized


def status_badge(status: str) -> str:
    normalized = str(status).lower()
    visible = normalized.replace("_", " ").upper()
    return f'<span class="status status-{escaped(normalized)}">{escaped(visible)}</span>'


def evidence_links(references: list[str]) -> str:
    if not references:
        return ""
    links = []
    for index, reference in enumerate(references, start=1):
        effective = effective_evidence_reference(reference)
        label = "退役映射" if effective != reference.replace("\\", "/") else "证据"
        links.append(f'<a href="{escaped(project_href(reference))}">{label} {index}</a>')
    return '<details><summary>查看证据</summary><div class="evidence">' + " · ".join(links) + "</div></details>"


def load_status() -> dict:
    return json.loads(STATUS_PATH.read_text(encoding="utf-8"))


def load_recent_tasks(limit: int = 4) -> list[dict]:
    tasks: list[dict] = []
    for raw_line in TASK_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if raw_line.strip():
            tasks.append(json.loads(raw_line))
    return tasks[-limit:][::-1]


def render_cockpit() -> None:
    status = load_status()
    project = status["project"]
    overview = project["model_overview"]
    active_work = status.get("active_work", [])
    next_actions = status.get("next_actions", [])
    current_work = active_work[-1] if active_work else {"title": "无", "status": "unknown", "summary": ""}
    next_action = next_actions[0] if next_actions else {"title": "未登记", "status": "unknown", "summary": ""}

    roadmap_html = "".join(
        f'''<article class="stage stage-{escaped(item["status"])}" title="{escaped(item["summary"])}">
<span class="dot"></span><strong>{escaped(item["label"])}</strong><small>{escaped(item["status"].upper())}</small></article>'''
        for item in status.get("roadmap", [])
    )
    pipeline_html = "".join(
        f'<li><span>{index}</span><strong>{escaped(label)}</strong></li>'
        for index, label in enumerate(overview.get("pipeline", []), start=1)
    )
    assumption_html = "".join(f"<li>{escaped(item)}</li>" for item in overview.get("assumptions", []))
    method_html = "".join(f"<li>{escaped(item)}</li>" for item in overview.get("methods", []))

    result_cards: list[str] = []
    for item in status.get("results", []):
        image_html = ""
        if item.get("image"):
            image_html = f'''<figure><img src="{escaped(project_href(item["image"]))}" alt="{escaped(item["title"])}">
<figcaption>{escaped(item.get("image_caption", ""))}</figcaption></figure>'''
        result_cards.append(
            f'''<article class="result-card">{image_html}<div class="card-body"><div class="card-head">{status_badge(item["status"])}<h3>{escaped(item["title"])}</h3></div>
<p class="result-summary">{escaped(item["summary"])}</p><p class="boundary"><strong>解释边界：</strong>{escaped(item.get("interpretation_boundary", ""))}</p>
{evidence_links(item.get("evidence_refs", []))}</div></article>'''
        )

    blocker_html = "".join(
        f'''<article class="brief"><div class="card-head">{status_badge(item["status"])}<h3>{escaped(item["title"])}</h3></div>
<p>{escaped(item["summary"])}</p>{evidence_links(item.get("evidence_refs", []))}</article>'''
        for item in status.get("blockers", [])
    )
    next_html = "".join(
        f'''<article class="brief"><div class="card-head">{status_badge(item["status"])}<h3>{escaped(item["title"])}</h3></div>
<p>{escaped(item["summary"])}</p>{evidence_links(item.get("evidence_refs", []))}</article>'''
        for item in next_actions
    )
    task_html = "".join(
        f'''<li><div>{status_badge(item["outcome"])} <time>{escaped(item["completed_at"])}</time></div>
<strong>{escaped(item["title"])}</strong><p>{escaped(item["summary"])}</p>{evidence_links(item.get("evidence_refs", []))}</li>'''
        for item in load_recent_tasks()
    )
    boundary_html = "".join(f"<li>{escaped(item)}</li>" for item in status.get("evidence_boundaries", []))

    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escaped(project["name"])} 项目驾驶舱</title>
<style>
:root{{--bg:#f3f6f4;--ink:#17231e;--muted:#65736c;--line:#dbe4df;--panel:#fff;--green:#176b4d;--red:#a83f38;--amber:#98651a;--blue:#326d96}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.55}}main{{max-width:1160px;margin:auto;padding:24px}}a{{color:var(--green)}}h1,h2,h3,p{{margin-top:0}}h2{{margin-bottom:12px}}section{{margin-top:22px}}
.hero{{padding:24px;border-radius:18px;background:#183f31;color:#fff}}.hero-top,.card-head,.section-head{{display:flex;align-items:center;gap:9px}}.hero-top{{justify-content:space-between}}.hero h1{{font-size:2rem;margin:0}}.hero-goal{{font-size:1.08rem;margin:15px 0 7px}}.hero-summary{{color:#cfe0d8;margin:0}}.eyebrow{{font-size:.72rem;letter-spacing:.12em;color:var(--muted)}}
.status{{display:inline-block;border-radius:999px;padding:3px 8px;font-size:.66rem;font-weight:750;white-space:nowrap}}.status-passed{{background:#d9efe5;color:#155b43}}.status-failed{{background:#f7dedd;color:#92352f}}.status-blocked{{background:#f8e9cf;color:#87570e}}.status-not_run,.status-unknown{{background:#e8ece9;color:#56625c}}
.model{{display:grid;grid-template-columns:1.05fr 1.95fr;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden}}.model-copy{{padding:20px;background:#e5f0ea}}.model-copy h3{{font-size:1rem;line-height:1.6}}.model figure{{margin:0;padding:16px}}.model figure img{{width:100%;height:300px;object-fit:contain}}figcaption{{font-size:.72rem;color:var(--muted)}}.model-detail{{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line)}}.model-detail article{{padding:16px 20px}}.model-detail article+article{{border-left:1px solid var(--line)}}.model-detail li{{font-size:.84rem;margin:4px 0}}.pipeline{{grid-column:1/-1;display:flex;gap:6px;overflow:auto;list-style:none;padding:14px 18px;margin:0;border-top:1px solid var(--line)}}.pipeline li{{min-width:120px;flex:1;text-align:center}}.pipeline span{{display:grid;place-items:center;width:28px;height:28px;margin:auto;border-radius:50%;background:#d9e9e1;color:#155b43;font-size:.72rem;font-weight:800}}.pipeline strong{{font-size:.74rem}}
.overview{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.overview article,.panel,.brief{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px}}.overview small{{color:var(--muted)}}.overview strong{{display:block;font-size:.92rem;margin:6px 0}}.overview p,.brief p{{font-size:.83rem;color:var(--muted);margin:6px 0}}
.stage-track{{display:flex;overflow:auto;background:#fff;border:1px solid var(--line);border-radius:14px;padding:15px;margin-top:12px}}.stage{{min-width:145px;flex:1;text-align:center;padding:0 9px}}.stage strong,.stage small{{display:block;font-size:.73rem}}.stage small{{color:var(--muted)}}.dot{{display:block;width:18px;height:18px;margin:0 auto 6px;border-radius:50%;background:#7a8580;box-shadow:0 0 0 3px #fff,0 0 0 5px var(--line)}}.stage-passed .dot{{background:#198754}}.stage-failed .dot{{background:#c2413b}}.stage-blocked .dot{{background:#b7791f}}
.result-grid,.decision-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.result-card{{background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden}}.result-card figure{{margin:0;background:#edf3f0;padding:12px}}.result-card img{{width:100%;height:280px;object-fit:contain}}.card-body{{padding:15px}}.card-head h3{{font-size:.96rem;margin:0}}.result-summary{{font-weight:650}}.boundary{{font-size:.8rem;color:var(--muted)}}details{{font-size:.78rem;color:var(--muted)}}.evidence{{padding-top:6px}}.brief+ .brief{{margin-top:10px}}
.timeline{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;list-style:none;padding:0}}.timeline li{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px}}.timeline time{{font-size:.7rem;color:var(--muted)}}.timeline strong{{display:block;margin-top:7px}}.timeline p{{font-size:.8rem;color:var(--muted)}}footer{{margin-top:22px;color:var(--muted);font-size:.75rem}}@media(max-width:780px){{.model,.overview,.result-grid,.decision-grid,.model-detail,.timeline{{grid-template-columns:1fr}}.model-detail article+article{{border-left:0;border-top:1px solid var(--line)}}}}
</style></head><body><main>
<header class="hero"><div class="hero-top"><div><div class="eyebrow" style="color:#b9d3c7">PROJECT COCKPIT</div><h1>{escaped(project["name"])}</h1></div>{status_badge(status["overall_status"])}</div>
<p class="hero-goal"><strong>项目目标：</strong>{escaped(project["goal"])}</p><p class="hero-summary">{escaped(status["summary"])}</p></header>
<section><div class="section-head"><div><div class="eyebrow">MODEL</div><h2>当前模型与问题</h2></div></div><div class="model"><div class="model-copy"><div class="eyebrow">CURRENT OBJECT</div><h3>{escaped(overview["simulated_object"])}</h3><p>{escaped(overview["theory"])}</p><p><strong>当前问题：</strong>{escaped(overview["current_question"])}</p></div>
<figure><img src="{escaped(project_href(overview["diagram"]))}" alt="当前模型结构"><figcaption>{escaped(overview["diagram_caption"])}</figcaption></figure>
<ol class="pipeline">{pipeline_html}</ol><div class="model-detail"><article><strong>关键假设</strong><ul>{assumption_html}</ul></article><article><strong>本阶段方法</strong><ul>{method_html}</ul></article></div></div></section>
<section><div class="eyebrow">PROGRESS</div><h2>当前进展</h2><div class="overview"><article><small>当前阶段</small><strong>{escaped(project["current_stage"])}</strong><p>{escaped(project["current_location"])}</p></article>
<article><small>正在解决</small><div class="card-head">{status_badge(current_work["status"])}<strong>{escaped(current_work["title"])}</strong></div><p>{escaped(current_work["summary"])}</p></article>
<article><small>优先下一步</small><div class="card-head">{status_badge(next_action["status"])}<strong>{escaped(next_action["title"])}</strong></div><p>{escaped(next_action["summary"])}</p></article></div><div class="stage-track">{roadmap_html}</div></section>
<section><div class="eyebrow">EVIDENCE</div><h2>当前核心结果</h2><div class="result-grid">{"".join(result_cards)}</div></section>
<section><div class="decision-grid"><div class="panel"><div class="eyebrow">HARD PART</div><h2>主要难点</h2>{blocker_html}</div><div class="panel"><div class="eyebrow">NEXT</div><h2>唯一下一步</h2>{next_html}</div></div></section>
<section><details><summary>最近任务与证据边界</summary><h3>最近更新</h3><ol class="timeline">{task_html}</ol><h3>项目范围</h3><p>{escaped(project["scope"])}</p><h3>证据边界</h3><ul>{boundary_html}</ul></details></section>
<footer>更新：{escaped(status["updated_at"])} · 证据核对：{escaped(project["evidence_checked_at"])} · 基线：{escaped(project["evidence_basis_commit"])}<br>{escaped(project["freshness_note"])}</footer>
</main></body></html>'''
    INDEX_PATH.write_text(document, encoding="utf-8")


class LocalLinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute_name = "src" if tag == "img" else "href" if tag == "a" else None
        if attribute_name is None:
            return
        for name, value in attrs:
            if name == attribute_name and value:
                self.references.append(value)


def validate_links() -> dict:
    parser = LocalLinkCollector()
    parser.feed(INDEX_PATH.read_text(encoding="utf-8"))
    missing: list[str] = []
    checked: list[str] = []
    for reference in parser.references:
        lowered = reference.lower()
        if lowered.startswith(("http://", "https://", "mailto:", "data:", "#")):
            continue
        local_part = unquote(reference.split("#", 1)[0].split("?", 1)[0])
        candidate = (INDEX_PATH.parent / local_part).resolve()
        checked.append(reference)
        if not candidate.exists():
            missing.append(reference)
    evidence_references: list[str] = []

    def gather_references(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "evidence_refs":
                    evidence_references.extend(child)
                elif key in ("diagram", "image") and isinstance(child, str):
                    evidence_references.append(child)
                else:
                    gather_references(child)
        elif isinstance(value, list):
            for child in value:
                gather_references(child)

    gather_references(load_status())
    gather_references(load_recent_tasks(limit=100000))
    retired: list[str] = []
    for reference in sorted(set(evidence_references)):
        effective = effective_evidence_reference(reference)
        if effective != reference.replace("\\", "/"):
            retired.append(reference)
        if not (PROJECT_ROOT / effective).exists():
            missing.append(reference)
    return {
        "status": "passed" if not missing else "failed",
        "checked_local_links": len(checked),
        "checked_evidence_paths": len(set(evidence_references)),
        "retired_evidence_paths": retired,
        "missing": missing,
    }


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("mode", choices=("render", "validate"))
    argument_parser.add_argument("--strict-links", action="store_true")
    arguments = argument_parser.parse_args()
    if arguments.mode == "render":
        render_cockpit()
        print(json.dumps({"status": "passed", "output": str(INDEX_PATH)}, ensure_ascii=False))
        return 0
    verdict = validate_links()
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 1 if arguments.strict_links and verdict["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
