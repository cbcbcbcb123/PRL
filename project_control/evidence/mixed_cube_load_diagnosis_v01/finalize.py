"""Preserve checks and render one exploratory page; no native solve or deletion."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from prl.result_store import result_path
from prl.runs.mixed_cube_load_diagnosis import STAGE, digest, save

workspace = Path.cwd()
root = result_path(workspace, STAGE)
render_only = '--render-only' in sys.argv
if (root / 'manifest.json').exists() or ((root / 'tests.json').exists() and not render_only):
    raise FileExistsError('Create-only delivery; never overwrite frozen evidence')
environment = {**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
command = [sys.executable, '-B', '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
           'tests/prl/test_mixed_cube.py', 'tests/prl/test_positive_j.py',
           'tests/prl/test_volume_projection.py', 'tests/prl/test_mixed_cube_loads.py']
if not render_only:
    tests = subprocess.run(command, cwd=workspace, env=environment, capture_output=True,
                           text=True, encoding='utf-8', timeout=120)
    save(root / 'tests.json', {'status': 'passed' if tests.returncode == 0 else 'failed',
                             'command': command, 'returncode': tests.returncode,
                             'stdout': tests.stdout, 'stderr': tests.stderr})
test_record = json.loads((root / 'tests.json').read_text(encoding='utf-8'))
if test_record['status'] != 'passed':
    raise RuntimeError('Targeted checks failed; preserved tests.json')
style_source = Path('C:/Users/chenb/.codex/skills/cb-plot-unified-style/assets/cb_plot_unified_style.py')
style_target = root / 'source_code/cb_plot_unified_style.py'
if not render_only:
    shutil.copy2(style_source, style_target)
suffix = '_layout_v02' if render_only else ''
for origin, target_name in [(workspace / 'src/prl/rendering/mixed_cube_loads.py', 'render_mixed_cube_loads'),
                             (Path(__file__), 'finalize')]:
    target = root / 'source_code' / (target_name + suffix + '.py')
    if target.exists():
        raise FileExistsError('Source snapshot exists: ' + str(target))
    shutil.copy2(origin, target)
os.environ['MPLCONFIGDIR'] = str(root / '.plot_cache')
spec = importlib.util.spec_from_file_location('load_diagnosis_style', style_target)
style = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = style
spec.loader.exec_module(style)
from prl.rendering.mixed_cube_loads import draw
figures = draw(root, style)
validator_path = style_source.parent.parent / 'scripts/validate_cb_plot_style.py'
spec = importlib.util.spec_from_file_location('load_diagnosis_style_validator', validator_path)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
errors, warnings = validator.validate_manifest(Path(figures['manifest']))
expected_dpi_errors = [error for error in errors if '600' in error and ('dpi' in error.lower())]
unexpected = [error for error in errors if error not in expected_dpi_errors]
save(root / 'figure_check.json', {'exploratory_layout_status': 'passed' if not unexpected else 'failed',
     'publication_600dpi_status': 'failed' if errors else 'passed', 'errors': errors, 'warnings': warnings,
     'authorized_exception': '160dpi exploratory one-page diagnosis; not a publication figure',
     'visual_review': 'not_run', 'outputs': figures})
if unexpected:
    raise RuntimeError('Unexpected figure verification failure')
sources = json.loads((root / 'sources.json').read_text(encoding='utf-8'))
if not all(digest(path) == value for path, value in sources['protected_sha256'].items()):
    raise ValueError('Protected evidence drift')
print(json.dumps({'tests': test_record['stdout'], 'figures': figures, 'style_errors': errors,
                  'protected_files': len(sources['protected_sha256'])}, ensure_ascii=False))
