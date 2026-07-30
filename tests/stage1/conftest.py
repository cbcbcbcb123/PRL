from __future__ import annotations

import pytest

from route_h.geometry import load_reference_bundle


@pytest.fixture(scope="session")
def bundle():
    return load_reference_bundle()

