"""Analytic shape checks; fixtures are mathematical, not biological evidence."""
from itertools import permutations
import numpy as np
import pytest
from prl.verification.tetra_quality import tetra_quality, regional_summary, descriptive_spearman


def regular():
    return np.array([[0., 0., 0.], [1., 0., 0.], [.5, np.sqrt(3)/2, 0.], [.5, np.sqrt(3)/6, np.sqrt(2/3)]])


def test_equilateral_analytic_quality():
    measured = tetra_quality(regular()[None])
    for name in ['q_radius', 'q_mean', 'edge_ratio', 'condition_regular']:
        assert measured[name][0] == pytest.approx(1.)
    assert measured['min_dihedral_deg'][0] == pytest.approx(np.degrees(np.arccos(1/3)))
    assert measured['max_dihedral_deg'][0] == pytest.approx(np.degrees(np.arccos(1/3)))
    assert measured['volume'][0] == pytest.approx(np.sqrt(2)/12)
    assert measured['max_edge_over_min_height'][0] == pytest.approx(np.sqrt(1.5))


def test_shape_is_permutation_and_similarity_invariant():
    original = regular()*np.array([.15, 2., .7])
    angle = .7
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    reference = tetra_quality(original[None])
    for permutation in permutations(range(4)):
        result = tetra_quality((3.7*original[list(permutation)] @ rotation + [2., -3., 1.])[None])
        for key in set(reference)-{'volume', 'centroid'}:
            np.testing.assert_allclose(result[key], reference[key], rtol=1e-11, atol=1e-11)


def test_flat_tetra_is_bad_and_degenerate_is_rejected():
    flat = regular()*[1., 1., .001]
    result = tetra_quality(flat[None])
    assert result['q_radius'][0] < .001 and result['min_dihedral_deg'][0] < 1
    assert result['condition_regular'][0] > 999
    flat[:, 2] = 0.
    with pytest.raises(ValueError, match='Degenerate'):
        tetra_quality(flat[None])


def test_shape_screen_does_not_replace_mechanical_gate():
    measured = tetra_quality(np.stack([regular()]*6))
    measured.update(layers=np.array([1, 1, 2, 2, 3, 3]), clamp_adjacent=np.array([1, 0]*3, dtype=bool),
                    max_abs_J_minus_one=np.array([.015, .004, .013, .003, .002, .001]))
    summary = regional_summary(measured)
    assert summary['all']['shape_screen_flagged_cells'] == 0
    assert summary['all']['volume_gate_failed_cells'] == 2
    assert summary['away_from_clamp']['volume_gate_failed_cells'] == 0
    assert summary['all']['q_radius_vs_J_spearman_descriptive'] is None
    assert descriptive_spearman(np.arange(5), -np.arange(5)) == pytest.approx(-1.)
