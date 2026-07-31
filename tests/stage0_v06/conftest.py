from __future__ import annotations

import pytest

from route_h.discretization import LEVELS, load_discretization_level


@pytest.fixture(scope="session")
def v06_levels():
    return {
        level.name: load_discretization_level(level.name)
        for level in LEVELS
    }
