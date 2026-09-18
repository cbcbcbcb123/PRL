"""Create-only, manifest-protected controller for the approved pressure probe."""
import json
from pathlib import Path
import shutil
import subprocess
import time

from prl.fem.ring_geometry import configuration as ring_configuration
from prl.result_store import result_path,result_admission,disk_admission
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_contour import protected,RETAINED_MESH,RETAINED_MESH_SHA,SOURCE
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import read_docker,IMAGE,TAG,container_command,save_json,verify_container_settings

RESULT=Path('results/ventricle_fem/f6s1r_pressure_space_v01_20260918')
CONTRACT=Path('project_control/ventricle_fem_pressure_space_contract_v01.md')
RESUME_RESULT=Path('results/ventricle_fem/f6s1s4_ring_first_pressure_v01_20260918')
RESUME_CONTRACT=Path('project_control/ventricle_fem_ring_resume_contract_v01.md')
RESUME_V2_RESULT=Path('results/ventricle_fem/f6s1s4_ring_first_pressure_v02_20260918')
RESUME_V2_CONTRACT=Path('project_control/ventricle_fem_ring_resume_contract_v02.md')
PASSIVE_RESULT=Path('results/ventricle_fem/f6s1s5_ring_passive_v01_20260918')
PASSIVE_CONTRACT=Path('project_control/ventricle_fem_ring_passive_qualification_contract_v01.md')


def pressure_target(resume_first_ring=False,resume_revision=1,complete_passive_ring=False):
    if complete_passive_ring:
        if resume_first_ring or resume_revision!=1:
            raise ValueError('Choose only one bounded pressure execution mode')
        return PASSIVE_RESULT,PASSIVE_CONTRACT
    if resume_revision not in (1,2) or (resume_revision!=1 and not resume_first_ring):
        raise ValueError('Resume revision requires the explicitly bounded resume mode')
    if not resume_first_ring:
        return RESULT,CONTRACT
    return (RESUME_V2_RESULT,RESUME_V2_CONTRACT) if resume_revision==2 else (RESUME_RESULT,RESUME_CONTRACT)


def configuration(resume_first_ring=False,resume_revision=1,complete_passive_ring=False):
    pressure_target(resume_first_ring,resume_revision,complete_passive_ring)
    cfg=ring_configuration()
    cfg.update(schema_version='prl.pressure_space_diagnostic.v1',pressure_space='DG2',
               passive_loads=[0.,.02],active_peak=0.,meshes=[cfg['meshes'][0]],
               scope='finite bulk, plane strain, same geometry; no physiological clock or 3D claim',
               objects=['ring','contour'],maximum_equilibrium_solves=4,
               resources={'seconds':1200,'threads':1,'gpu':0,'automatic_retries':0})
    if resume_first_ring:
        cfg.update(resume_first_ring=True,retain_solver_iterates=True,objects=['ring'],
                   passive_loads=[.02],maximum_equilibrium_solves=1,
                   scope='one original first-pressure ring equilibrium from retained accepted zero; no zero rerun')
        cfg['solver']['mat_mumps_icntl_14']=100
    if resume_revision==2:
        cfg.update(resume_revision=2,runtime_interface_gate=True)
    if complete_passive_ring:
        original=ring_configuration()
        cfg.update(complete_passive_ring=True,retain_solver_iterates=True,objects=['ring'],
                   geometry_kind='ring',meshes=original['meshes'],passive_loads=original['passive_loads'],
                   execution_plan={'M0':[2,3,4],'M1':[0,1,2,3,4]},maximum_equilibrium_solves=8,
                   scope='complete original passive ring sequence on two meshes; reuse M0 zero and first pressure; not physiological time')
        cfg['solver']['mat_mumps_icntl_14']=100
    return cfg


