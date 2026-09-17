"""Bounded RED/GREEN real-kernel qualification; not a tissue simulation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from prl.storage import MIB, evaluate_storage, scan_workspace
from prl.workspace import find_workspace

RESULT = Path("results/ventricle_z1/z1_myo_passive_audit_v01_20260916")
BUILD = Path("b/myo-mechanics-v01")
SOURCES = (
    "external/simucell3d/src/mesh/cell.cpp",
    "external/simucell3d/include/mesh/cell.hpp",
    "src/ventricle_bioform_myo/passive_mechanics_probe.cpp",
    "src/ventricle_bioform_myo/ventricle_bioform_myo_v03.cpp",
    "src/ventricle_bioform_myo/CMakeLists.txt",
    "project_control/ventricle_myocardial_irregular_sheet_recenter_v01.md",
)


def run_audit(phase: str, workspace: Path | None = None) -> dict:
    root = find_workspace(workspace)
    result, build = root / RESULT, root / BUILD
    phase_record = result / f"{phase}_execution.json"
    if phase_record.exists() or (result / phase).exists():
        raise ValueError("create-only audit phase already exists")
    if phase == "green" and not (result / "red_execution.json").is_file():
        raise ValueError("RED evidence is required before GREEN")
    admission = evaluate_storage(scan_workspace(root), planned_new_bytes=256*MIB, stop_reserve_bytes=64*MIB)
    if not admission["can_start"]:
        raise RuntimeError("storage admission rejected")
    result.mkdir(parents=True, exist_ok=True)
    temporary = build / "runtime_tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update({"TEMP": str(temporary), "TMP": str(temporary), "OMP_NUM_THREADS": "1",
                        "OMP_DYNAMIC": "FALSE", "PYTHONDONTWRITEBYTECODE": "1",
                        "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    record = {"phase": phase, "status": "not_run", "admission": admission, "calls": [], "sources": []}
    for relative in SOURCES:
        source = root / relative
        target = result / f"{phase}_source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError("source snapshot already exists")
        shutil.copy2(source, target)
        record["sources"].append({"path": relative, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    commands = [
        (["cmake", "-S", str(root), "-B", str(build), "-G", "Visual Studio 17 2022", "-A", "x64"], 120),
        (["cmake", "--build", str(build), "--config", "Release", "--target", "prl_passive_mechanics_probe", "--parallel", "1"], 480),
        ([str(build / "src/ventricle_bioform_myo/Release/prl_passive_mechanics_probe.exe"), str(result / phase)], 120),
    ]
    try:
        for index, (command, limit) in enumerate(commands):
            began = time.monotonic()
            completed = subprocess.run(command, cwd=root, env=environment, timeout=limit,
                                       capture_output=True, text=True, encoding="utf-8", errors="replace")
            record["calls"].append({"command": command, "return_code": completed.returncode,
                                    "elapsed_seconds": time.monotonic()-began,
                                    "stdout": completed.stdout, "stderr": completed.stderr})
            if completed.returncode and index != 2:
                raise RuntimeError("build/configure failed; see execution record")
            growth = scan_workspace(build).logical_bytes + scan_workspace(result).logical_bytes
            if growth > 256*MIB:
                raise RuntimeError("audit stage storage budget exceeded")
        record["status"] = "passed" if completed.returncode == 0 else "failed"
        record["scope"] = "real-kernel static mechanics only; tissue dynamics not_run"
        record["stage_bytes"] = growth
        record["binary_sha256"] = hashlib.sha256(Path(commands[-1][0][0]).read_bytes()).hexdigest()
    except Exception as error:
        record["status"] = "failed"
        record["error"] = str(error)
        raise
    finally:
        phase_record.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return record


def run_regressions(workspace: Path | None = None) -> dict:
    """Build affected entry points and check precision / explicit-input guard."""
    root = find_workspace(workspace)
    output = root / RESULT / "regression_execution.json"
    if output.exists():
        raise ValueError("create-only regression record exists")
    if not json.loads((root/RESULT/"green_verification.json").read_text())["status"] == "passed":
        raise ValueError("independent GREEN qualification required")
    admission = evaluate_storage(scan_workspace(root), planned_new_bytes=64*MIB, stop_reserve_bytes=64*MIB)
    if not admission["can_start"]:
        raise RuntimeError("storage admission rejected")
    environment = os.environ.copy()
    environment.update({"TEMP": str(root/BUILD/"runtime_tmp"), "TMP": str(root/BUILD/"runtime_tmp"),
                        "OMP_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    base = root/BUILD
    binary = base/"src/ventricle_simucell3d_m0/Release/prl_myo_contact_barrier_relaxation_v01.exe"
    commands = [
        (["cmake", "--build", str(base), "--config", "Release", "--target", "prl_surface_energy_precision", "prl_myo_contact_barrier_relaxation_v01", "--parallel", "1"], 240, 0),
        ([str(base/"src/ventricle_bioform_myo/Release/prl_surface_energy_precision.exe")], 120, 0),
        ([str(binary)], 10, 2),
    ]
    record = {"status": "not_run", "calls": [], "scope": "build, precision, missing-explicit-material rejection; no time integration"}
    try:
        for command, timeout, expected in commands:
            completed = subprocess.run(command, cwd=root, env=environment, timeout=timeout,
                                       capture_output=True, text=True, encoding="utf-8", errors="replace")
            record["calls"].append({"command": command, "return_code": completed.returncode,
                                    "expected_return_code": expected, "stdout": completed.stdout, "stderr": completed.stderr})
            if completed.returncode != expected:
                raise RuntimeError("regression failed")
        record["status"] = "passed"
        record["entry_source_sha256"] = hashlib.sha256((root/"src/ventricle_simucell3d_m0/myo_contact_barrier_relaxation_v01.cpp").read_bytes()).hexdigest()
        record["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    except Exception as error:
        record["status"] = "failed"
        record["error"] = str(error)
        raise
    finally:
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("red", "green", "regressions"))
    arguments = parser.parse_args()
    result = run_regressions() if arguments.phase == "regressions" else run_audit(arguments.phase)
    print(json.dumps({key: value for key, value in result.items() if key not in ("calls", "admission", "sources")}, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
