"""Matched finite sheets and bounded, create-only real-kernel qualification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np

from ..storage import MIB, evaluate_storage, scan_workspace

RESULT = Path("results/ventricle_z1/z1_myo_sheet_pair_v01_20260916")
BUILD = Path("b/myo-mechanics-v01")
CONTRACT = Path("project_control/ventricle_myocardial_sheet_pair_contract_v01.md")
EXECUTABLE = BUILD / "src/ventricle_simucell3d_m0/Release/prl_myo_contact_barrier_relaxation_v01.exe"
SOURCE = Path("src/ventricle_simucell3d_m0/myo_contact_barrier_relaxation_v01.cpp")
LENGTH, WIDTH, HEIGHT, GAP = 9.0, 6.0, 5.3, .07
SEED = 20260916
VOLUME = (LENGTH-GAP)*(WIDTH-GAP)*HEIGHT
AREA = 2*((LENGTH-GAP)*(WIDTH-GAP)+(LENGTH-GAP)*HEIGHT+(WIDTH-GAP)*HEIGHT)
Q0 = AREA**3/VOLUME**2


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def make_sheet(irregular: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One partition, symmetric quadrature: per-cell volume is unchanged by waviness."""
    generator = np.random.default_rng(SEED)
    amplitudes = np.zeros((5, 4))
    amplitudes[1:4] = generator.uniform(.4, .8, (3, 4))*generator.choice([-1, 1], (3, 4)) if irregular else 0
    nx, ny, nz = 6, 8, 4
    keys = [(i, j, k) for i in range(nx+1) for j in range(ny+1) for k in range(nz+1)
            if i in (0, nx) or j in (0, ny) or k in (0, nz)]
    lookup = {key: index for index, key in enumerate(keys)}
    faces = []
    # For axes x,y,z the ordered tangents have positive cross product.
    for axis, extent in enumerate((nx, ny, nz)):
        first, second = (axis+1) % 3, (axis+2) % 3
        extents = (nx, ny, nz)
        for side in (0, extent):
            for u in range(extents[first]):
                for v in range(extents[second]):
                    quad = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        key = [0, 0, 0]; key[axis] = side; key[first] = u+du; key[second] = v+dv
                        quad.append(lookup[tuple(key)])
                    if side == 0:
                        quad.reverse()
                    faces.extend(((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])))
    points = []
    for row in range(4):
        for col in range(4):
            cell = []
            for i, j, k in keys:
                local_y = GAP/2 + (WIDTH-GAP)*j/ny
                wave = np.sin(2*np.pi*local_y/WIDTH)
                left = col*LENGTH+amplitudes[col, row]*wave+GAP/2
                right = (col+1)*LENGTH+amplitudes[col+1, row]*wave-GAP/2
                cell.append((left+(right-left)*i/nx, row*WIDTH+local_y, HEIGHT*(k/nz-.5)))
            points.append(cell)
    return np.asarray(points), np.asarray(faces, dtype=int), amplitudes


def perturbation(points: np.ndarray, kind: str) -> np.ndarray:
    direction = np.zeros_like(points)
    for cell in range(16):
        col = cell % 4
        if kind == "translation":
            if col in (1, 2):
                direction[cell, :, 0] = 1 if col == 1 else -1
        elif kind == "shape":
            # Zero on the actual end caps. Smooth, non-rigid, in-plane displacement.
            x, y = points[cell, :, 0], points[cell, :, 1]
            direction[cell, :, 0] = np.sin(np.pi*(x-GAP/2)/(4*LENGTH-GAP))*np.sin(2*np.pi*y/WIDTH)
        else:
            raise ValueError("unknown perturbation")
    return direction


def write_mesh(path: Path, points: np.ndarray, faces: np.ndarray) -> None:
    with path.open("x", encoding="ascii") as stream:
        stream.write(f"{len(points)}\n")
        for cell in points:
            stream.write(f"{len(cell)} {len(faces)}\n")
            np.savetxt(stream, cell, fmt="%.17g")
            np.savetxt(stream, faces, fmt="%d")


def _environment(root: Path) -> dict:
    environment = os.environ.copy()
    environment.update(OMP_NUM_THREADS="1", OMP_DYNAMIC="FALSE", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       TEMP=str(root/BUILD/"runtime_tmp"), TMP=str(root/BUILD/"runtime_tmp"), PYTHONDONTWRITEBYTECODE="1")
    return environment


