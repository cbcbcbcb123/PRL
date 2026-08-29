# PRL integrated cell-engine policy

This directory is the PRL-owned cell-surface, contact, and remeshing engine.
It is integrated directly into the parent PRL repository, is derived from
SimuCell3D, and retains the upstream BSD 3-Clause license.

## Provenance

- Upstream: `https://git.bsse.ethz.ch/iber/Publications/2024_runser_simucell3d.git`
- Imported commit: `38af45154070b2b08dcdb25cbe629de499f382d9`
- Immutable baseline tag: `upstream-simucell3d-38af451`
- Final controlled-fork commit: `5864a63d5b77943812ddfeb2b44442dab4f8a068`
- Import archive tag in PRL: `prl-cell-engine-import-20260829`
- Monorepo integration tag in PRL: `prl-monorepo-integration-20260829`
- History-preserving PRL merge: `918d20c8e1090f4cbf9887994f50160da5042739`

The imported upstream and controlled-fork commits must remain reachable from
the PRL history. Do not rewrite their published history or remove upstream
copyright and license notices. The former GitHub repository
`cbcbcbcb123/prl-cell-engine` was deleted after its history and source tree were
verified in PRL.

## Scope

This fork owns only the high-performance cell-engine boundary:

- closed triangulated cell surfaces;
- contact and local mesh operations;
- synchronous remesh-event hooks required by PRL material-state transfer;
- portability, deterministic tests, CI, and performance work for this engine.

Volumetric ECM constitutive laws, cell-ECM coupling, coupled time integration,
Python experiment orchestration, and scientific evidence remain in the parent
PRL repository.

## Change policy

1. Keep reviewed upstream imports distinguishable from PRL-owned changes by
   explicit commits and provenance records.
2. Make owned changes on PRL feature branches and merge them only after focused
   remesh tests and the parent PRL contract tests pass.
3. One patch should deepen one seam. The first scientific seam is a synchronous
   callback after every accepted edge split, edge swap, and edge merge.
4. Public adapter types belong to PRL; upstream pointers and transient face IDs
   must not cross the boundary.
5. Record the upstream base, test commands, numerical behavior, and parent PRL
   commit for every release.

## Upstream refresh

Fetch the official source into a clearly named temporary or remote-tracking ref
inside the PRL repository, review the new range against the immutable baseline,
and integrate reviewed changes with an explicit merge or cherry-pick protected
by tests. Do not recreate a separately maintained PRL cell-engine repository
without a new human decision. Never rewrite baseline or import archive tags.
