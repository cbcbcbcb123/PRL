"""Dimension-neutral state sequencing/identity, with no mechanical judgment."""
from pathlib import Path
import numpy as np


def is_retained(config,name,label):
    return bool(config.get('reuse_m0_zero',False) and name=='M0' and label=='zero')


def state_path(root,config,name,label):
    folder='retained' if is_retained(config,name,label) else 'raw'
    return Path(root)/folder/f'{name}_state_{label}.npz'


def remaining_states(config,name):
    return [spec for spec in config['states'] if not is_retained(config,name,spec['label'])]


def advance_case(solid,config,states,before_solve,after_solve):
    """Never retry an exception; caller supplies one explicit retained state map."""
    for spec in remaining_states(config,solid.name):
        initial=np.zeros_like(solid.w.x.array) if spec['initial'] is None else states[spec['initial']]
        before_solve(spec)
        state=solid.solve(spec,initial)
        states[spec['label']]=state
        after_solve(spec)
    return states


def restart_identity(current,retained,state,vector_size):
    """Exact identity, except the known row/flat integer-map layout difference."""
    checks={'same_keys':set(current)==set(retained)}
    for key in sorted(set(current)|set(retained)):
        if key not in current or key not in retained:
            checks[key]=False
        elif key in ['mixed_u_map','mixed_p_map']:
            checks[key]=bool(current[key].ndim==1 and np.array_equal(current[key],retained[key].ravel()))
        else:
            checks[key]=bool(np.array_equal(current[key],retained[key]))
    checks['vector_size']=state['mixed_state'].shape==(vector_size,)
    checks['zero_load']=float(state['load'])==0. and float(state['activation'])==0.
    if checks['vector_size'] and checks.get('mixed_u_map') and checks.get('mixed_p_map'):
        checks['state_u']=bool(np.array_equal(state['mixed_state'][current['mixed_u_map']],state['u'].ravel()))
        checks['state_p']=bool(np.array_equal(state['mixed_state'][current['mixed_p_map']],state['pressure'].ravel()))
    else:
        checks['state_u']=checks['state_p']=False
    return checks
