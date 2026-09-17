"""Pure filesystem smoke test; no FEM/JIT, networking, installation or deletion."""
import json
from pathlib import Path
import shutil

root=Path('/out')
expected='prl-external-result-store-v01'
for sequence in [1,2]:
    record=json.loads((root/f'host_round_{sequence}.json').read_text())
    assert record=={'identity':expected,'sequence':sequence}
target=root/'docker_roundtrip.json'
with target.open('x') as handle:
    json.dump({'identity':expected,'rounds_read':2,'solver_calls':0,
               'disk_free_bytes':shutil.disk_usage(root).free},handle,indent=2)
assert json.loads(target.read_text())['solver_calls']==0
print('PRL_EXTERNAL_IO_PASSED; no scientific solves',flush=True)
