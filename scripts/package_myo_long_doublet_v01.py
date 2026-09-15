"""Delivery-only integrity checks; never launches a scientific calculation."""
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from verify_myo_sheet_relaxation_delivery_v01 import Links
from run_myo_long_doublet_v01 import ROOT, OUT

def main():
    figures=OUT/'figures'
    pngs=list(figures.glob('*.png'));svgs=list(figures.glob('*.svg'))
    assert len(pngs)==len(svgs)==15
    for path in pngs:
        with Image.open(path) as im:im.verify()
    for path in svgs:ET.parse(path)
    with Image.open(figures/'long_doublet.gif') as im:
        assert im.n_frames==5
        for i in range(im.n_frames):im.seek(i);im.load()
    parser=Links();parser.feed((OUT/'index.html').read_text(encoding='utf-8'))
    missing=[ref for ref in parser.refs if not (OUT/ref.split('#')[0]).exists()]
    assert not missing,missing
    validator=Path('C:/Users/chenb/.codex/skills/cb-plot-unified-style/scripts/validate_cb_plot_style.py')
    styles=[]
    for path in figures.glob('*_style_manifest.json'):
        result=subprocess.run([sys.executable,'-B','-X','utf8',str(validator),str(path)],capture_output=True,text=True)
        styles.append({'manifest':path.name,'exit_code':result.returncode,'output':result.stdout+result.stderr})
    assert len(styles)==6 and all(r['exit_code']==0 for r in styles)
    size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file());assert size<2*1024**3
    reviewed=['state_4.png','minimum_angle.png','static_cost.png','scaling_structures.png','cell_length.png','residual.png','minimum_gap.png','end_fields.png','adaptive_steps.png']
    qa={'artifact_checks':'passed','png_count':15,'svg_count':15,'gif_frames':5,'offline_links_checked':len(parser.refs),'missing_links':missing,'style_checks':styles,'representative_static_visual_review':'passed','visually_inspected_files':reviewed,'live_browser_QA':'not_run','output_bytes':size,'notes':'Actual solver data only; artifact QA is not biological validation. Pressure uses a zero-based scale to avoid exaggerating tiny differences.'}
    (OUT/'visual_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    numerical=json.loads((OUT/'long_verdict.json').read_text())
    adaptive=json.loads((OUT/'A/verdict.json').read_text())
    performance=json.loads((OUT/'P/verdict.json').read_text())
    assert numerical['status']==adaptive['status']==performance['status']=='passed'
    verdict={'status':'passed','scope':'bounded long-doublet numerical qualification, adaptive safety and static profiling only','long_doublet_numerical':'passed','actual_adaptive_clipping':'passed','static_profiling':'passed','static_equilibrium':'failed','parent_Z1':'blocked','biological_validation':'blocked','sixteen_cell_dynamics':'not_run','performance_optimization':'not_run','morphology_heterogeneity':'not_run','cleanup_previous_temp':'blocked','evidence':['long_verdict.json','A/verdict.json','P/verdict.json','visual_qa.json'],'interpretation':'Residual around 0.104 exceeds 0.001 at coordinate 5; finite-horizon nonconvergence does not prove asymptotic instability. No universal no-fold or no-crossing proof.'}
    (OUT/'verdict.json').write_text(json.dumps(verdict,ensure_ascii=False,indent=2),encoding='utf-8')
    files=['scripts/run_myo_long_doublet_v01.py','scripts/verify_myo_long_doublet_v01.py','scripts/myo_fold_monitor_v01.py','scripts/run_myo_long_doublet_extensions_v01.py','scripts/render_myo_long_doublet_v01.py','scripts/render_myo_long_doublet_extensions_v01.py','scripts/package_myo_long_doublet_v01.py','tests/test_myo_adjacent_fold_monitor_v01.py','src/ventricle_simucell3d_m0/myo_contact_scaling_probe_v01.cpp','src/ventricle_simucell3d_m0/CMakeLists.txt','project_control/ventricle_myocardial_long_doublet_contract_v01.md','project_control/ventricle_myocardial_long_doublet_execution_v01.md','docs/myocardial_shape_variability_literature_v01.md','b/z1m0a/Release/prl_myo_contact_scaling_probe_v01.exe']
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    (OUT/'delivery_source_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    manifest={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.name!='delivery_hashes.json'}
    (OUT/'delivery_hashes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'verdict':verdict,'artifact_count':len(manifest),'output_bytes':size,'styles':len(styles),'links':len(parser.refs)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
