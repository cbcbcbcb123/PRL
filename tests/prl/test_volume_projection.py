"""Mathematical checks of saved-state diagnostics, not biological validation."""
import numpy as np
import pytest
from prl.verification.volume_projection import weighted_summary, distance_bands, analyze
from prl.verification import ventricle_3d as mechanics


def affine_fixture(deformation=np.diag([1.001, .999, 1.])):
    vertices = np.array([[0., 0., 0.], [0., 1., 0.], [1., 0., 0.], [0., 0., -1.]])
    xyz = np.vstack([vertices, [(vertices[i]+vertices[j])/2 for i,j in mechanics.EDGES]])
    a, b = .5854101966249685, .1381966011250105
    mesh = {'coordinates': xyz, 'cells': np.arange(10)[None], 'layers': np.array([1]),
        'pressure_cells': np.arange(4)[None], 'pressure_coordinates': vertices,
        'qpoints': np.array([[b,b,b],[a,b,b],[b,a,b],[b,b,a]]), 'qweights': np.full(4, 1/24)}
    config = {'kappa': 1000., 'mu': 1.}
    state = {'u': xyz @ (deformation-np.eye(3)).T,
             'pressure': np.full(4, config['kappa']*(np.linalg.det(deformation)-1))}
    return mesh, state, config


def test_weighted_rms_uses_reference_volume_not_sample_count():
    measured = weighted_summary(np.array([1.,3.]), np.array([3.,1.]))
    assert measured['mean'] == 1.5
    assert measured['rms'] == pytest.approx(np.sqrt(3))
    assert measured['reference_volume'] == 4


def test_empty_region_is_unknown_not_zero_error():
    result = weighted_summary(np.array([2.]), np.array([1.]), np.array([False]))
    assert result['rms'] is None and result['max_abs'] is None and result['reference_volume'] == 0


@pytest.mark.parametrize('weights', [np.array([0.]), np.array([-1.]), np.array([np.nan])])
def test_invalid_quadrature_weight_is_rejected(weights):
    with pytest.raises(ValueError, match='Positive'):
        weighted_summary(np.ones(1), weights)


def test_physical_bands_include_boundaries_once_and_do_not_depend_on_cell_id():
    points = np.zeros((5,3)); points[:,2] = -np.array([0,.15,.30,.45,1.5])
    np.testing.assert_array_equal(distance_bands(points), [0,1,2,3,3])
    np.testing.assert_array_equal(distance_bands(points[::-1]), [3,3,2,1,0])


def test_compatible_nonzero_affine_material_has_no_projection_defect():
    mesh, state, config = affine_fixture()
    result, arrays = analyze(mesh,state,config,mechanics)
    assert result['max_abs_J_minus_one'] > 0
    assert result['rms_projection_defect'] < 1e-14
    assert result['max_abs_projection_defect'] < 1e-14
    assert result['solid_reference_volume'] == pytest.approx(1/6)
    assert result['pressure_weak_moment_norm'] < 1e-14
    assert sum(result['regions']['all/band_'+str(i)]['projection_defect']['reference_volume'] for i in range(4)) == pytest.approx(1/6)
    assert len(arrays['cell_peak_distance']) == 1


def test_bad_cell_volume_fraction_is_not_sample_exceedance_fraction():
    mesh, state, config = affine_fixture(np.diag([1.02,1.,1.]))
    state['pressure'][:] = 0
    result, _ = analyze(mesh,state,config,mechanics)
    assert result['bad_cells'] == 1
    assert result['fraction_solid_volume_in_bad_cells'] == 1
    assert result['scientific_pressure_gate'] == 'failed'
    assert result['rms_projection_defect'] == pytest.approx(.02)
    assert abs(result['exact_split_identity_error']) < 1e-14


def test_nonorthogonal_data_does_not_get_relabelled_as_projection_solution():
    mesh, state, config = affine_fixture(np.diag([1.02,1.,1.]))
    state['pressure'][:] = 10
    result, _ = analyze(mesh,state,config,mechanics)
    assert result['pressure_weak_moment_norm'] > 1e-4
    assert result['orthogonal_split_error'] > 1e-3
    assert abs(result['exact_split_identity_error']) < 1e-14


def test_nonpositive_J_rejected_before_reporting():
    mesh, state, config = affine_fixture(np.diag([-1.,1.,1.]))
    with pytest.raises(ValueError, match='Nonpositive'):
        analyze(mesh,state,config,mechanics)
