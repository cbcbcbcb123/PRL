"""Frozen v08 migration protocol and production endpoint naming."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from .config import ACTIVE_CONFIG


@dataclass(frozen=True)
class HybridProtocol:
    schema: str = "paper2_hybrid_protocol_v08"
    parity_cases: tuple[str, ...] = ("A2", "LN", "LS", "C0", "CQ", "S1")
    spatial_level: str = "S4"
    time_level: str = "T64"
    steps_per_cycle: int = 64
    tolerance_level: str = "D0"
    common_projection_segments: int = 64
    parity_absolute_tolerance: float = 1.0e-12
    parity_normalized_l2_tolerance: float = 1.0e-10
    direct_relative_residual_tolerance: float = 1.0e-7
    direct_backward_error_tolerance: float = 1.0e-12
    discrete_ledger_closure_tolerance: float = 1.0e-10
    runtime_budget_seconds: float = 1200.0
    memory_budget_gib: float = 8.0
    cpu_processes: int = 1

    def checked(self) -> "HybridProtocol":
        if self.parity_cases != ("A2", "LN", "LS", "C0", "CQ", "S1"):
            raise ValueError("the six migration cases changed")
        if (self.spatial_level, self.time_level, self.tolerance_level) != (
            "S4",
            "T64",
            "D0",
        ):
            raise ValueError("the v08 migration endpoint changed")
        if self.steps_per_cycle != 64 or self.common_projection_segments != 64:
            raise ValueError("the v08 sampling or projection changed")
        if self.cpu_processes != 1:
            raise ValueError("v08 is single-process only")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self.checked())
        payload["active_cases"] = list(ACTIVE_CONFIG.cases)
        return payload

    def digest(self) -> str:
        serialized = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


def endpoint_key(
    case_id: str,
    spatial_level: str = "S4",
    time_level: str = "T64",
    tolerance_level: str = "D0",
) -> str:
    if case_id not in ACTIVE_CONFIG.cases:
        raise ValueError(f"case is not active: {case_id}")
    return "__".join((case_id, spatial_level, time_level, tolerance_level))


ACTIVE_PROTOCOL = HybridProtocol().checked()
