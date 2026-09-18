"""Create-only controller for one approved retained-state matrix diagnosis."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time

from prl.fem.ring_geometry import configuration as ring_configuration
from prl.result_store import result_path,result_admission,disk_admission
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_contour import protected
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import read_docker,IMAGE,TAG,container_command,save_json,verify_container_settings

RESULT=Path('results/ventricle_fem/f6s1s_linear_system_diagnosis_v01_20260918')
SOURCE_RESULT=Path('results/ventricle_fem/f6s1r_pressure_space_v01_20260918')
CONTRACT=Path('project_control/ventricle_fem_mixed_linear_diagnosis_contract_v01.md')
REPLAY_RESULT=Path('results/ventricle_fem/f6s1s2_linear_report_replay_v01_20260918')
REPLAY_CONTRACT=Path('project_control/ventricle_fem_mixed_linear_replay_contract_v01.md')
WORKSPACE_RESULT=Path('results/ventricle_fem/f6s1s3_mumps_workspace_v01_20260918')
WORKSPACE_CONTRACT=Path('project_control/ventricle_fem_mumps_workspace_contract_v01.md')


def configuration(workspace_margin=False):
    cfg=ring_configuration()
    cfg.update(schema_version='prl.mixed_linear_diagnosis.v1',pressure_space='DG2',
               loads=[.02],meshes=[cfg['meshes'][0]],scope='retained initial tangent only; no equilibrium solve',
               nonlinear_equilibrium_solves=0,matrix_assemblies=1,mumps_factorizations=1,
               superlu_factorizations=1,automatic_retries=0,
               resources={'seconds':300,'threads':1,'gpu':0})
    if workspace_margin:
        cfg['solver']['mat_mumps_icntl_14']=100
        cfg.update(workspace_margin=True,matrix_assemblies=0,superlu_factorizations=0,
                   relative_residual_limit=1e-8,relative_solution_difference_limit=1e-6,
                   scope='saved CSR only; one MUMPS workspace-margin check; no FEM state update')
    return cfg


def run_diagnosis(workspace, replay=False, workspace_margin=False):
    workspace=Path(workspace).resolve(strict=True)
    if replay and workspace_margin:
        raise ValueError('Choose only one diagnostic mode')
    contract=WORKSPACE_CONTRACT if workspace_margin else REPLAY_CONTRACT if replay else CONTRACT
    target=WORKSPACE_RESULT if workspace_margin else REPLAY_RESULT if replay else RESULT
    root=result_path(workspace,target,new=True)
    if not (workspace/contract).is_file():
        raise ValueError('Approved diagnosis contract is missing')
    source=result_path(workspace,SOURCE_RESULT)
    source_manifest=json.loads((source/'manifest.json').read_text())
    if not all(digest(source/item['path'])==item['sha256'] for item in source_manifest['files']):
        raise ValueError('F6-S1-R source package identity drift')
    version=json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server') or read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned local runtime unavailable; no restart, install or pull permitted')
    admission=result_admission(workspace,64*1024**2,64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    parents=protected(workspace,fine=True)
    source_hashes={str(path):digest(path) for path in source.rglob('*') if path.is_file()}
    previous=result_path(workspace,REPLAY_RESULT if workspace_margin else RESULT) if replay or workspace_margin else None
    if previous is not None:
        prior_manifest=json.loads((previous/'manifest.json').read_text())
        if not all(digest(previous/item['path'])==item['sha256'] for item in prior_manifest['files']):
            raise ValueError('F6-S1-S evidence identity drift')
        source_hashes.update({str(path):digest(path) for path in previous.rglob('*') if path.is_file()})
        if workspace_margin:
            ancestors=json.loads((previous/'source_result_preflight.json').read_text())
            if not all(digest(path)==sha for path,sha in ancestors.items()):
                raise ValueError('Preserved ancestor evidence changed')
            source_hashes.update(ancestors)
    with scientific_lock(workspace):
        root.mkdir(parents=True,exist_ok=False)
        save_json(root/'storage_preflight.json',admission)
        cfg=configuration(workspace_margin=workspace_margin)
        cfg['report_replay']=replay
        save_json(root/'configuration.json',cfg)
        if previous is not None:
            shutil.copyfile(previous/'matrix_csr.npz',root/'previous_matrix_csr.npz')
        if workspace_margin:
            for original,renamed in [('mumps_diagnosis.json','previous_mumps_diagnosis.json'),
                                     ('superlu_linear_solution.npz','reference_superlu_solution.npz'),
                                     ('configuration.json','previous_configuration.json')]:
                shutil.copyfile(previous/original,root/renamed)
        save_json(root/'docker_version.json',version)
        save_json(root/'protected_preflight.json',parents)
        save_json(root/'source_result_preflight.json',source_hashes)
        inputs=root/'source_f6s1r'; inputs.mkdir()
        for name in ['M0_mesh.npz','M0_state_passive_0.npz','M0_state_passive_0.json',
                     'M0_state_passive_1.npz','M0_state_passive_1.json']:
            shutil.copyfile(source/'ring/raw'/name,inputs/name)
        sources=['src/prl/fem/fenicsx_linear_system.py','src/prl/fem/fenicsx_ring.py',
                 'src/prl/fem/ring_geometry.py','src/prl/verification/fenicsx_linear_system.py',
                 'src/prl/verification/fenicsx_pressure.py','src/prl/verification/fenicsx_ring.py',
                 'src/prl/runs/fenicsx_linear_system.py','src/prl/runs/fenicsx_runtime.py',
                 'src/prl/runs/fem_finite_strain.py','src/prl/result_store.py',
                 'project_control/result_storage_policy.json',contract.as_posix()]
        for relative in sources:
            destination=root/'sources_at_execution'/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(workspace/relative,destination)
        save_json(root/'source_hashes.json',{relative:digest(workspace/relative) for relative in sources})
        name='prl-f6s1s3-mumps-workspace-v01-20260918' if workspace_margin else 'prl-f6s1s2-linear-report-replay-v01-20260918' if replay else 'prl-f6s1s-linear-diagnosis-v01-20260918'
        args=container_command(workspace,name,'/workspace/src/prl/fem/fenicsx_linear_system.py',root)
        save_json(root/'command.json',args)
        save_json(root/'diagnostic_started.json',{'container_invocations':1,'nonlinear_equilibrium_solves':0,
                  'matrix_assemblies':cfg['matrix_assemblies'],'automatic_retries':0})
        started=time.monotonic(); stop_reason=None
        with (root/'stdout.log').open('x',encoding='utf-8') as stdout,(root/'stderr.log').open('x',encoding='utf-8') as stderr:
            process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
            try:
                while process.poll() is None:
                    disk=disk_admission(root,0)
                    if time.monotonic()-started>300 or not disk['can_start']:
                        stop_reason='deadline' if time.monotonic()-started>300 else 'disk free floor'
                        read_docker('stop','--time','5',name); process.wait(timeout=20); break
                    time.sleep(.5)
            except BaseException:
                read_docker('stop','--time','5',name); process.wait(timeout=20)
                raise
        inspection=json.loads(read_docker('inspect',name))[0]
        save_json(root/'container_inspect.json',inspection)
        settings=verify_container_settings(inspection)
        unchanged=all(digest(workspace/path)==value for path,value in parents.items())
        source_unchanged=all(digest(path)==value for path,value in source_hashes.items())
        report={'status':'passed' if process.returncode==0 and all(settings.values()) and unchanged and source_unchanged and stop_reason is None else 'failed',
                'exit_code':process.returncode,'stop_reason':stop_reason,'container_checks':settings,
                'protected_parent_files':len(parents),'parents_unchanged':unchanged,
                'source_result_files':len(source_hashes),'source_result_unchanged':source_unchanged,
                'diagnostic_container_invocations':1,'nonlinear_equilibrium_solves':0,
                'automatic_retries':0,'gpu':0,'elapsed_seconds':time.monotonic()-started}
        save_json(root/'execution.json',report)
        save_json(root/'formal_invocation_manifest.json',package_manifest(root))
        return report


def finalize_diagnosis(workspace):
    """Seal the failed invocation from saved evidence; never repeat a factorization."""
    from prl.result_store import register_result
    from prl.verification.fenicsx_linear_system_result import verify_linear_system_result

    workspace=Path(workspace).resolve(strict=True)
    root=result_path(workspace,RESULT)
    formal=json.loads((root/'formal_invocation_manifest.json').read_text(encoding='utf-8'))
    identities={item['path']:(root/item['path']).is_file() and digest(root/item['path'])==item['sha256']
                for item in formal['files']}
    if not all(identities.values()):
        raise ValueError('Formal diagnostic invocation evidence changed')
    verification=verify_linear_system_result(root,workspace,save=True)
    if verification['verification_status']!='passed':
        raise ValueError('Independent retained-matrix verification failed')
    rendering=json.loads((root/'rendering.json').read_text(encoding='utf-8'))
    final_png=root/'figures/FigS1S_linear_system_diagnosis_v02_20260918.png'
    final_svg=root/'figures/FigS1S_linear_system_diagnosis_v02_20260918.svg'
    if not final_png.is_file() or not final_svg.is_file():
        raise ValueError('Visually reviewed final diagnostic figure is missing')
    rendering.update(visual_qa='passed_after_v02_bottom_label_review',
                     final_png=final_png.relative_to(root).as_posix(),
                     final_svg=final_svg.relative_to(root).as_posix(),
                     retained_draft=['figures/FigS1S_linear_system_diagnosis_v01_20260918.png',
                                     'figures/FigS1S_linear_system_diagnosis_v01_20260918.svg'])
    save_json(root/'rendering.json',rendering)
    summary={'status':'failed','execution_status':'failed','independent_post_verification':'passed',
             'diagnostic_delivery_status':'failed','scientific_root_cause_status':'not_evaluable',
             'model':'2-D plane-strain P2 displacement / cellwise DG2 pressure; mu=1, kappa=1000',
             'load':'retained ideal annulus initial state at p/mu=0.02; follower cavity pressure; active stress=0',
             'matrix':verification['matrix'],'derived':verification['derived'],
             'excluded_by_saved_matrix':['nonfinite assembled entries','zero rows or columns',
                                          'structural rank deficiency','singular cellwise pressure block'],
             'supported_hypothesis':'severe mixed-block scale separation / small numerical pivots',
             'confirmed_mumps_reason':False,
             'failure':'a nonfinite MUMPS diagnostic value was rejected by strict JSON; exact KSP/PC/MUMPS and SuperLU outcomes were not retained',
             'nonlinear_equilibrium_solves':0,'newton_state_updates':0,'automatic_retries':0,'gpu':0,
             'contour':'not_run','three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run',
             'figure':final_png.relative_to(root).as_posix(),
             'next_action':'pending approval: one corrected report-only replay of the same retained matrix diagnosis; no equilibrium solve or parameter change'}
    save_json(root/'summary.json',summary)
    index=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>F6-S1-S 混合线性系统诊断</title>
<style>body{{max-width:1050px;margin:32px auto;padding:0 20px;color:#17221d;font:16px/1.6 "Segoe UI","Microsoft YaHei",sans-serif}}.fail{{color:#9b2f2f}}.ok{{color:#146b4d}}img{{width:100%;border:1px solid #d9e1dc}}code{{background:#f2f5f3;padding:2px 5px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #d9e1dc;padding:8px;text-align:left}}</style></head><body>
<h1>F6-S1-S｜P2/DG2 混合线性系统诊断</h1><p><b class="fail">执行与诊断交付 FAILED</b>；<b class="ok">保存矩阵的独立复核 PASSED</b>。这不是新的平衡计算。</p>
<img src="{final_png.relative_to(root).as_posix()}" alt="mixed matrix diagnosis">
<h2>结论</h2><p>9,216阶矩阵有限、无零行/列且满结构秩，896个逐单元压力块全部满秩；但位移块与压力块Frobenius范数相差约3.14e7，至少2,688个高阶压力模态只由很小的有限体积模量块约束。证据支持尺度/小主元风险，但未保存MUMPS INFOG，根因仍为not_evaluable。</p>
<table><tr><th>执行</th><th>结果</th></tr><tr><td>非线性平衡求解</td><td>0</td></tr><tr><td>自动重跑 / GPU</td><td>0 / 0</td></tr><tr><td>结构秩</td><td>9,216 / 9,216</td></tr><tr><td>压力块最小奇异值</td><td>2.78956e-8</td></tr><tr><td>MUMPS/KSP明细</td><td>未保留；严格JSON在<code>inf</code>处失败</td></tr></table>
<h2>证据</h2><ul><li><a href="summary.json">summary.json</a></li><li><a href="post_verification.json">post_verification.json</a></li><li><a href="failure.json">failure.json</a></li><li><a href="matrix_csr.npz">matrix_csr.npz</a></li><li><a href="rendering.json">rendering.json</a></li></ul>
<p>轮廓、三维、FSI、生长和ECM反馈均未运行；DG2受压平衡仍failed。</p></body></html>'''
    (root/'index.html').write_text(index,encoding='utf-8')
    audit={'status':'passed','formal_invocation_files_unchanged':len(identities),
           'independent_post_verification':'passed','visual_qa':rendering['visual_qa'],
           'postprocess_equilibrium_solves':0,'postprocess_global_factorizations':0,
           'targeted_tests':{'passed':51,'subtests_passed':21},
           'phase_bytes_before_manifest':sum(path.stat().st_size for path in root.rglob('*') if path.is_file())}
    save_json(root/'delivery_audit.json',audit)
    save_json(root/'manifest.json',package_manifest(root))
    register_result(workspace,root,'failed',digest(root/'manifest.json'))
    return {'status':'failed','delivery_status':'failed','post_verification':'passed',
            'root_cause':'not_evaluable','equilibrium_solves':0,
            'package_bytes':sum(path.stat().st_size for path in root.rglob('*') if path.is_file())}


def finalize_replay(workspace):
    """Seal verified same-matrix evidence, retaining the scientific failure."""
    from prl.result_store import register_result
    from prl.verification.fenicsx_linear_system_result import verify_replay_result
    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,REPLAY_RESULT)
    index=workspace/'project_control/result_index'/f'{root.name}.json'
    if index.exists():
        raise FileExistsError('Replay delivery already sealed')
    verification=verify_replay_result(root,workspace,save=True)
    if verification['status']!='passed':
        raise ValueError('Replay delivery verification failed')
    rendering=json.loads((root/'rendering.json').read_text())
    rendering.update(visual_qa='passed_v02_font_and_layout_review',
                     retained_draft='figures/FigS1S2_report_replay_v01_20260918.png')
    save_json(root/'rendering.json',rendering)
    summary={'status':'passed','diagnostic_delivery':'passed','scientific_pressure_space_status':'failed',
             'cause':verification['cause'],'mumps_infog_1':verification['mumps_infog_1'],
             'mumps_infog_2':verification['mumps_infog_2'],'mumps_icntl_14':verification['mumps_icntl_14'],
             'superlu_relative_residual':verification['superlu_independent_relative_residual'],
             'same_saved_matrix':True,'state_unchanged':True,'nonlinear_equilibrium_solves':0,
             'automatic_retries':0,'gpu':0,'contour':'not_run','fsi':'not_run','growth':'not_run',
             'figure':rendering['png'],'next_action':'proposed: same CSR, one MUMPS attempt with ICNTL(14)=100; no equilibrium solve',
             'caution':'workspace exhaustion is confirmed; a successful nonlinear pressure equilibrium and the 1% local volume gate remain unverified'}
    save_json(root/'summary.json',summary)
    for relative in ['src/prl/rendering/fenicsx_linear_system.py',
                     'src/prl/verification/fenicsx_linear_system_result.py',
                     'src/prl/runs/fenicsx_linear_system.py',
                     'project_control/ventricle_fem_mixed_linear_replay_execution_v01.md']:
        destination=root/'sources_at_delivery'/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(workspace/relative,destination)
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>F6-S1-S2 同矩阵诊断</title>
<style>body{{max-width:1100px;margin:32px auto;padding:0 20px;color:#183c2b;font:16px/1.7 'Microsoft YaHei',sans-serif}}img{{width:100%}}a{{color:#167153}}code{{background:#eef3ef;padding:3px}}</style>
<h1>F6-S1-S2：已定位MUMPS内部工作空间不足</h1>
<p>诊断交付passed；原DG2受压平衡仍failed。一次单CPU诊断，0个新平衡态，状态前后逐字节相同。</p>
<img src="{rendering['png']}" alt="三层圆环与同矩阵求解器对照">
<p>原配置返回<code>INFOG(1)=-9</code>，即内部数值工作数组过小；<code>INFOG(2)=1321</code>，<code>ICNTL(14)=20</code>。同一CSR的SuperLU线性解独立相对残量为3.17e-13。</p>
<p>这将直接失败原因从先前的数值奇异假设定位到工作空间预分配。矩阵条件数估计约1.09e9，仍需后续精度检查。当前证据不证明非线性平衡或1%体积门已经通过。</p>
<p><a href="post_verification.json">独立复核</a> · <a href="mumps_diagnosis.json">MUMPS明细</a> · <a href="superlu_diagnosis.json">SuperLU明细</a> · <a href="matrix_identity.json">新旧矩阵身份</a> · <a href="summary.json">阶段摘要</a></p>
<p>复算入口：prl.verification.fenicsx_linear_system_result.verify_replay_result；绘图入口：prl.rendering.fenicsx_linear_system.render_replay。原始CSR、解向量、输入、执行与绘图源快照均在本包中。</p>
<p>文档依据：<a href="https://mumps-solver.org/doc/userguide_5.9.1.pdf">MUMPS用户指南</a>及<a href="https://petsc.org/release/manualpages/Mat/MATSOLVERMUMPS/">PETSc MUMPS选项</a>。</p></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    save_json(root/'manifest.json',package_manifest(root))
    register_result(workspace,root,'passed',digest(root/'manifest.json'))
    return summary


def finalize_workspace(workspace):
    """Seal the one-factorization workspace check after notebook and visual QA."""
    from prl.result_store import register_result
    from prl.verification.fenicsx_linear_system_result import verify_workspace_result
    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,WORKSPACE_RESULT)
    if (root/'manifest.json').exists():
        raise FileExistsError('Workspace check is already sealed')
    report=verify_workspace_result(root,workspace,save=True)
    if report['verification_status']!='passed':
        raise ValueError('Saved evidence integrity failed')
    revision=next((root/'figures/FigS1S3_workspace_check').glob('FigS1S3_*')); prefix=revision.name
    methods=(revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    if '- 包状态: 最终包' not in methods:
        raise ValueError('Executed and visually reviewed final figure package required')
    rendering={'status':'passed','notebook':(revision/f'03_{prefix}_plot.ipynb').relative_to(root).as_posix(),
               'png':(revision/f'04_{prefix}.png').relative_to(root).as_posix(),
               'svg':(revision/f'05_{prefix}.svg').relative_to(root).as_posix(),
               'visual_qa':'passed','style_validation':'passed','new_equilibria':0,
               'temporary_cleanup':'not_authorized; figure_runtime retained'}
    summary={'status':report['linear_solver_status'],'engineering_delivery':'passed',
             'scientific_pressure_space_status':'failed','metrics':report['metrics'],
             'infog_1':report['mumps_infog_1'],'workspace_margin':report['mumps_icntl_14'],
             'matrix_assemblies':0,'mumps_factorizations':1,'superlu_factorizations':0,
             'nonlinear_equilibrium_solves':0,'state_updates':0,'automatic_retries':0,'gpu':0,
             'host_preflight_attempts':2,'scientific_containers':1,
             'next_action':'proposed bounded original ring first-pressure nonlinear qualification with ICNTL(14)=100',
             'caution':'The saved linear tangent is qualified, not the nonlinear equilibrium or 1% local-volume gate.'}
    save_json(root/'rendering.json',rendering); save_json(root/'summary.json',summary)
    for relative in ['src/prl/rendering/fenicsx_linear_system.py','src/prl/verification/fenicsx_linear_system_result.py',
                     'src/prl/runs/fenicsx_linear_system.py','project_control/ventricle_fem_mumps_workspace_execution_v01.md']:
        target=root/'sources_at_delivery'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(workspace/relative,target)
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>F6-S1-S3 工作空间验证</title>
<style>body{{max-width:1120px;margin:32px auto;padding:0 20px;font:16px/1.7 'Microsoft YaHei',sans-serif;color:#173e2e}}img{{width:100%}}a{{color:#176b4d}}</style>
<h1>同矩阵MUMPS工作空间验证：{report['linear_solver_status']}</h1>
<p>只调整ICNTL(14) 20→100，原矩阵、物理及FEM初值不变；0次非线性求解。原1%局部体积资格仍failed。</p>
<img src="{rendering['png']}" alt="三层实际圆环和同矩阵残量对照">
<p>独立相对残量：{report['metrics']['relative_residual']:.5e}；与保留SuperLU解相对差：{report['metrics']['relative_solution_difference']:.5e}。</p>
<p><a href="post_verification.json">独立复核</a> · <a href="mumps_diagnosis.json">MUMPS报告</a> · <a href="preflight_observation.json">主机准入超时记录</a> · <a href="{rendering['notebook']}">可复算Notebook</a> · <a href="summary.json">摘要</a></p>
<p>旧20%失败证据与所有父包保持；新增一次8.380秒单CPU容器，无GPU/重跑/安装/拉取/删除。下一步是另行恢复圆环首个受压非线性资格。</p></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    save_json(root/'manifest.json',package_manifest(root))
    register_result(workspace,root,report['linear_solver_status'],digest(root/'manifest.json'))
    return summary
