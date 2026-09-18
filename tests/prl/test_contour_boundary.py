"""Explicit geometric fixtures only; no scientific FEM solve."""
import numpy as np
import pytest
from prl.verification.contour_boundary import curve,ordered_outer


def test_straight_quadratic_square_has_exact_sampled_area():
    nodes=np.array([[0,0],[.5,0],[1,0],[1,.5],[1,1],[.5,1],[0,1],[0,.5]],dtype=float)
    edges=np.array([[0,1,2],[2,3,4],[4,5,6],[6,7,0]])
    from shapely.geometry import Polygon
    for count in [24,48]:
        boundary=curve(nodes,edges,count)
        assert boundary.is_simple and Polygon(boundary).area==pytest.approx(1.)


def test_single_triangle_outer_order_and_missing_cycle_refusal():
    mesh={'cells':np.array([[0,1,2,3,4,5]]),'inner_edges':np.empty((0,3),dtype=int)}
    assert len(ordered_outer(mesh))==3
    mesh['inner_edges']=np.array([[0,5,1]])
    with pytest.raises(ValueError,match='cycle'):
        ordered_outer(mesh)
