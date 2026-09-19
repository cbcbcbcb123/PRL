---
name: cb-docker-windows-runtime
description: Diagnose Windows Docker Desktop Linux-engine startup failures, especially AF_UNIX runtime sockets and error 1920, and gate local FEniCSx runtime readiness before startup. Use for missing dockerDesktopLinuxEngine, Ingest/Secrets initialization failures, or recurrence after quarantine; not for FEM convergence, ordinary Linux Docker, or automatic repair.
---

# Windows Docker runtime: check before starting

Prevent a known host-runtime failure from consuming another startup attempt. Diagnose first; keep normal startup, runtime repair, and scientific execution as separate authorities.

## Read-only entry

1. Read the current project's startup/repair decision and relevant prior failure record or memory. Old exact-path approval is historical, not permission to repeat it. For the PRL recurrence, read [the case reference](references/prl-case.md).
2. Before any Desktop startup, inspect the **current** Linux-engine API, both runtime roots, socket metadata/ACL accessibility, process/service/WSL state, and backend log timestamps. A running UI/backend process is not a ready engine.
3. Use the bundled standard-library helper on Windows:

   ```powershell
   python -B -X utf8 <skill-dir>/scripts/runtime_doctor.py --live
   ```

   It prints JSON, never writes files, never starts Desktop or a container, and only queries the explicit local `dockerDesktopLinuxEngine` named pipe. It ignores Docker endpoint/TLS overrides **in its child environment only**, not in user configuration. Its Windows PowerShell child rebuilds native module paths instead of inheriting PowerShell 7 modules. Paths with linked ancestors are not traversed. Each subprocess is bounded; there are no retries. Exit 0 means runtime preflight passed; 2 means blocked/unknown, not necessarily corruption.

   If a current contract pins a local image, add `--image <tag> --expected-image-id <sha256:...>`. This uses `image inspect`, never pull. Do not copy a historical image ID into a new contract. `--snapshot <file>` replays recorded JSON without subprocesses; `--prior-repair-recurred` only applies after reading evidence of recurrence.
4. Save necessary evidence only to an approved project path. The helper's limited log tail is context, **not** a complete log archive or repair/deletion manifest. Do not repeatedly poll unchanged state.

## Interpret evidence before consuming startup authority

- **Engine unavailable + current runtime ACL error 1920:** known access-failure signature. Stop ordinary startup attempts *before* invoking Desktop; report the affected absolute paths and request a separately scoped recovery decision. A fresh startup log naming failed Ingest/Secrets socket operations supports the immediate cause; the deeper reason for recurrence can remain `unknown`.
- **Zero bytes + ReparsePoint alone:** insufficient to diagnose damage. Missing engine pipe alone can mean Desktop is simply stopped. Missing CLI, timeouts, or incomplete filesystem inspection remain unknown/blocked, never passed.
- **Old log errors:** compare timestamps with the actual startup attempt. Never treat an earlier crash as a new failure. The helper deliberately does not infer current causation from log strings.
- **Engine API healthy but socket inspection abnormal:** report API readiness separately from the failed preflight; do not stop a healthy engine or attempt repair automatically.
- **No known signature and Desktop is merely stopped:** one normal startup can be proposed if needed, but only under the user's current startup authority. Use a hidden window for a background launch. If the user explicitly requests one controlled reproduction after being told the known signature, honor that bounded request and identify it as reproduction, not repair.
- **Same signature recurs after controlled repair:** stop directory-rotation retries. A maintainer-supported Docker fix or a separately scoped alternative runtime may be evaluated; this skill does not authorize installs, updates, migration, mounts, or settings changes.

## Repair is not automated

Only after the user chooses repair, prepare a frozen manifest with normalized absolute source/destination paths, object counts/bytes, link/reparse checks, relevant process IDs, interface, irreversible risks, and protected paths. Inaccessible socket contents cannot be honestly hashed; record that limitation. Do not infer their integrity from zero length.

For this failure class, a whole-directory `System.IO.Directory.Move` to an exact approved quarantine was historically effective. It is **not** a universal fix and not authorization:

- Recheck approved source/destination boundaries and state immediately before execution. Stop only the specifically authorized, currently verified processes. Never overwrite a quarantine destination.
- Never touch Docker `wsl`, VHDX files, images, volumes, unrelated settings, or another user's runtime. Do not fall back to socket deletion, ACL changes, factory reset, WSL shutdown/unregister, or manual backend launching.
- Move one authorized directory at a time; verify source absence and destination metadata. Partial completion, new objects, a newly exposed older directory, or a changed target requires stopping and a new audit/decision. Do not automatically repeat the old manifest.
- After the approved isolation, allow only the agreed number of validation starts (historically one), then bounded local API and pinned-image checks. Retain quarantines; deleting them needs separate exact approval.

No supplied script implements repair, process termination, startup, cleanup, or scientific execution.

## Handoff

Report separately: `runtime API`, `preflight`, `local image`, `scientific execution`, actual startup/container/solve counts, current evidence, and the one next decision needed. Use `passed / failed / blocked / not_run / unknown`; file existence and host tests do not establish scientific success.

An engine/image check does not prove FEniCSx import, JIT, equilibrium, or biological validity. Resume a scientific batch only when its original authority is still valid and its own guards pass. For PRL, preserve the existing image-library environment and JIT mount recipe in the current contract; do not replace them with ad hoc container commands.

## Check this skill

```powershell
python -B -X utf8 -m unittest discover -s <skill-dir>/scripts -p test_runtime_doctor.py -v
```

Tests cover unavailable engines, error 1920, misleading ReparsePoint metadata/old logs, timeouts, recurrence, image mismatch, local-only endpoints, and zero mutation calls. Synthetic tests do not replace a live read-only check or validate a repair.
