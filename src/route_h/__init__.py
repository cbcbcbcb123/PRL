"""Route H Stage 1 passive DCM–ECM verification kernel.

The package deliberately exposes no active-contraction implementation and no
full-patch trajectory runner.  Stage 0 v04 remains the immutable scientific
contract.
"""

from .contracts import STAGE0_CONTRACT_ID, assert_stage0_inputs

__all__ = ["STAGE0_CONTRACT_ID", "assert_stage0_inputs"]

