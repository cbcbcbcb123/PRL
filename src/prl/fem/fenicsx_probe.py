"""Container-only G0: imports, JIT and analytic scalar/matrix assembly."""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import time


def main():
    started = time.monotonic()
    import basix
    import dolfinx
    import ffcx
    import numpy as np
    import ufl
    from mpi4py import MPI
    from petsc4py import PETSc
    from dolfinx import fem, mesh
    from dolfinx.fem import petsc

    domain = mesh.create_unit_square(MPI.COMM_WORLD, 2, 2)
    space = fem.functionspace(domain, ("Lagrange", 1))
    field = fem.Function(space)
    field.interpolate(lambda x: x[0] + 2*x[1])
    measure = ufl.Measure("dx", domain=domain, metadata={"quadrature_degree": 6})
    area = float(fem.assemble_scalar(fem.form(fem.Constant(domain, PETSc.ScalarType(1))*measure)))
    energy = float(fem.assemble_scalar(fem.form(ufl.inner(ufl.grad(field), ufl.grad(field))*measure)))
    trial, test = ufl.TrialFunction(space), ufl.TestFunction(space)
    matrix = petsc.assemble_matrix(fem.form(ufl.inner(ufl.grad(trial), ufl.grad(test))*measure))
    matrix.assemble()
    constant = matrix.createVecRight()
    constant.set(1)
    residual = matrix.createVecLeft()
    matrix.mult(constant, residual)
    null_residual = float(residual.norm())
    mounts = Path('/proc/mounts').read_text().splitlines()
    cpu_max = Path('/sys/fs/cgroup/cpu.max').read_text().strip()
    memory_max = Path('/sys/fs/cgroup/memory.max').read_text().strip()
    checks = {
        'dolfinx_version': dolfinx.__version__.startswith('0.11.0'),
        'mpi_single_rank': MPI.COMM_WORLD.size == 1,
        'scalar_float64': np.dtype(PETSc.ScalarType) == np.dtype('float64'),
        'cpu_quota_one': cpu_max == '100000 100000',
        'memory_8gib': memory_max == str(8*1024**3),
        'unit_area': abs(area-1) < 1e-12,
        'affine_energy': abs(energy-5) < 1e-12,
        'laplacian_constant_nullspace': null_residual < 1e-12,
    }
    result = {
        'status': 'passed' if all(checks.values()) else 'failed',
        'checks': checks,
        'versions': {'dolfinx': dolfinx.__version__, 'basix': basix.__version__,
                     'ufl': ufl.__version__, 'ffcx': ffcx.__version__,
                     'petsc': PETSc.Sys.getVersion(), 'numpy': np.__version__,
                     'python': platform.python_version()},
        'measurements': {'area': area, 'affine_energy': energy,
                         'constant_null_residual': null_residual,
                         'matrix_shape': matrix.getSize(), 'matrix_norm': matrix.norm()},
        'environment': {k: os.environ.get(k) for k in
                        ['PYTHONPATH', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']},
        'mounts': [x for x in mounts if any(' '+p+' ' in x for p in ['/','/workspace','/root/.cache','/tmp'])],
        'cpu_max': cpu_max, 'memory_max': memory_max,
        'elapsed_seconds': time.monotonic()-started,
        'scientific_equilibrium_solves': 0,
    }
    print('PRL_G0_JSON='+json.dumps(result), flush=True)
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
