"""Readback of the approved space comparison; no production-form imports."""
import math


def _sequence(cases, names, limits, orders):
    present = [name for name in names if name in cases]
    if not present:
        return {'status': 'not_run'}
    if len(present) != len(names):
        return {'status': 'blocked', 'reason': 'incomplete grid sequence'}
    if any(cases[name]['status'] != 'passed' for name in names):
        return {'status': 'failed', 'reason': 'equation or safety qualification failed'}
    metrics = [cases[name]['metrics'] for name in names]
    checks, measured = {}, {}
    for label in ('u_L2', 'u_H1', 'pressure_L2'):
        values = [item['relative_' + label] for item in metrics]
        finite = all(value is not None and math.isfinite(value) and value > 0 for value in values)
        measured[label] = [math.log(values[i]/values[i+1], 2) for i in (0, 1)] if finite else [None, None]
        checks[label + '_decreases'] = finite and all(values[i+1] < values[i] for i in (0, 1))
        checks[label + '_order'] = finite and measured[label][-1] >= orders[label]
        checks[label + '_fine'] = finite and values[-1] <= limits['fine_relative_' + label]
    checks['fine_J_error'] = metrics[-1]['J_error_RMS'] <= limits['fine_J_error_RMS']
    return {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks, 'EOC': measured}


def convergence(cases, config):
    candidate = _sequence(cases, [f'mms_p3p2_n{n}' for n in (2, 4, 8)],
                          config['mms_gates'], config['candidate_orders'])
    control = _sequence(cases, [f'mms_p3p1_n{n}' for n in (2, 4, 8)], config['mms_gates'],
                        {key: config['mms_gates']['EOC_' + key] for key in ('u_L2', 'u_H1', 'pressure_L2')})
    patch = cases.get('patch_cubic_volume_p3p2', {}).get('status', 'not_run')
    integral = cases.get('mms_p2p1_q8_n8', {}).get('status', 'not_run')
    paired = []
    for n in (2, 4, 8):
        first, second = (cases.get(f'mms_p3p{degree}_n{n}') for degree in (1, 2))
        if not first or not second or first['status'] != 'passed' or second['status'] != 'passed':
            continue
        paired.append({'n': n, **{label: {'p3p1': first['metrics'][label],
                                        'p3p2': second['metrics'][label],
                                        'decreased': second['metrics'][label] < first['metrics'][label]}
                                  for label in ('relative_u_H1', 'relative_pressure_L2')}})
    supports = len(paired) == 3 and all(row[key]['decreased'] for row in paired
                                     for key in ('relative_u_H1', 'relative_pressure_L2'))
    statuses = {candidate['status'], patch, integral}
    status = ('passed' if statuses == {'passed'} else 'failed' if 'failed' in statuses
              else 'not_run' if statuses == {'not_run'} else 'blocked')
    return {'status': status, 'groups': {'candidate_p3p2': candidate,
            'diagnostic_p3p1_old_gates': control, 'cubic_patch': {'status': patch},
            'quadrature_control_equation_checks': {'status': integral}},
            'paired_comparison': paired, 'pressure_contribution': 'passed' if supports else 'unknown',
            'scope': 'candidate kappa100 qualification only; paired evidence is not unique-root proof',
            'original_eight_case_qualification': 'failed_unchanged',
            'does_not_qualify_original_ventricle': True, 'inf_sup_or_locking_proof': False}
