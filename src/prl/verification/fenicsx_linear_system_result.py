"""Independent audit of a retained mixed-matrix diagnostic package.

This module never factorizes the matrix and never invokes DOLFINx or Docker.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import sparse

from .fenicsx_linear_system import sparse_metrics


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _identities(root, records):
    return {
        item["path"]: (root / item["path"]).is_file()
        and _digest(root / item["path"]) == item["sha256"]
        for item in records
    }


def verify_linear_system_result(root, workspace=None, save=False):
    """Audit saved assembly evidence without another solve or factorization."""
    root = Path(root).resolve(strict=True)
    archive = np.load(root / "matrix_csr.npz")
    size = len(archive["rhs"])
    matrix = sparse.csr_matrix(
        (archive["data"], archive["indices"], archive["indptr"]),
        shape=(size, size),
    )
    metrics = sparse_metrics(
        matrix,
        archive["residual"],
        archive["displacement"],
        archive["pressure"],
        archive["displacement_cells"],
        archive["pressure_cells"],
        archive["fixed"],
    )
    formal = _load_json(root / "formal_invocation_manifest.json")
    formal_identity = _identities(root, formal["files"])
    execution = _load_json(root / "execution.json")
    started = _load_json(root / "diagnostic_started.json")
    configuration = _load_json(root / "configuration.json")
    failure = _load_json(root / "failure.json")
    zero_metadata = _load_json(root / "source_f6s1r/M0_state_passive_0.json")
    failed_metadata = _load_json(root / "source_f6s1r/M0_state_passive_1.json")
    zero_state = np.load(root / "source_f6s1r/M0_state_passive_0.npz")
    failed_state = np.load(root / "source_f6s1r/M0_state_passive_1.npz")

    source_identity = {}
    for absolute, expected in _load_json(root / "source_result_preflight.json").items():
        path = Path(absolute)
        source_identity[absolute] = path.is_file() and _digest(path) == expected
    parent_identity = {}
    if workspace is not None:
        workspace = Path(workspace).resolve(strict=True)
        for relative, expected in _load_json(root / "protected_preflight.json").items():
            path = workspace / relative
            parent_identity[relative] = path.is_file() and _digest(path) == expected

    pressure_per_cell = int(archive["pressure_cells"].shape[1])
    rank_histogram = metrics["pressure_displacement_local_rank_histogram"]
    weak_mode_lower_bound = sum(
        (pressure_per_cell - int(rank)) * count
        for rank, count in rank_histogram.items()
    )
    scale_ratio = (
        metrics["maximum_abs_diagonal"]
        / metrics["pressure_block"]["minimum_cell_singular_value"]
    )
    block_norm_ratio = (
        metrics["block_frobenius_norms"]["uu"]
        / metrics["block_frobenius_norms"]["pp"]
    )
    state_chain = bool(
        np.array_equal(failed_state["initial_mixed"], zero_state["mixed_state"])
        and np.array_equal(archive["initial"], failed_state["initial_mixed"])
    )
    serializer_failure = (
        failure.get("error", {}).get("type") == "ValueError"
        and "Out of range float values" in failure.get("error", {}).get("message", "")
    )
    checks = {
        "formal_invocation_files_unchanged": all(formal_identity.values()),
        "source_result_unchanged": all(source_identity.values()),
        "protected_parent_unchanged": bool(parent_identity) and all(parent_identity.values()),
        "single_container_failed_without_retry": execution.get("status") == "failed"
        and execution.get("diagnostic_container_invocations") == 1
        and execution.get("automatic_retries") == 0,
        "no_nonlinear_equilibrium_solve_declared": started.get("nonlinear_equilibrium_solves") == 0
        and execution.get("nonlinear_equilibrium_solves") == 0
        and configuration.get("nonlinear_equilibrium_solves") == 0,
        "zero_gpu": execution.get("gpu") == 0 and configuration["resources"].get("gpu") == 0,
        "retained_initial_state_chain": state_chain,
        "original_failure_is_first_nonzero_state": zero_metadata.get("iterations") == 0
        and failed_metadata.get("iterations") == 0
        and failed_metadata.get("snes_reason") == -3,
        "matrix_entries_finite": metrics["finite_entries"],
        "matrix_structurally_full_rank": metrics["structural_rank"] == size,
        "matrix_has_no_zero_rows_or_columns": metrics["zero_rows"] == 0
        and metrics["zero_columns"] == 0,
        "pressure_cell_blocks_full_rank": metrics["pressure_block"]["all_cells_full_rank"],
        "strict_json_failure_retained": serializer_failure and not (root / "diagnosis.json").exists(),
    }
    verification_status = "passed" if all(checks.values()) else "failed"
    report = {
        "verification_status": verification_status,
        "execution_status": "failed",
        "diagnostic_delivery_status": "failed",
        "scientific_root_cause_status": "not_evaluable",
        "checks": checks,
        "matrix": metrics,
        "derived": {
            "pressure_dofs_per_cell": pressure_per_cell,
            "weakly_coupled_pressure_mode_lower_bound": int(weak_mode_lower_bound),
            "maximum_diagonal_to_minimum_pressure_cell_singular_ratio": float(scale_ratio),
            "uu_to_pp_frobenius_norm_ratio": float(block_norm_ratio),
        },
        "failure_localization": {
            "class": "nonfinite_mumps_diagnostic_value_not_serialized",
            "basis": "all independently recomputed matrix metrics are finite and the executed SuperLU path guards a nonfinite condition estimate; an unguarded MUMPS scalar remained",
            "exact_field": "unknown",
            "ksp_reason": "not_retained",
            "pc_failed_reason": "not_retained",
            "mumps_infog": "not_retained",
            "superlu_outcome": "not_retained",
        },
        "bounded_interpretation": {
            "excluded": [
                "structural rank deficiency",
                "zero assembled row or column",
                "singular per-cell finite-bulk pressure mass block",
            ],
            "supported_hypothesis": "severe mixed-block scaling or numerical pivot difficulty",
            "confirmed_solver_root_cause": False,
            "reason": "the exact MUMPS and SuperLU reports were lost at strict JSON serialization and the approved run was not repeated",
        },
        "state_after_factorization": "not_evaluable_no_post_state_was_persisted",
        "new_equilibria": 0,
        "new_factorizations_in_post_verification": 0,
        "contour": "not_run",
        "three_dimensional_model": "not_run",
        "fsi": "not_run",
        "growth": "not_run",
    }
    if save:
        target = root / "post_verification.json"
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return report


def mumps_failure_cause(report):
    """Interpret a saved MUMPS error code without inferring it from block scales."""
    code=report.get('mumps',{}).get('infog',{}).get('1')
    return {-9:'mumps_internal_real_workspace_too_small',
            -8:'mumps_internal_integer_workspace_too_small',
            -10:'mumps_numerical_singularity_or_zero_pivot',
            -6:'mumps_structural_singularity',
            -13:'mumps_memory_allocation_failure',
            0:'mumps_no_reported_error'}.get(code,'unknown_mumps_failure')


def saved_solution_metrics(matrix,rhs,solution,reference):
    """Independent saved-vector checks, with no linear solve or factorization."""
    finite=bool(np.isfinite(solution).all())
    return {'finite':finite,
            'relative_residual':float(np.linalg.norm(matrix@solution-rhs)/np.linalg.norm(rhs)) if finite else None,
            'relative_solution_difference':float(np.linalg.norm(solution-reference)/np.linalg.norm(reference)) if finite else None,
            'reference_relative_residual':float(np.linalg.norm(matrix@reference-rhs)/np.linalg.norm(rhs))}


def verify_workspace_result(root,workspace,save=False):
    """Audit the saved S3 matrix/solution; outcome is separate from preservation."""
    root=Path(root).resolve(strict=True); workspace=Path(workspace).resolve(strict=True)
    diagnosis=_load_json(root/'diagnosis.json'); execution=_load_json(root/'execution.json')
    config=_load_json(root/'configuration.json'); old_config=_load_json(root/'previous_configuration.json')
    mumps=_load_json(root/'mumps_diagnosis.json'); old=_load_json(root/'previous_mumps_diagnosis.json')
    formal=_identities(root,_load_json(root/'formal_invocation_manifest.json')['files'])
    sources=_load_json(root/'source_result_preflight.json'); parents=_load_json(root/'protected_preflight.json')
    with np.load(root/'matrix_csr.npz',allow_pickle=False) as data:
        arrays={key:data[key] for key in data.files}
    with np.load(root/'previous_matrix_csr.npz',allow_pickle=False) as data:
        identities={key:np.array_equal(arrays[key],data[key]) for key in data.files}
    with np.load(root/'matrix_after.npz',allow_pickle=False) as data:
        after={key:np.array_equal(arrays[key],data[key]) for key in data.files}
    with np.load(root/'state_identity.npz',allow_pickle=False) as data:
        state={key:data[key].tobytes()==arrays['initial'].tobytes() for key in data.files}
    with np.load(root/'mumps_linear_solution.npz',allow_pickle=False) as data:
        actual=data['solution']
    with np.load(root/'reference_superlu_solution.npz',allow_pickle=False) as data:
        reference=data['solution']
    size=len(arrays['rhs'])
    matrix=sparse.csr_matrix((arrays['data'],arrays['indices'],arrays['indptr']),shape=(size,size))
    metrics=saved_solution_metrics(matrix,arrays['rhs'],actual,reference)
    controls=mumps.get('mumps',{})
    control_identity={f'{group}_{key}':controls.get(group,{}).get(key)==value
                      for group in ('icntl','cntl') for key,value in old['mumps'][group].items()
                      if not (group=='icntl' and key=='14')}
    physics=['radii','meshes','mu','kappa','quadrature_degree','pressure_space','loads']
    declared={'matrix_assemblies':0,'mumps_factorizations':1,'superlu_factorizations':0,
              'nonlinear_equilibrium_solves':0,'newton_updates':0,'automatic_retries':0,'gpu':0}
    checks={
        'formal_files_preserved':bool(formal) and all(formal.values()),
        'sources_preserved':bool(sources) and all(_digest(path)==sha for path,sha in sources.items()),
        'parents_preserved':bool(parents) and all(_digest(workspace/path)==sha for path,sha in parents.items()),
        'matrix_rhs_and_maps_identical':len(identities)==11 and all(identities.values()),
        'native_matrix_after_identical':len(after)==3 and all(after.values()),
        'state_bytes_unchanged':len(state)==2 and all(state.values()),
        'physics_unchanged':all(config[key]==old_config[key] for key in physics),
        'only_one_solver_setting_changed':config['solver']=={**old_config['solver'],'mat_mumps_icntl_14':100},
        'old_margin_failure_is_retained':old['mumps']['infog']['1']==-9 and old['mumps']['icntl']['14']==20,
        'actual_controls_except_margin_unchanged':all(control_identity.values()),
        'backend_and_prefix_preserved':all(mumps[key]==old[key] for key in ['ksp_type','pc_type','factor_solver_type','ksp_options_prefix','matrix_type']),
        'single_bounded_container':execution['diagnostic_container_invocations']==1 and all(execution['container_checks'].values()),
        'no_oom':not _load_json(root/'container_inspect.json')['State']['OOMKilled'],
        'attempt_counts_and_no_updates':all(diagnosis[key]==value for key,value in declared.items()) and mumps['attempts']==1,
        'report_matches_saved_vector_finiteness':metrics['finite']==mumps['solution_finite'],
        'report_matches_diagnosis':mumps==diagnosis['mumps'],
        'reference_residual_acceptable':metrics['reference_relative_residual']<=1e-8,
    }
    if metrics['finite']:
        checks['reported_residual_matches']=bool(np.isclose(metrics['relative_residual'],mumps['relative_residual'],rtol=1e-3,atol=1e-14))
        checks['reported_solution_difference_matches']=bool(np.isclose(metrics['relative_solution_difference'],diagnosis['relative_solution_difference'],rtol=1e-10,atol=1e-14))
    linear={'infog_zero':controls.get('infog',{}).get('1')==0,
            'ksp_positive':mumps['converged_reason']>0,'pc_zero':mumps['pc_failed_reason']==0,
            'actual_margin_100':controls.get('icntl',{}).get('14')==100,
            'solution_finite':metrics['finite'],
            'relative_residual':metrics['finite'] and metrics['relative_residual']<=1e-8,
            'solution_agreement':metrics['finite'] and metrics['relative_solution_difference']<=1e-6}
    report={'verification_status':'passed' if all(checks.values()) else 'failed',
            'linear_solver_status':'passed' if all(linear.values()) and all(checks.values()) else 'failed',
            'checks':checks,'linear_checks':linear,'metrics':metrics,
            'mumps_infog_1':controls.get('infog',{}).get('1'),'mumps_infog_2':controls.get('infog',{}).get('2'),
            'mumps_icntl_14':controls.get('icntl',{}).get('14'),'ksp_reason':mumps['converged_reason'],
            'pc_failed_reason':mumps['pc_failed_reason'],'other_control_identity':control_identity,
            'formal_files_checked':len(formal),'source_files_checked':len(sources),'parent_files_checked':len(parents),
            'matrix_arrays_checked':len(identities),'native_csr_arrays_checked':len(after),'state_arrays_checked':len(state),
            'postprocess_factorizations':0,'new_equilibria':0,'scientific_pressure_space_status':'failed',
            'contour':'not_run','three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run'}
    if save:
        (root/'post_verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


def verify_replay_result(root, workspace, save=False):
    """Verify the S2 reports and saved solutions using matvecs, without any solve."""
    root=Path(root).resolve(strict=True); workspace=Path(workspace).resolve(strict=True)
    diagnostic=_load_json(root/'diagnosis.json'); execution=_load_json(root/'execution.json')
    mumps=_load_json(root/'mumps_diagnosis.json'); superlu=_load_json(root/'superlu_diagnosis.json')
    formal=_load_json(root/'formal_invocation_manifest.json')
    identity=_identities(root,formal['files'])
    sources=_load_json(root/'source_result_preflight.json')
    parents=_load_json(root/'protected_preflight.json')
    with np.load(root/'matrix_csr.npz',allow_pickle=False) as saved:
        arrays={key:saved[key] for key in saved.files}
    with np.load(root/'previous_matrix_csr.npz',allow_pickle=False) as previous:
        same_matrix={key:np.array_equal(previous[key],arrays[key]) for key in previous.files}
    size=len(arrays['rhs'])
    matrix=sparse.csr_matrix((arrays['data'],arrays['indices'],arrays['indptr']),shape=(size,size))
    with np.load(root/'state_identity.npz',allow_pickle=False) as states:
        same_state={key:states[key].tobytes()==arrays['initial'].tobytes() for key in states.files}
    with np.load(root/'superlu_linear_solution.npz',allow_pickle=False) as solution:
        superlu_vector=solution['solution']
    with np.load(root/'mumps_linear_solution.npz',allow_pickle=False) as solution:
        mumps_finite=bool(np.isfinite(solution['solution']).all())
    relative=float(np.linalg.norm(matrix@superlu_vector-arrays['rhs'])/np.linalg.norm(arrays['rhs']))
    fixed=arrays['fixed']; reference=np.zeros((len(fixed),size))
    reference[np.arange(len(fixed)),fixed]=1.
    gauge_error=float(np.max(np.abs(matrix[fixed].toarray()-reference)))
    inspection=_load_json(root/'container_inspect.json')
    snapshot_hashes=_load_json(root/'source_hashes.json')
    checks={
        'formal_files_preserved':all(identity.values()),
        'source_packages_preserved':all(_digest(path)==sha for path,sha in sources.items()),
        'parent_files_preserved':all(_digest(workspace/path)==sha for path,sha in parents.items()),
        'source_snapshots_preserved':all(_digest(root/'sources_at_execution'/path)==sha for path,sha in snapshot_hashes.items()),
        'identical_saved_matrix_rhs_and_maps':bool(all(same_matrix.values())),
        'state_bytes_unchanged':bool(all(same_state.values())),
        'fixed_dofs_have_unit_rows':gauge_error<1e-14,
        'negated_residual_is_rhs':bool(np.array_equal(-arrays['residual'],arrays['rhs'])),
        'superlu_solution_finite':bool(np.isfinite(superlu_vector).all()),
        'superlu_relative_residual':relative<1e-8,
        'superlu_saved_residual_matches':bool(np.isclose(relative,superlu['relative_residual'],rtol=1e-3,atol=1e-14)),
        'mumps_report_consistency':mumps==diagnostic['mumps'] and superlu==diagnostic['superlu'],
        'mumps_nonfinite_flag_matches':mumps_finite==mumps['solution_finite'],
        'diagnostic_execution_passed':execution['status']=='passed' and diagnostic['status']=='passed',
        'one_container':execution['diagnostic_container_invocations']==1,
        'one_factorization_each':mumps['attempts']==superlu['attempts']==1,
        'zero_equilibria_and_newton_updates':diagnostic['nonlinear_equilibrium_solves']==diagnostic['newton_updates']==0,
        'zero_automatic_retries_and_gpu':execution['automatic_retries']==execution['gpu']==0,
        'container_not_oom_killed':not inspection['State']['OOMKilled'],
    }
    report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'diagnostic_delivery':'passed' if all(checks.values()) else 'failed',
            'scientific_pressure_space_status':'failed','cause':mumps_failure_cause(mumps),
            'ksp_reason':mumps['converged_reason'],'pc_failed_reason':mumps['pc_failed_reason'],
            'mumps_infog_1':mumps['mumps']['infog']['1'],'mumps_infog_2':mumps['mumps']['infog']['2'],
            'mumps_icntl_14':mumps['mumps']['icntl']['14'],
            'superlu_independent_relative_residual':relative,
            'superlu_estimated_condition_1':superlu['estimated_condition_1'],
            'fixed_row_max_error':gauge_error,'matrix_arrays_checked':len(same_matrix),
            'state_arrays_checked':len(same_state),'formal_files_checked':len(identity),
            'source_result_files_checked':len(sources),'protected_parent_files_checked':len(parents),
            'postprocess_factorizations':0,'new_equilibria':0,'state_updated':False,
            'interpretation':'MUMPS workarray capacity was exhausted. Block scale separation may contribute to pivoting and fill-in, but this run does not establish that causal link. SuperLU gives a small residual for this right-hand side; nonlinear mechanics and local J remain untested.',
            'documentation':[
                'https://mumps-solver.org/doc/userguide_5.9.1.pdf',
                'https://petsc.org/release/manualpages/Mat/MATSOLVERMUMPS/']}
    if save:
        (root/'post_verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report
