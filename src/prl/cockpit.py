"""Small, stable renderer and strict-link validator for the project cockpit."""

from __future__ import annotations

import html
from html.parser import HTMLParser
import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from .workspace import find_workspace


def _paths(workspace: Path) -> tuple[Path, Path, Path, Path]:
    cockpit = workspace / "memory/project_cockpit"
    return (
        cockpit / "status.json",
        cockpit / "task_log.jsonl",
        cockpit / "index.html",
        workspace / "project_control/evidence/repository_cleanup_v01/retired_paths_v01.json",
    )


def _retired(workspace: Path) -> tuple[tuple[str, ...], str | None]:
    _, _, _, path = _paths(workspace)
    if not path.is_file():
        return (), None
    payload = json.loads(path.read_text(encoding="utf-8"))
    prefixes = tuple(str(value).replace("\\", "/").rstrip("/") for value in payload.get("retired_prefixes", []))
    mapping = payload.get("mapping_document")
    return prefixes, str(mapping).replace("\\", "/") if mapping else None


def _effective(workspace: Path, reference: str) -> str:
    normalized = reference.replace("\\", "/")
    if (workspace / normalized).exists():
        return normalized
    prefixes, mapping = _retired(workspace)
    if mapping and any(normalized == prefix or normalized.startswith(prefix + "/") for prefix in prefixes):
        return mapping
    return normalized


def _href(workspace: Path, reference: str) -> str:
    effective = _effective(workspace, reference)
    prefix = "memory/project_cockpit/"
    return effective[len(prefix) :] if effective.startswith(prefix) else f"../../{effective}"


def _badge(value: str) -> str:
    normalized = str(value).lower()
    return f'<span class="status {html.escape(normalized)}">{html.escape(normalized.upper())}</span>'


def _links(workspace: Path, references: list[str]) -> str:
    return " ".join(
        f'<a href="{html.escape(_href(workspace, reference), quote=True)}">证据 {index}</a>'
        for index, reference in enumerate(references, start=1)
    )


def render_cockpit(workspace: Path | str | None = None) -> dict[str, Any]:
    root = find_workspace(workspace)
    status_path, task_path, index_path, _ = _paths(root)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    project = status["project"]
    overview = project["model_overview"]
    tasks = [json.loads(line) for line in task_path.read_text(encoding="utf-8").splitlines() if line.strip()][-4:][::-1]

    def cards(items: list[dict[str, Any]], *, images: bool = False) -> str:
        rendered = []
        for item in items:
            image = ""
            if images and item.get("image"):
                image = f'<img src="{html.escape(_href(root, item["image"]), quote=True)}" alt="result">'
            rendered.append(
                f'<article>{image}<div>{_badge(item.get("status", item.get("outcome", "unknown")))}'
                f'<h3>{html.escape(str(item.get("title", "")))}</h3>'
                f'<p>{html.escape(str(item.get("summary", "")))}</p>'
                f'{_links(root, item.get("evidence_refs", []))}</div></article>'
            )
        return "".join(rendered)

    roadmap = "".join(
        f'<li>{_badge(item["status"])} <strong>{html.escape(item["label"])}</strong><small>{html.escape(item["summary"])}</small></li>'
        for item in status.get("roadmap", [])
    )
    assumptions = "".join(f"<li>{html.escape(value)}</li>" for value in overview.get("assumptions", []))
    methods = "".join(f"<li>{html.escape(value)}</li>" for value in overview.get("methods", []))
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(project["name"])}</title>
<style>:root{{--ink:#18231e;--muted:#617168;--line:#d9e3dd;--green:#176b4d;--bg:#f4f7f5}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Segoe UI","Microsoft YaHei",sans-serif}}main{{max-width:1120px;margin:auto;padding:24px}}header{{background:#173f31;color:white;padding:26px;border-radius:18px}}h1{{margin:0}}h2{{margin:26px 0 12px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}article,.model{{background:white;border:1px solid var(--line);border-radius:13px;padding:16px}}article img,.model img{{width:100%;height:270px;object-fit:contain;background:#edf3f0}}.status{{display:inline-block;padding:2px 7px;border-radius:99px;background:#e8ece9;font-size:11px;font-weight:700}}.passed{{background:#d9efe5;color:#155b43}}.failed{{background:#f7dedd;color:#92352f}}.blocked{{background:#f8e9cf;color:#87570e}}a{{color:var(--green)}}p,small{{color:var(--muted)}}header p{{color:#d8e6df}}ol.roadmap{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:0;list-style:none}}ol.roadmap li{{background:white;border:1px solid var(--line);padding:12px;border-radius:12px}}ol.roadmap small{{display:block;margin-top:6px}}@media(max-width:760px){{.grid,ol.roadmap{{grid-template-columns:1fr}}}}</style></head><body><main>
<header>{_badge(status["overall_status"])}<h1>{html.escape(project["name"])}</h1><p><strong>目标：</strong>{html.escape(project["goal"])}</p><p>{html.escape(status["summary"])}</p></header>
<h2>当前模型与问题</h2><section class="model"><h3>{html.escape(overview["simulated_object"])}</h3><p>{html.escape(overview["theory"])}</p><p><strong>当前问题：</strong>{html.escape(overview["current_question"])}</p><img src="{html.escape(_href(root, overview["diagram"]), quote=True)}" alt="model"><div class="grid"><div><h3>关键假设</h3><ul>{assumptions}</ul></div><div><h3>本阶段方法</h3><ul>{methods}</ul></div></div></section>
<h2>阶段</h2><ol class="roadmap">{roadmap}</ol>
<h2>核心结果</h2><section class="grid">{cards(status.get("results", []), images=True)}</section>
<h2>主要难点与唯一下一步</h2><section class="grid">{cards(status.get("blockers", []))}{cards(status.get("next_actions", []) )}</section>
<h2>最近执行</h2><section class="grid">{cards(tasks)}</section>
<footer><p>更新 {html.escape(status["updated_at"])} · 基线 {html.escape(project["evidence_basis_commit"])}</p></footer></main></body></html>'''
    index_path.write_text(document, encoding="utf-8")
    return {"schema_version": "prl.cockpit.render.v1", "status": "passed", "output": str(index_path)}


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        wanted = "src" if tag == "img" else "href" if tag == "a" else None
        if wanted:
            self.references.extend(value for name, value in attrs if name == wanted and value)


def validate_cockpit_links(workspace: Path | str | None = None) -> dict[str, Any]:
    root = find_workspace(workspace)
    status_path, task_path, index_path, _ = _paths(root)
    parser = _Collector()
    parser.feed(index_path.read_text(encoding="utf-8"))
    missing: list[str] = []
    for reference in parser.references:
        if reference.lower().startswith(("http://", "https://", "mailto:", "data:", "#")):
            continue
        local = unquote(reference.split("#", 1)[0].split("?", 1)[0])
        if not (index_path.parent / local).resolve().exists():
            missing.append(reference)
    evidence: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "evidence_refs":
                    evidence.extend(child)
                elif key in ("diagram", "image") and isinstance(child, str):
                    evidence.append(child)
                else:
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(json.loads(status_path.read_text(encoding="utf-8")))
    for line in task_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            collect(json.loads(line))
    for reference in sorted(set(evidence)):
        if not (root / _effective(root, reference)).exists():
            missing.append(reference)
    return {
        "schema_version": "prl.cockpit.links.v1",
        "status": "passed" if not missing else "failed",
        "html_links": len(parser.references),
        "evidence_paths": len(set(evidence)),
        "missing": sorted(set(missing)),
    }
