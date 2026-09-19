"""Prospectively fixed P3/P2 refinement; old eight-case qualification is retained."""
from .mixed_cube_representation_spec import configuration as representation_configuration


def configuration():
    result = representation_configuration()
    baseline = next(case for case in result['cases'] if case['name'] == 'mms_p3p2_n8')
    result.update(
        schema='prl.mixed_cube_refinement.v1',
        authorization='requires_refinement_milestone_authorization',
        cases=[{**baseline, 'name': 'mms_p3p2_n12', 'n': 12, 'role': 'refinement'}],
        maximum_equilibrium_solves=1,
        refinement={
            'grid_levels': [4, 8, 12],
            'primary_pair': [8, 12],
            'reference_cases': [{**baseline, 'name': f'mms_p3p2_n{n}', 'n': n} for n in (4, 8)],
            'reference_policy': 'Reuse separately protected and independently audited n4/n8; no new reference solves.',
            'initial_state': 'all-zero mixed vector for each new case; no warm start or continuation',
            'mesh_size': 'Uniform Freudenthal tetrahedron diameter sqrt(3)/n on the unit cube',
            'order_rule': 'log(E_coarse/E_fine)/log(n_fine/n_coarse)',
            'secondary_pairs': [[4, 8], [4, 12]],
            'secondary_pair_policy': 'Descriptive only; never replace the fixed primary pair.',
            'missing_policy': 'blocked if either reference, n12 terminal, or resource admission is missing',
            'original_n2_n4_n8_qualification': 'failed_unchanged',
            'historical_n4_n8_L2_order': 'failed_unchanged',
            'n16_resource_decision': 'excluded before new solves: estimated 9.77 GiB exceeds the unchanged 8 GiB limit',
            'production_quadrature_boundary': 'Keep Q8; order6/8 error readback does not establish production-load integration independence.',
        },
        scope='Fixed n4/8/12 P3/P2 kappa100 qualification; not original benchmark or ventricular qualification',
    )
    return result
