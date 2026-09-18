"""Analytic interface and first-failure tests; never invokes a mesher or FEM."""
import json
from unittest.mock import Mock
import numpy as np
import pytest
from prl.fem.ventricle_geometry import configuration, half_ellipsoid
from prl.fem.unstructured_geometry import boundary_complex, exact_surface_indices, OPTIONS
from prl.fem.ventricle_unstructured import execute
from prl.runs.ventricle_unstructured import candidate_configuration
from prl.verification.mesh_equivalence import compare, topology


@pytest.fixture
def reference():
    return half_ellipsoid({'segments': 8, 'bands': 3, 'radial': [1, 1, 2]}, configuration())


def test_reference_volume_and_boundary_producer(reference):
    summary, faces, _ = topology(reference)
    assert all(summary['checks'].values())
    produced = boundary_complex(reference)
    assert len(produced['facets']) == len(faces)
    xyz = reference['xyz']
    # Every oriented shell independently encloses the same layer volume.
    for layer, tags in produced['shells'].items():
        oriented = np.array([xyz[produced['facets'][abs(t)-1]][::1 if t > 0 else -1] for t in tags])
        volume = np.einsum('fi,fi->', oriented[:, 0], np.cross(oriented[:, 1], oriented[:, 2]))/6
        assert volume == pytest.approx(summary['layer_volumes'][str(layer)], abs=1e-14)


def test_renumbering_preserves_exact_surfaces_and_dofs(reference):
    permutation = np.arange(len(reference['xyz']))[::-1]
    candidate = {k: v.copy() for k, v in reference.items()}
    candidate['xyz'] = reference['xyz'][permutation]
    for key in ['tetrahedra', 'inner_faces', 'outer_faces']:
        candidate[key] = permutation[reference[key]]
    report, _ = compare(reference, candidate)
    assert report['checks']['identical_surface_coordinates_and_adjacency']
    assert report['checks']['same_volumes']
    assert report['reference']['mixed_dofs'] == report['candidate']['mixed_dofs']
    assert report['failed_checks'] == ['global_q05_improves_5percent']


def test_changed_surface_coordinates_are_rejected(reference):
    changed = {k: v.copy() for k, v in reference.items()}
    changed['xyz'][0, 0] += 1e-13  # No tolerance can conceal a moved interface.
    report, _ = compare(reference, changed)
    assert not report['checks']['identical_surface_coordinates_and_adjacency']


def test_corrupt_adjacency_and_unused_vertices_are_rejected(reference):
    changed = {k: v.copy() for k, v in reference.items()}
    changed['layers'][0] = 3
    report, _ = compare(reference, changed)
    assert not report['checks']['identical_surface_coordinates_and_adjacency']
    changed = {**reference, 'xyz': np.vstack([reference['xyz'], [3., 3., 3.]])}
    assert not topology(changed)[0]['checks']['no_unused_vertices']


def test_quality_failure_never_calls_solver_or_retries(reference, tmp_path):
    (tmp_path/'input').mkdir()
    np.savez_compressed(tmp_path/'input/M1_geometry.npz', **reference)
    (tmp_path/'configuration.json').write_text(json.dumps(candidate_configuration()))
    generator = Mock(return_value=reference); solver = Mock()
    result = execute(tmp_path, generator=generator, solver=solver)
    assert result['status'] == 'failed' and result['FEM'] == 'not_run'
    assert result['attempted_states'] == 0 and result['automatic_retries'] == 0
    generator.assert_called_once(); solver.assert_not_called()
    assert not (tmp_path/'raw').exists()


def test_configuration_changes_only_mesh_and_two_state_scope():
    original, candidate = configuration(), candidate_configuration()
    assert candidate['states'] == original['states'][:2]
    for key in set(original)-{'meshes', 'states', 'maximum_equilibrium_solves'}:
        assert candidate[key] == original[key]
    assert candidate['maximum_equilibrium_solves'] == 2
    assert OPTIONS['Mesh.Optimize'] == OPTIONS['Mesh.OptimizeNetgen'] == OPTIONS['Mesh.MaxRetries'] == 0
    assert OPTIONS['Mesh.Algorithm3D'] == OPTIONS['Mesh.MeshOnlyEmpty'] == 1


def test_surface_adapter_accepts_renumbering_but_never_snaps(reference):
    nodes = np.arange(len(reference['xyz']))[::-1]
    coordinates = reference['xyz'][nodes].copy()
    mapped = exact_surface_indices(reference['xyz'], reference['outer_faces'], coordinates)
    np.testing.assert_array_equal(coordinates[mapped], reference['xyz'][reference['outer_faces']])
    coordinates[nodes[reference['outer_faces'][0, 0]], 0] += 1e-13
    with pytest.raises(ValueError, match='changed or disappeared'):
        exact_surface_indices(reference['xyz'], reference['outer_faces'], coordinates)


def test_surface_adapter_rejects_duplicate_coordinates(reference):
    with pytest.raises(ValueError, match='Duplicate'):
        exact_surface_indices(reference['xyz'], reference['outer_faces'],
                              np.vstack([reference['xyz'], reference['xyz'][0]]))


def test_saved_mesh_reader_roundtrip_is_independent(reference, tmp_path):
    import meshio
    from prl.verification.saved_gmsh import load_saved
    path = tmp_path/'analytic_fixture.msh'
    meshio.write(path, meshio.Mesh(reference['xyz'], [('tetra', reference['tetrahedra'])],
        cell_data={'gmsh:physical': [reference['layers']], 'gmsh:geometrical': [reference['layers']]}), file_format='gmsh22')
    actual = load_saved(path, reference)
    report, _ = compare(reference, actual)
    assert report['checks']['identical_surface_coordinates_and_adjacency']
    assert report['checks']['same_volumes']
    assert report['failed_checks'] == ['global_q05_improves_5percent']


def test_generation_exception_stops_without_retry(reference, tmp_path):
    (tmp_path/'input').mkdir()
    np.savez_compressed(tmp_path/'input/M1_geometry.npz', **reference)
    (tmp_path/'configuration.json').write_text(json.dumps(candidate_configuration()))
    generator = Mock(side_effect=KeyError(726)); solver = Mock()
    result = execute(tmp_path, generator=generator, solver=solver)
    assert result['phase'] == 'meshing' and result['FEM'] == 'not_run'
    assert result['attempted_states'] == 0
    generator.assert_called_once(); solver.assert_not_called()


def test_consumed_result_refuses_before_container():
    from pathlib import Path
    from unittest.mock import patch
    from prl.runs.ventricle_unstructured import run
    with patch('prl.runs.ventricle_unstructured.result_path', side_effect=FileExistsError('consumed')):
        with patch('prl.runs.ventricle_unstructured.read_docker') as docker:
            with pytest.raises(FileExistsError):
                run(Path.cwd())
            docker.assert_not_called()
