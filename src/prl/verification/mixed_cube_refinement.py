"""Independent fixed-window refinement gates; no production imports or solves."""
import math
from numbers import Real


LABELS = ('u_L2', 'u_H1', 'pressure_L2')


def _finite_number(value, *, positive=False):
    return (isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
            and (value > 0 if positive else value >= 0))


def observed_order(coarse, fine, coarse_n, fine_n):
    """For this self-similar mesh family h_max=sqrt(3)/n, not DOF**(-1/3)."""
    if (not _finite_number(coarse, positive=True) or not _finite_number(fine, positive=True)
            or not _finite_number(coarse_n, positive=True)
            or not _finite_number(fine_n, positive=True) or fine_n <= coarse_n):
        raise ValueError('Finite positive errors and increasing grid resolution required')
    return math.log(coarse/fine)/math.log(fine_n/coarse_n)


def convergence(cases, config, references=None):
    """Use n4/n8 audits supplied by case name by the hash-protecting caller.

    This function checks numerical qualification only. The caller must verify
    the reference path, source hashes and saved-state/path readback independently.
    """
    specification = config['refinement']
    if (config['schema'] != 'prl.mixed_cube_refinement.v1'
            or specification['grid_levels'] != [4, 8, 12]
            or specification['primary_pair'] != [8, 12]
            or [case['name'] for case in specification['reference_cases']]
            != ['mms_p3p2_n4', 'mms_p3p2_n8']):
        raise ValueError('Refinement window or primary pair differs from the frozen design')
    expected_new = {'mms_p3p2_n12'}
    if set(cases)-expected_new:
        raise ValueError('Unregistered result; n4/n8 must be provided separately as protected references')
    references = {} if references is None else references
    if set(references)-{'mms_p3p2_n4', 'mms_p3p2_n8'}:
        raise ValueError('Unregistered reference case')
    reports = {n: references.get(f'mms_p3p2_n{n}') for n in (4, 8)}
    reports[12] = cases.get('mms_p3p2_n12')
    result = {
        'status': 'blocked', 'scope': 'P3/P2 kappa100 fixed n4/8/12 refinement window only',
        'grid_levels': [4, 8, 12], 'primary_pair': [8, 12],
        'mesh_sizes': {str(n): math.sqrt(3)/n for n in reports},
        'primary_mesh_ratio': 12/8, 'references_supplied_separately': sorted(references),
        'original_n2_n4_n8_qualification': 'failed_unchanged',
        'historical_n4_n8_L2_order': 'failed_unchanged',
        'original_ventricular_qualification': 'failed_unchanged',
        'pressure_representation_causal_attribution': 'unknown_unchanged',
        'threshold_changes': 0, 'primary_pair_substitutions': 0,
        'checks': {}, 'primary_EOC': {}, 'secondary_EOC': {},
    }
    missing = [f'mms_p3p2_n{n}' for n, report in reports.items() if report is None]
    unsafe = [f'mms_p3p2_n{n}' for n, report in reports.items() if report is not None
              and (report.get('status') == 'failed' or report.get('safety_status') == 'failed')]
    unavailable = [f'mms_p3p2_n{n}' for n, report in reports.items() if report is not None
                   and (report.get('status') != 'passed'
                        or report.get('safety_status', 'passed') != 'passed')]
    if missing or unavailable:
        result.update(status='failed' if unsafe else 'blocked', missing_cases=missing,
                      nonqualified_cases=unavailable,
                      reason='The complete fixed sequence requires three equation- and safety-qualified terminal states.')
        return result
    metrics = {n: report.get('metrics', {}) for n, report in reports.items()}
    invalid = {}
    for n, values in metrics.items():
        invalid_keys = [f'relative_{label}' for label in LABELS
                        if not _finite_number(values.get(f'relative_{label}'), positive=True)]
        if not _finite_number(values.get('J_error_RMS')):
            invalid_keys.append('J_error_RMS')
        if invalid_keys:
            invalid[f'mms_p3p2_n{n}'] = invalid_keys
    if invalid:
        result.update(status='failed', invalid_metrics=invalid,
                      reason='Nonfinite, negative, zero, absent or invalid error metric; no empirical order assigned.')
        return result
    checks, primary, secondary = {}, {}, {'4_to_8': {}, '4_to_12': {}}
    for label in LABELS:
        key = 'relative_'+label
        values = [metrics[n][key] for n in (4, 8, 12)]
        checks[label+'_decreases'] = values[0] > values[1] > values[2]
        primary[label] = observed_order(values[1], values[2], 8, 12)
        checks[label+'_order'] = primary[label] >= config['candidate_orders'][label]
        checks[label+'_fine'] = values[-1] <= config['mms_gates']['fine_relative_'+label]
        secondary['4_to_8'][label] = observed_order(values[0], values[1], 4, 8)
        secondary['4_to_12'][label] = observed_order(values[0], values[2], 4, 12)
    checks['fine_J_error'] = metrics[12]['J_error_RMS'] <= config['mms_gates']['fine_J_error_RMS']
    result.update(status='passed' if all(checks.values()) else 'failed', checks=checks,
                  primary_EOC=primary, secondary_EOC=secondary,
                  fine_metrics=metrics[12],
                  thresholds={'orders': dict(config['candidate_orders']),
                              'fine_absolute': {key: value for key, value in config['mms_gates'].items()
                                                if key.startswith('fine_')}},
                  interpretation='Secondary intervals are descriptive; no alternate pair or refitted threshold can change this verdict.')
    return result
