"""Mechanical energy, dissipation, external-power, and residual ledger."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


@dataclass
class MechanicalLedger:
    stored: dict[str, float] = field(default_factory=dict)
    dissipation: dict[str, float] = field(default_factory=dict)
    external_power: dict[str, float] = field(default_factory=dict)

    def add_stored(self, owner: str, value: float) -> None:
        self.stored[owner] = self.stored.get(owner, 0.0) + float(value)

    def add_dissipation(self, owner: str, value: float) -> None:
        if value < -1e-10:
            raise ValueError(f"negative dissipation for {owner}: {value}")
        self.dissipation[owner] = self.dissipation.get(owner, 0.0) + float(value)

    def add_external_power(self, owner: str, value: float) -> None:
        allowed = {"pressure", "WSS"}
        if owner not in allowed:
            raise ValueError(f"Stage 1 external power owner is not allowed: {owner}")
        self.external_power[owner] = self.external_power.get(owner, 0.0) + float(value)

    @property
    def total_stored(self) -> float:
        return sum(self.stored.values())

    @property
    def total_dissipation(self) -> float:
        return sum(self.dissipation.values())

    @property
    def total_external_power(self) -> float:
        return sum(self.external_power.values())


def trapezoidal_integral(time: FloatArray, values: FloatArray) -> float:
    if len(time) != len(values) or len(time) < 2:
        raise ValueError("trapezoidal data must have equal length >= 2")
    return float(np.trapezoid(values, time))


def integrated_power_residual(
    time: FloatArray,
    stored_energy: FloatArray,
    total_dissipation: FloatArray,
    external_power: FloatArray,
) -> float:
    delta = float(stored_energy[-1] - stored_energy[0])
    dissipated = trapezoidal_integral(time, total_dissipation)
    work = trapezoidal_integral(time, external_power)
    numerator = abs(delta + dissipated - work)
    denominator = max(
        1.0,
        abs(delta) + dissipated + trapezoidal_integral(time, np.abs(external_power)),
    )
    return numerator / denominator


def static_force_residual(force_blocks: list[FloatArray]) -> float:
    if not force_blocks:
        return 0.0
    residual = sum((block for block in force_blocks), np.zeros_like(force_blocks[0]))
    denominator = max(1.0, sum(float(np.linalg.norm(block)) for block in force_blocks))
    return float(np.linalg.norm(residual) / denominator)

