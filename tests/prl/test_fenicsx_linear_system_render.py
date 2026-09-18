import numpy as np
from scipy import sparse

from prl.rendering.fenicsx_linear_system import matrix_diagnostics


def test_matrix_diagnostics_keeps_block_and_cell_spectrum_evidence_in_memory():
    matrix = sparse.csr_matrix(
        np.array(
            [
                [2.0, 0.0, 1.0, 0.0, 1.0, 0.0],
                [0.0, 3.0, 0.0, 1.0, 0.0, 1.0],
                [1.0, 0.0, -1e-3, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, -2e-3, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0, -3e-3, 0.0],
                [0.0, 1.0, 0.0, 0.0, 0.0, -4e-3],
            ]
        )
    )
    report = matrix_diagnostics(
        matrix,
        displacement=np.array([0, 1]),
        pressure=np.array([2, 3, 4, 5]),
        pressure_cells=np.array([[2, 3], [4, 5]]),
        sparsity_bins=8,
    )

    assert report["size"] == 6
    assert report["displacement_dofs"] == 2
    assert report["pressure_dofs"] == 4
    assert report["pressure_cells"] == 2
    assert report["pressure_modes_per_cell"] == 2
    assert report["occupancy"].sum() == np.count_nonzero(matrix.data)
    np.testing.assert_allclose(
        report["pressure_cell_singular_values"],
        np.array([[2e-3, 1e-3], [4e-3, 3e-3]]),
    )
    assert report["zero_rows"] == 0
    assert report["zero_diagonal_entries"] == 0


def test_matrix_diagnostics_rejects_nonpartitioned_mixed_maps():
    matrix = sparse.eye(4, format="csr")
    try:
        matrix_diagnostics(
            matrix,
            displacement=np.array([0, 1]),
            pressure=np.array([1, 2]),
            pressure_cells=np.array([[1, 2]]),
        )
    except ValueError as error:
        assert "partition" in str(error)
    else:
        raise AssertionError("Overlapping mixed maps must not be plotted")
