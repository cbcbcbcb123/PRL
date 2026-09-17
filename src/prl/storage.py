"""Read-only repository storage accounting and admission policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import stat


GIB = 1024**3
MIB = 1024**2


@dataclass(frozen=True)
class StoragePolicy:
    warning_bytes: int = int(2.4 * GIB)
    hard_limit_bytes: int = 3 * GIB
    default_stage_bytes: int = 800 * MIB
    minimum_stop_reserve_bytes: int = 64 * MIB


@dataclass(frozen=True)
class StorageSnapshot:
    workspace: str
    file_count: int
    directory_count: int
    logical_bytes: int
    skipped_reparse_points: tuple[str, ...] = ()
    scan_errors: tuple[str, ...] = ()


def _is_reparse(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & flag)


def scan_workspace(workspace: Path) -> StorageSnapshot:
    """Count ordinary files without following reparse points or links."""

    root = workspace.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Workspace is not a directory: {root}")

    file_count = 0
    directory_count = 0
    logical_bytes = 0
    skipped: list[str] = []
    errors: list[str] = []
    pending = [root]

    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    relative = path.relative_to(root).as_posix()
                    try:
                        if _is_reparse(path):
                            skipped.append(relative)
                        elif entry.is_dir(follow_symlinks=False):
                            directory_count += 1
                            pending.append(path)
                        elif entry.is_file(follow_symlinks=False):
                            file_count += 1
                            logical_bytes += entry.stat(follow_symlinks=False).st_size
                    except OSError as error:
                        errors.append(f"{relative}: {error.__class__.__name__}: {error}")
        except OSError as error:
            relative = current.relative_to(root).as_posix() or "."
            errors.append(f"{relative}: {error.__class__.__name__}: {error}")

    return StorageSnapshot(
        workspace=str(root),
        file_count=file_count,
        directory_count=directory_count,
        logical_bytes=logical_bytes,
        skipped_reparse_points=tuple(sorted(skipped, key=str.casefold)),
        scan_errors=tuple(sorted(errors, key=str.casefold)),
    )


def evaluate_storage(
    snapshot: StorageSnapshot,
    *,
    planned_new_bytes: int | None = None,
    stop_reserve_bytes: int | None = None,
    policy: StoragePolicy | None = None,
) -> dict:
    """Evaluate a snapshot against the frozen warning and hard limits."""

    active_policy = policy or StoragePolicy()
    planned = (
        active_policy.default_stage_bytes
        if planned_new_bytes is None
        else planned_new_bytes
    )
    reserve = (
        active_policy.minimum_stop_reserve_bytes
        if stop_reserve_bytes is None
        else stop_reserve_bytes
    )
    if planned < 0 or reserve < 0:
        raise ValueError("Planned output and stop reserve must be non-negative")

    current = snapshot.logical_bytes
    projected = current + planned + reserve
    remaining = max(0, active_policy.hard_limit_bytes - current)
    admissible_new = max(0, active_policy.hard_limit_bytes - current - reserve)

    if snapshot.scan_errors:
        status = "unknown"
        level = "scan_incomplete"
        can_start = False
    elif current >= active_policy.hard_limit_bytes:
        status = "blocked"
        level = "hard_limit_exceeded"
        can_start = False
    elif projected > active_policy.hard_limit_bytes:
        status = "blocked"
        level = "preflight_rejected"
        can_start = False
    elif current >= active_policy.warning_bytes:
        status = "passed"
        level = "warning"
        can_start = True
    else:
        status = "passed"
        level = "normal"
        can_start = True

    return {
        "schema_version": "prl.storage_status.v1",
        "status": status,
        "level": level,
        "can_start": can_start,
        "workspace": snapshot.workspace,
        "usage": {
            "file_count": snapshot.file_count,
            "directory_count": snapshot.directory_count,
            "logical_bytes": current,
            "remaining_to_hard_limit_bytes": remaining,
        },
        "request": {
            "planned_new_bytes": planned,
            "stop_reserve_bytes": reserve,
            "projected_logical_bytes": projected,
            "maximum_admissible_new_bytes": admissible_new,
        },
        "policy": asdict(active_policy),
        "skipped_reparse_points": list(snapshot.skipped_reparse_points),
        "scan_errors": list(snapshot.scan_errors),
        "scope": "logical file bytes inside the workspace; reparse points are not followed",
    }
