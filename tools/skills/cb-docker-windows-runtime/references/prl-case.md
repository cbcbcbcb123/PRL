# PRL: verified history, not transferable repair authority

## 2026-09-17: temporary recovery

The user twice approved exact `System.IO.Directory.Move` quarantines of:

- `C:\Users\chenb\AppData\Local\Docker\run`
- `C:\Users\chenb\AppData\Local\docker-secrets-engine`

The first isolation exposed an older secrets socket; a validation start failed and created new runtime objects. Work stopped for a second exact-path approval. The second isolation and one subsequent startup recovered the engine. No deletion or alteration of `Docker\wsl`, VHDX, images, volumes, or unrelated settings was performed.

Historical observed versions: Desktop `4.89.0 (238018)`, Engine `29.7.2`, WSL kernel `6.6.87.2-microsoft-standard-WSL2`. Historical local `dolfinx/dolfinx:v0.11.0` image ID:

`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`

These are historical host-specific observations, not required versions or a current image qualification. No container, JIT, FEM, pull, install, update, or GPU work occurred in that recovery check.

## 2026-09-19: recurrence and the avoidable startup

Before startup, all five runtime objects rejected ACL reads with error 1920:

- `Docker/run/dockerEthernetVfkit`
- `Docker/run/dockerInference`
- `Docker/run/sailor-ingest.sock`
- `Docker/run/userAnalyticsOtlpHttp.sock`
- `docker-secrets-engine/engine.sock`

The engine API was unavailable. Despite this known signature, one user-authorized normal startup was attempted at 18:06:25 UTC+8. New backend logs at 10:06:28/10:06:59 UTC reported Ingest initialization and `sailor-ingest.sock` rename failure: `The file cannot be accessed by the system`. The backend crashed; the scientific four-case batch remained at zero containers/solves.

The startup was within the numerical permission count, but should have been stopped at the error-1920 precheck. The immediate socket-access failure is evidenced; why it repeatedly develops after shutdown remains unknown. Do not rewrite this into a proven Windows ACL, FEM, mesh, or material defect. Do not repeat quarantines indefinitely or reuse the September 17 approvals.

## Authoritative records to re-read when in PRL

Repository-relative paths (use the current checkout, not an assumed drive):

- `project_control/ventricle_fem_fenicsx_runtime_repair_execution_v01.md`
- `project_control/ventricle_mixed_cube_control_execution_v01.md`
- `project_control/evidence/mixed_cube_controls_v01_startup/startup.json`
- `project_control/evidence/mixed_cube_controls_v01_startup/backend_failure.log`

The three-line log excerpt's SHA-256 at skill creation was `cae385be43568861ffbe34efea120ed8fc3f905d0bf20504418a520a20e62128`. Later runtime state must be checked live, not inferred from this hash.

Global memory used as a cross-check: `MEMORY.md` Docker task group and `extensions/ad_hoc/notes/20260917-1801-docker-desktop-af-unix-runtime-repair.md`. Memory is not executable authority and has not been edited by this skill installation.

## FEniCSx-specific pitfalls after runtime recovery

Follow the **current project's** controlled launch recipe. Previously verified PRL runs preserved the image's library `PYTHONPATH` and used an executable `/root/.cache` tmpfs for JIT (`rw,exec,nosuid,nodev,size=536870912`). Overwriting that environment or using a non-executable JIT cache can create a separate error after Docker is healthy. This is not permission to mount anything, run a container, or change a scientific model.

Treat an orderly Desktop shutdown before a planned OS restart as an operational precaution requiring the appropriate user authority, not as a proven cure for recurrence.
