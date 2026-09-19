"""Supplement, not alteration, of saved-path ratio checks near cancellation."""
import json
from pathlib import Path
import numpy as np
from .ventricle_3d import load_arrays


def exact_endpoint_certificate(current, direction, accepted, scale):
    """Certify only bitwise equality with the stored permitted full endpoint.

    Recovering alpha from (x-y).d/(d.d) is ill-conditioned when d is tiny
    relative to x. This uses no tolerance and does not modify the guarded path,
    positive-J requirement, or original ratio check. Non-endpoints get no pass.
    """
    valid=(current.shape==direction.shape==accepted.shape and np.isfinite(scale)
        and 0 < scale <= 1 and all(np.isfinite(a).all() for a in [current,direction,accepted]))
    expected=current-scale*direction if valid else None
    equal=bool(valid and np.array_equal(accepted,expected))
    return {'status':'passed' if equal else 'failed','bitwise_endpoint_equal':equal,
        'maximum_endpoint_difference':float(np.max(np.abs(accepted-expected))) if valid else None,
        'method':'exact equality to float64 current - registered_scale * stored_direction; no tolerance'}


def resolve_roundtrip(root, original):
    """All original path checks remain mandatory except a proven exact endpoint."""
    root=Path(root)
    failed=[key for key,value in original['checks'].items() if not value]
    certificates={}
    candidates={f'{item["case"]}_{item["sequence"]}_accepted_in_segment':item
                for item in original['candidates']}
    for key in failed:
        entry=candidates.get(key)
        if entry is None:
            certificates[key]={'status':'failed','reason':'Not an endpoint membership check'}
            continue
        folder=root/'iterates'/entry['case']
        stored=load_arrays(folder/f'candidate_{entry["sequence"]:03d}.npz')
        accepted=load_arrays(folder/f'iterate_{entry["newton_iteration"]+1:03d}.npz')['mixed_state']
        report=exact_endpoint_certificate(stored['current_mixed'],stored['direction_mixed'],accepted,entry['scale'])
        report.update(original_ratio=entry['accepted_scale'],original_defect=entry['direction_fit_error'])
        certificates[key]=report
    status=('not_run' if not original['candidates'] else
            'passed' if all(item['status']=='passed' for item in certificates.values()) else 'failed')
    return {'status':status,'original_audit_status':original['status'],
        'original_failed_checks':failed,'certificates':certificates,
        'original_checks_preserved':True,'physical_or_accuracy_threshold_changes':0,
        'scope':'readback arithmetic certificate only; no new solve or production-code change'}
