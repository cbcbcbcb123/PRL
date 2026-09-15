"""Artifact integrity, plotting-style and offline-link QA; no native solve."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from PIL import Image
from verify_myo_sheet_relaxation_v01 import ROOT,OUT
class Links(HTMLParser):
    def __init__(self):super().__init__();self.refs=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if (tag=='img' and key=='src') or (tag=='a' and key=='href'):self.refs.append(value)
def main():
    figures=OUT/'figures';pngs=list(figures.glob('*.png'));svgs=list(figures.glob('*.svg'))
    for path in pngs:
        with Image.open(path) as im:im.verify()
    for path in svgs:ET.parse(path)
    with Image.open(figures/'doublet_relaxation.gif') as im:
        frames=im.n_frames;assert frames==5
        for i in range(frames):im.seek(i);im.load()
    parser=Links();parser.feed((OUT/'index.html').read_text(encoding='utf-8'))
    missing=[ref for ref in parser.refs if not (OUT/unquote(ref.split('#')[0])).exists()];assert not missing
    styles=[]
    validator=Path('C:/Users/chenb/.codex/skills/cb-plot-unified-style/scripts/validate_cb_plot_style.py')
    for path in figures.glob('*_style_manifest.json'):
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(validator),str(path)],capture_output=True,text=True)
        styles.append({'manifest':path.name,'exit_code':result.returncode,'output':result.stdout+result.stderr})
    assert all(r['exit_code']==0 for r in styles)
    size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file());assert size<2*1024**3
    reviewed=['doublet_state_4.png','doublet_length.png','doublet_fields.png','quadrature_error.png','penetration_failure.png','penetration_sections.png','sheet_initial.png','sheet_residual.png']
    report={'artifact_checks':'passed','png_count':len(pngs),'svg_count':len(svgs),'gif_frames':frames,'offline_links_checked':len(parser.refs),'missing_links':missing,'style_checks':styles,'representative_static_visual_review':'passed','visually_inspected_files':reviewed,'live_browser_QA':'not_run','model_validation':'failed_nonpenetration','M_time_series_mesh_delivery':'failed_only_initial_saved','output_bytes':size,'notes':'Image parse/style/link QA does not imply scientific success. Raw partial M files retained.'}
    (OUT/'visual_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={str(p.relative_to(OUT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.name!='delivery_hashes.json'}
    (OUT/'delivery_hashes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