def run_pressure(workspace,resume_first_ring=False,resume_revision=1,complete_passive_ring=False):
    workspace=Path(workspace).resolve(strict=True)
    target,contract=pressure_target(resume_first_ring,resume_revision,complete_passive_ring)
    root=result_path(workspace,target,new=True)
    if not (workspace/contract).is_file() or (not resume_first_ring and not complete_passive_ring and digest(workspace/RETAINED_MESH)!=RETAINED_MESH_SHA):
        raise ValueError('Contract or retained mesh missing/changed')
    version=json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server') or read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned local runtime unavailable; no restart, install or pull permitted')
    admission=result_admission(workspace,256*1024**2,64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    parents=protected(workspace,fine=True)
    if resume_first_ring or complete_passive_ring:
        from prl.runs.fenicsx_linear_system import WORKSPACE_RESULT
        source=result_path(workspace,RESULT)
        qualified=result_path(workspace,WORKSPACE_RESULT)
        external_parents=json.loads((qualified/'source_result_preflight.json').read_text())
        packages=[source,qualified]
        if resume_revision==2 or complete_passive_ring:
            packages.append(result_path(workspace,RESUME_RESULT))
        if complete_passive_ring:
            accepted_parent=result_path(workspace,RESUME_V2_RESULT)
            packages.append(accepted_parent)
            accepted_report=json.loads((accepted_parent/'post_verification.json').read_text())
            if accepted_report['status']!='passed' or accepted_report['accepted_equilibria']!=1 or accepted_report['runtime_interface']['status']!='passed':
                raise ValueError('Original first-pressure/interface prerequisite not passed')
        for package in packages:
            manifest=json.loads((package/'manifest.json').read_text())
            if not all(digest(package/item['path'])==item['sha256'] for item in manifest['files']):
                raise ValueError('Retained source manifest changed')
            external_parents.update({str(p):digest(p) for p in package.rglob('*') if p.is_file()})
        if not all(digest(path)==sha for path,sha in external_parents.items()):
            raise ValueError('Ancestor evidence changed')
        qualification=json.loads((qualified/'post_verification.json').read_text())
        if qualification['verification_status']!='passed' or qualification['linear_solver_status']!='passed':
            raise ValueError('Original workspace-margin prerequisite not passed')
    else:
        fine=result_path(workspace,Path('results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917'))
        external_parents={str(p):digest(p) for p in fine.rglob('*') if p.is_file()}
    with scientific_lock(workspace):
        root.mkdir(parents=True,exist_ok=False)
        save_json(root/'storage_preflight.json',admission)
        save_json(root/'configuration.json',configuration(resume_first_ring,resume_revision,complete_passive_ring))
        save_json(root/'docker_version.json',version)
        save_json(root/'protected_preflight.json',parents)
        save_json(root/'external_protected_preflight.json',external_parents)
        if complete_passive_ring:
            retained=root/'retained_passive'; retained.mkdir()
            copies=[('ring/raw/M0_mesh.npz','M0_mesh.npz'),
                    ('configuration.json','configuration.json'),('post_verification.json','verification.json')]
            for extension in ['npz','json']:
                copies.extend([(f'retained_zero/state.{extension}',f'M0_state_passive_0.{extension}'),
                               (f'ring/raw/M0_state_passive_1.{extension}',f'M0_state_passive_1.{extension}')])
            for before,after in copies:
                shutil.copyfile(accepted_parent/before,retained/after)
            control=workspace/'results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917'
            comparison=root/'comparison'; comparison.mkdir()
            shutil.copyfile(control/'configuration.json',comparison/'configuration.json')
            for name in ['M0','M1']:
                shutil.copyfile(control/'raw'/f'{name}_mesh.npz',comparison/f'{name}_mesh.npz')
                for index in range(5):
                    for extension in ['npz','json']:
                        filename=f'{name}_state_passive_{index}.{extension}'
                        shutil.copyfile(control/'raw'/filename,comparison/filename)
        elif resume_first_ring:
            retained=root/'retained_zero'; retained.mkdir()
            for before,after in [('ring/raw/M0_mesh.npz','mesh.npz'),('ring/raw/M0_state_passive_0.npz','state.npz'),
                                 ('ring/raw/M0_state_passive_0.json','state.json'),('configuration.json','configuration.json')]:
                shutil.copyfile(source/before,retained/after)
            shutil.copyfile(qualified/'post_verification.json',root/'workspace_prerequisite.json')
        else:
            shutil.copyfile(workspace/RETAINED_MESH,root/'retained_mesh.npz')
            shutil.copyfile(workspace/SOURCE,root/'geometry_source.npz')
        comparisons=[] if complete_passive_ring else [('ring','f6s0_fenicsx_ring_active_v01_20260917')]
        if not resume_first_ring and not complete_passive_ring:
            comparisons.append(('contour','f6s1p_retained_passive_v01_20260917'))
        for kind,name in comparisons:
            source=workspace/'results/ventricle_fem'/name
            target=root/'comparison'/kind; target.mkdir(parents=True)
            for before,after in [('raw/M0_mesh.npz','mesh.npz'),('raw/M0_state_passive_1.npz','state.npz'),
                                 ('raw/M0_state_passive_1.json','state.json'),('configuration.json','configuration.json')]:
                shutil.copyfile(source/before,target/after)
        sources=['src/prl/fem/fenicsx_pressure.py','src/prl/fem/fenicsx_ring.py','src/prl/fem/ring_geometry.py',
                 'src/prl/verification/fenicsx_ring.py','src/prl/verification/fenicsx_pressure.py',
                 'src/prl/verification/fenicsx_contour.py','src/prl/fem/fenicsx_contour.py',
                 'src/prl/runs/fenicsx_pressure.py','src/prl/runs/fenicsx_contour.py','src/prl/runs/fenicsx_runtime.py',
                 'src/prl/runs/fenicsx_ring.py','src/prl/runs/fem_finite_strain.py','src/prl/result_store.py',
                 'project_control/result_storage_policy.json',contract.as_posix()]
        for relative in sources:
            destination=root/'sources_at_execution'/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(workspace/relative,destination)
        save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in sources})
        name=f'prl-f6s1s4-ring-first-pressure-v{resume_revision:02d}-20260918' if resume_first_ring else 'prl-f6s1r-pressure-space-v01-20260918'
        if complete_passive_ring:
            name='prl-f6s1s5-ring-passive-v01-20260918'
        args=container_command(workspace,name,'/workspace/src/prl/fem/fenicsx_pressure.py',root)
        save_json(root/'command.json',args)
        save_json(root/'science_started.json',{'invocations':1,'container':name,'automatic_retries':0})
        started=time.monotonic(); reason=None
        with (root/'stdout.log').open('x',encoding='utf-8') as stdout,(root/'stderr.log').open('x',encoding='utf-8') as stderr:
            process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
            try:
                while process.poll() is None:
                    disk=disk_admission(root,0)
                    if time.monotonic()-started>1200 or not disk['can_start']:
                        reason='deadline' if time.monotonic()-started>1200 else 'disk free floor'
                        read_docker('stop','--time','5',name); process.wait(timeout=20); break
                    time.sleep(.5)
            except BaseException:
                read_docker('stop','--time','5',name); process.wait(timeout=20)
                raise
        inspection=json.loads(read_docker('inspect',name))[0]
        save_json(root/'container_inspect.json',inspection)
        settings=verify_container_settings(inspection)
        unchanged=all(digest(workspace/p)==h for p,h in parents.items()) and all(digest(p)==h for p,h in external_parents.items())
        report={'status':'passed' if process.returncode==0 and all(settings.values()) and unchanged and reason is None else 'failed',
                'exit_code':process.returncode,'stop_reason':reason,'container_checks':settings,
                'protected_parent_files':len(parents)+len(external_parents),'parents_unchanged':unchanged,
                'scientific_invocations':1,'automatic_retries':0,'gpu':0,'elapsed_seconds':time.monotonic()-started}
        save_json(root/'execution.json',report)
        save_json(root/'formal_invocation_manifest.json',package_manifest(root))
        return report
