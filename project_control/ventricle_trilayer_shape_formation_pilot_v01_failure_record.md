# Z1-TF v01 result-package failure record

- Recorded: 2026-09-12
- Scope: `results/ventricle_z1/tissue_formation_pilot_v01_20260912`
- Package status: `failed`
- Parent Z1 status: `unresolved`

## Failure boundary

All four frozen static conditions completed 100 accepted updates and wrote their five mesh snapshots. The run then failed closed while exporting the unified-style quantitative figure. The style validator reported that the x-axis label, y-axis label, and `No cytoskeleton` tick label did not retain the required 12 pt canvas clearance.

This is a post-computation render/package failure. It does not invalidate the serialized cell meshes or metrics, but v01 is incomplete because the quantitative figure, final mechanics figure, report, index, provenance file, and independent verification were not all delivered. The v01 directory is therefore preserved unchanged as failure evidence and must not be relabeled as a completed package.

## Scientific screen already visible in frozen v01 data

- Reference-shape term: zero in every condition.
- Mesh and volume gates: passed in the runner summary.
- Central endocardial flatness / initial: `1.18202129600719`, below the frozen `1.50` target.
- Central myocardial elongation / initial: `0.9836709837418025`, below the frozen `1.10` target.
- Runner screening status before the rendering failure: `unknown`.

These values are retained as results, not tuned away. A render-only v02 repair may reuse the completed v01 computational arrays bit-for-bit after hashing them; it must not change parameters, states, gates, or scientific status.
