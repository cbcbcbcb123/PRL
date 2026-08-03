# X1-K v08r1 recomputation commands

```powershell
$env:PYTHONPATH='src'
python -m pytest -q tests/hybrid/test_x1k_v08r1_adjudicator_repair.py tests/hybrid/test_x1k_v08_adjudication.py
python scripts/adjudicate_x1k_v08r1.py `
  --verification-dir results/hybrid/x1_k_revised_fixed_topology_v08r1/verification `
  --output-dir results/hybrid/x1_k_revised_fixed_topology_v08r1
```

The exporter has no hard-coded verification fallback. It requires the five versioned
command logs and matching `.exitcode` files; missing or inconsistent evidence fails closed.
