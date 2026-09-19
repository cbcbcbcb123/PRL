"""Floating-point endpoint certificates; fixture values are not science data."""
import numpy as np
from prl.verification.saved_segment import exact_endpoint_certificate


def test_exact_rounded_endpoint_is_not_rejected_by_cancellation():
    current=np.array([4.,3.,2.])
    direction=np.array([2e-8,1e-9,-3e-10])
    accepted=current-direction
    ratio=float((current-accepted)@direction/(direction@direction))
    assert abs(ratio-1.)>1e-10
    report=exact_endpoint_certificate(current,direction,accepted,1.)
    assert report['status']=='passed'
    assert report['maximum_endpoint_difference']==0.


def test_even_one_ulp_endpoint_change_does_not_receive_exact_certificate():
    current=np.array([4.,3.,2.]); direction=np.array([2e-8,1e-9,-3e-10])
    accepted=current-direction
    accepted[0]=np.nextafter(accepted[0],np.inf)
    assert exact_endpoint_certificate(current,direction,accepted,1.)['status']=='failed'


def test_wrong_scale_and_nonfinite_state_are_not_certified():
    current=np.array([4.,3.,2.]); direction=np.array([.2,.1,-.3])
    accepted=current-.5*direction
    assert exact_endpoint_certificate(current,direction,accepted,.5)['status']=='passed'
    assert exact_endpoint_certificate(current,direction,accepted,1.)['status']=='failed'
    assert exact_endpoint_certificate(current,direction,accepted,float('nan'))['status']=='failed'
