"""Stable application and evidence interfaces for the PRL project."""

from .workspace import WorkspaceNotFoundError, find_workspace

__all__ = ["WorkspaceNotFoundError", "find_workspace"]
__version__ = "0.2.0"
