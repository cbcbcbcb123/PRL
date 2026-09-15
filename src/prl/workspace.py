"""Workspace discovery shared by stable PRL commands."""

from __future__ import annotations

from pathlib import Path


WORKSPACE_MARKERS = ("START_HERE.md", "pyproject.toml")


class WorkspaceNotFoundError(ValueError):
    """Raised when a path is not inside a recognizable PRL workspace."""


def find_workspace(start: str | Path | None = None) -> Path:
    """Return the nearest ancestor containing all PRL workspace markers."""

    candidate = Path.cwd() if start is None else Path(start)
    candidate = candidate.resolve(strict=True)
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if all((directory / marker).is_file() for marker in WORKSPACE_MARKERS):
            return directory
    marker_text = ", ".join(WORKSPACE_MARKERS)
    raise WorkspaceNotFoundError(
        f"No PRL workspace containing {marker_text} was found from {candidate}"
    )