def _call(root: Path, command: list, timeout: int) -> dict:
    began = time.monotonic()
    command = [str(value) for value in command]
    try:
        response = subprocess.run(command, cwd=root, env=_environment(root), capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return dict(command=command, return_code=response.returncode, stdout=response.stdout,
                    stderr=response.stderr, elapsed_seconds=time.monotonic()-began)
    except subprocess.TimeoutExpired as error:
        return dict(command=command, return_code=None, stdout=str(error.stdout), stderr=str(error.stderr),
                    elapsed_seconds=time.monotonic()-began, status="failed", reason="wall timeout; no retry")


def run_sheet(root: Path, phase: str = "static") -> dict:
    output = root/RESULT
    admission = evaluate_storage(scan_workspace(root), planned_new_bytes=256*MIB, stop_reserve_bytes=64*MIB)
    if not admission["can_start"]:
        return dict(status="blocked", reason="storage admission", storage=admission)
    if phase == "static":
        if output.exists():
            raise FileExistsError(f"create-only: {output}")
        output.mkdir()
        write_json(output/"ownership.json", dict(owner="Codex", purpose="matched sheet static qualification and conditional pilot",
                   gpu=False, threads=1, automatic_retries=0, maximum_new_bytes=256*MIB, stop_reserve_bytes=64*MIB))
        write_json(output/"storage_preflight.json", admission)
        write_json(output/"configuration.json", dict(q0=Q0, volume=VOLUME, seed=SEED, gap=GAP, shape_amplitude_static=0,
                   shape_amplitude_pilot=.060, dt=.01, steps=20, contract=CONTRACT.as_posix()))
        inputs = output/"inputs"; inputs.mkdir()
        for case in ("regular", "irregular"):
            points, faces, amplitudes = make_sheet(case == "irregular")
            np.savez_compressed(inputs/f"{case}.npz", points=points, faces=faces, amplitudes=amplitudes,
                                translation=perturbation(points, "translation"), shape=perturbation(points, "shape"))
            write_mesh(inputs/f"{case}.mesh", points, faces)
            for direction in ("translation", "shape"):
                for exponent in (4, 5):
                    for sign, factor in (("plus", 1), ("minus", -1)):
                        write_mesh(inputs/f"{case}_{direction}_e{exponent}_{sign}.mesh",
                                   points+factor*10**(-exponent)*perturbation(points, direction), faces)
        sources = [CONTRACT, SOURCE, Path(__file__).resolve().relative_to(root),
                   Path("src/prl/verification/myocardial_sheet.py"),
                   Path("external/simucell3d/src/mesh/cell.cpp"),
                   Path("external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp")]
        write_json(output/"source_hashes.json", {p.as_posix(): hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources})
        build = _call(root, ["cmake", "--build", root/BUILD, "--config", "Release", "--target",
                            "prl_myo_contact_barrier_relaxation_v01", "--parallel", "1"], 600)
        write_json(output/"build.json", build)
        if build["return_code"] != 0:
            return dict(status="failed", reason="build")
        write_json(output/"binary.json", dict(path=EXECUTABLE.as_posix(), sha256=hashlib.sha256((root/EXECUTABLE).read_bytes()).hexdigest()))
        static_root = output/"static"; static_root.mkdir()
        ledger = []
        for case in ("regular", "irregular"):
            names = [case]+[f"{case}_{direction}_e{exponent}_{sign}" for direction in ("translation", "shape")
                            for exponent in (4, 5) for sign in ("plus", "minus")]
            for name in names:
                record = _call(root, [root/EXECUTABLE, inputs/f"{name}.mesh", static_root/name, .01, 0, "clamp", 90, Q0, 0], 100)
                record["case"] = name; ledger.append(record)
                write_json(output/"static_execution.json", ledger)
                print(f"static {name}: exit={record['return_code']} ({record['elapsed_seconds']:.2f}s)", flush=True)
                if record["return_code"] != 0:
                    return dict(status="failed", reason="static process", case=name)
                if scan_workspace(root).logical_bytes-admission["usage"]["logical_bytes"] > 256*MIB:
                    return dict(status="blocked", reason="stage budget")
        from ..verification.myocardial_sheet import verify_sheet
        report = verify_sheet(output)
        write_json(output/"static_verification.json", report)
        return report
    if phase != "pilot":
        raise ValueError("unknown phase")
    from ..verification.myocardial_sheet import verify_sheet
    report = verify_sheet(output)
    if report["status"] != "passed":
        return dict(status="blocked", reason="static qualification has not passed", static=report["status"])
    pilot = output/"pilot"
    if pilot.exists():
        raise FileExistsError(f"create-only: {pilot}")
    pilot.mkdir()
    ledger = []
    for case in ("regular", "irregular"):
        record = _call(root, [root/EXECUTABLE, output/"inputs"/f"{case}.mesh", pilot/case, .01, 20, "clamp", 600, Q0, .060], 620)
        record["case"] = case; ledger.append(record); write_json(output/"pilot_execution.json", ledger)
        if record["return_code"] != 0:
            return dict(status="failed", reason="pilot process", case=case)
    return dict(status="passed", independent_verification="not_run", scope="pilot execution only")
