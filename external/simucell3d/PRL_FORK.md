# PRL controlled-fork policy

This repository is the PRL-owned cell-surface, contact, and remeshing engine.
It is derived from SimuCell3D and retains the upstream BSD 3-Clause license.

## Provenance

- Upstream: `https://git.bsse.ethz.ch/iber/Publications/2024_runser_simucell3d.git`
- Imported commit: `38af45154070b2b08dcdb25cbe629de499f382d9`
- Immutable baseline tag: `upstream-simucell3d-38af451`
- Upstream mirror branch: `upstream/main`
- Owned integration branch: `main`

The imported upstream commit must remain an ancestor of `main`. Do not rewrite
published history or remove upstream copyright and license notices.

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

1. Keep `upstream/main` byte-for-byte aligned with reviewed upstream imports.
2. Make owned changes on feature branches and merge them into `main` only after
   focused remesh tests and the parent PRL contract tests pass.
3. One patch should deepen one seam. The first scientific seam is a synchronous
   callback after every accepted edge split, edge swap, and edge merge.
4. Public adapter types belong to PRL; upstream pointers and transient face IDs
   must not cross the boundary.
5. Record the upstream base, test commands, numerical behavior, and parent PRL
   submodule commit for every release.

## Upstream refresh

Add the official source as an `upstream` remote, fetch it, review the new range
against `upstream/main`, then fast-forward only the mirror branch. Integrate
reviewed changes into `main` with an explicit merge or cherry-pick protected by
tests. Never force-push `main`, `upstream/main`, or baseline tags.
