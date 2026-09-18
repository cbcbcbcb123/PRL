"""Independent sparse-matrix diagnostics; no DOLFINx or nonlinear solve."""
from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import structural_rank
from scipy.sparse.linalg import norm as sparse_norm


def _norm(matrix):
    return float(sparse_norm(matrix)) if matrix.nnz else 0.0


def finite_json(value):
    """Preserve nonfinite solver diagnostics as explicit JSON strings."""
    if isinstance(value,(float,np.floating)) and not np.isfinite(value):
        if np.isnan(value):
            return 'nan'
        return 'positive_infinity' if value>0 else 'negative_infinity'
    if isinstance(value,dict):
        return {key:finite_json(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):
        return [finite_json(item) for item in value]
    return value


def sparse_metrics(matrix, rhs, displacement, pressure, displacement_cells, pressure_cells, fixed):
    """Measure one assembled mixed tangent without changing a mechanical state."""
    matrix=sparse.csr_matrix(matrix)
    rhs=np.asarray(rhs,dtype=float)
    displacement=np.asarray(displacement,dtype=int)
    pressure=np.asarray(pressure,dtype=int)
    displacement_cells=np.asarray(displacement_cells,dtype=int)
    pressure_cells=np.asarray(pressure_cells,dtype=int)
    fixed=np.asarray(fixed,dtype=int)
    n,m=matrix.shape
    if n!=m or rhs.shape!=(n,):
        raise ValueError('Expected a square tangent and one matching residual')
    partition=np.concatenate((displacement,pressure))
    if len(np.unique(partition))!=n or not np.array_equal(np.sort(partition),np.arange(n)):
        raise ValueError('Displacement and pressure maps do not partition the mixed system')
    if not np.all(np.isin(fixed,displacement)):
        raise ValueError('Gauge constraints must be displacement degrees of freedom')
    row_norm=np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=1)).ravel())
    column_norm=np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=0)).ravel())
    diagonal=matrix.diagonal()
    symmetry=_norm(matrix-matrix.T)/max(_norm(matrix),1e-300)
    uu=matrix[displacement][:,displacement]
    up=matrix[displacement][:,pressure]
    pu=matrix[pressure][:,displacement]
    pp=matrix[pressure][:,pressure]
    pressure_singular=[]; pressure_eigen_min=[]; pressure_eigen_max=[]; coupling_rank=[]
    local_pp_nnz=0
    for ucell,pcell in zip(displacement_cells,pressure_cells,strict=True):
        local=matrix[pcell][:,pcell].toarray()
        local_pp_nnz+=int(np.count_nonzero(local))
        singular=np.linalg.svd(local,compute_uv=False)
        eigen=np.linalg.eigvalsh((local+local.T)/2)
        pressure_singular.append(singular)
        pressure_eigen_min.append(float(eigen.min()))
        pressure_eigen_max.append(float(eigen.max()))
        coupling=matrix[pcell][:,ucell].toarray()
        values=np.linalg.svd(coupling,compute_uv=False)
        tolerance=(values[0] if len(values) else 0)*1e-10
        coupling_rank.append(int(np.sum(values>tolerance)))
    pressure_singular=np.asarray(pressure_singular)
    free=np.setdiff1d(np.arange(n),fixed,assume_unique=False)
    return {
        'shape':[int(n),int(m)],'nonzeros':int(matrix.nnz),
        'finite_entries':bool(np.all(np.isfinite(matrix.data)) and np.all(np.isfinite(rhs))),
        'structural_rank':int(structural_rank(matrix)),
        'zero_rows':int(np.count_nonzero(row_norm==0)),
        'zero_columns':int(np.count_nonzero(column_norm==0)),
        'minimum_nonzero_row_norm':float(row_norm[row_norm>0].min()) if np.any(row_norm>0) else 0.,
        'maximum_row_norm':float(row_norm.max(initial=0)),
        'minimum_abs_nonzero_diagonal':float(np.abs(diagonal[np.abs(diagonal)>0]).min()) if np.any(diagonal) else 0.,
        'maximum_abs_diagonal':float(np.abs(diagonal).max(initial=0)),
        'relative_symmetry_error':symmetry,
        'rhs_norm':float(np.linalg.norm(rhs)),'free_rhs_norm':float(np.linalg.norm(rhs[free])),
        'dofs':{'displacement':int(len(displacement)),'pressure':int(len(pressure)),'fixed':int(len(fixed))},
        'block_frobenius_norms':{'uu':_norm(uu),'up':_norm(up),'pu':_norm(pu),'pp':_norm(pp)},
        'pressure_block':{
            'off_cell_nonzeros':int(pp.nnz-local_pp_nnz),
            'minimum_cell_singular_value':float(pressure_singular[:,-1].min()),
            'maximum_cell_singular_value':float(pressure_singular[:,0].max()),
            'maximum_cell_condition':float(np.max(pressure_singular[:,0]/pressure_singular[:,-1])),
            'cell_eigenvalue_minimum':float(np.min(pressure_eigen_min)),
            'cell_eigenvalue_maximum':float(np.max(pressure_eigen_max)),
            'all_cells_full_rank':bool(np.all(pressure_singular[:,-1]>1e-15)),
        },
        'pressure_displacement_local_rank_histogram':{
            str(rank):int(coupling_rank.count(rank)) for rank in sorted(set(coupling_rank))
        },
    }


def classify(metrics, mumps, superlu):
    """Return an evidence-bounded cause class, never a mechanics qualification."""
    if not metrics['finite_entries']:
        return 'assembled_nonfinite_entries'
    if metrics['zero_rows'] or metrics['zero_columns'] or metrics['structural_rank']<metrics['shape'][0]:
        return 'structurally_singular_assembled_system'
    if not metrics['pressure_block']['all_cells_full_rank']:
        return 'singular_finite_bulk_pressure_block'
    mumps_ok=mumps.get('converged_reason',0)>0 and mumps.get('relative_residual',np.inf)<1e-8
    superlu_ok=superlu.get('status')=='passed' and superlu.get('relative_residual',np.inf)<1e-8
    if mumps_ok and superlu_ok:
        return 'matrix_solved_by_both_direct_paths_original_snes_failure_not_reproduced'
    if not mumps_ok and superlu_ok:
        return 'mumps_backend_failure_with_superlu_small_residual'
    if not mumps_ok and not superlu_ok:
        return 'numerically_singular_or_severely_ill_conditioned_mixed_system'
    return 'cross_solver_disagreement_requires_further_diagnosis'
