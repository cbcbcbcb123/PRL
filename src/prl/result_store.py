"""One approved external result root; historical evidence stays in place."""
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import stat

from .storage import scan_workspace,evaluate_storage

POLICY=Path('project_control/result_storage_policy.json')


def _no_links(path):
    for item in [path,*path.parents]:
        if item.exists() or item.is_symlink():
            attributes=getattr(item.lstat(),'st_file_attributes',0)
            if item.is_symlink() or attributes & getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0):
                raise ValueError('Linked/reparse result path is not authorized: '+str(item))


def policy(workspace):
    data=json.loads((Path(workspace)/POLICY).read_text(encoding='utf-8'))
    root=Path(data['root'])
    if data['status']!='approved' or not root.is_absolute() or root==Path(root.anchor):
        raise ValueError('Explicit approved result root required')
    _no_links(root)
    root=root.resolve(strict=True)
    if not root.is_dir() or root.is_relative_to(Path(workspace).resolve()):
        raise ValueError('Result root must be an existing separate directory')
    if data['fixed_stage_limit_bytes'] is not None:
        raise ValueError('External store uses disk-free admission, not a fixed stage cap')
    return data,root


def result_path(workspace,relative,new=False):
    """Explicit legacy location or external counterpart; never ambiguous fallback."""
    workspace=Path(workspace).resolve(strict=True)
    relative=Path(relative)
    if relative.is_absolute() or len(relative.parts)<2 or relative.parts[0]!='results' or '..' in relative.parts:
        raise ValueError('Expected a contained results/<stage path> identifier')
    _,store=policy(workspace)
    external=store.joinpath(*relative.parts[1:]); legacy=workspace/relative
    _no_links(external); _no_links(legacy)
    if not external.resolve().is_relative_to(store):
        raise ValueError('Result target escaped approved root')
    if new:
        if legacy.exists() or external.exists():
            raise FileExistsError('Stage already exists; relocation does not authorize rerunning it')
        return external
    if legacy.exists() and external.exists():
        raise ValueError('Ambiguous duplicate result identity')
    if legacy.exists():
        return legacy
    if external.exists():
        return external
    raise FileNotFoundError('Result not found at either explicitly declared location')


def disk_admission(directory,planned_new_bytes,stop_reserve_bytes=64*1024**2,free_floor_bytes=10*1024**3):
    if min(planned_new_bytes,stop_reserve_bytes,free_floor_bytes)<0:
        raise ValueError('Nonnegative disk forecast/reserves required')
    disk=shutil.disk_usage(directory)
    required=planned_new_bytes+stop_reserve_bytes+free_floor_bytes
    return {'status':'passed' if disk.free>=required else 'blocked','can_start':disk.free>=required,
            'mode':'external_disk_free','fixed_stage_limit_bytes':None,'disk_total_bytes':disk.total,
            'disk_free_bytes':disk.free,'required_free_bytes':required,'planned_new_bytes':planned_new_bytes,
            'stop_reserve_bytes':stop_reserve_bytes,'disk_free_floor_bytes':free_floor_bytes}


def result_admission(workspace,planned_new_bytes=0,stop_reserve_bytes=None):
    data,root=policy(workspace)
    reserve=max(data['minimum_stop_reserve_bytes'],stop_reserve_bytes or 0)
    report=disk_admission(root,planned_new_bytes,reserve,data['disk_free_floor_bytes'])
    # A small allowance for new code/control records, not for external arrays.
    repository=evaluate_storage(scan_workspace(Path(workspace)),planned_new_bytes=1024**2,stop_reserve_bytes=0)
    report.update({'root':str(root),'repository':repository,'usage':asdict(scan_workspace(root))})
    if not repository['can_start'] or report['usage']['scan_errors'] or report['usage']['skipped_reparse_points']:
        report.update(status='blocked',can_start=False)
    return report


def register_result(workspace,root,status,manifest_sha256):
    """Small immutable metadata record; no raw arrays in Git."""
    if status not in {'passed','failed','blocked','not_run','unknown'}:
        raise ValueError('Use a project execution status; scientific scope belongs in the result evidence')
    _,store=policy(workspace); root=Path(root).resolve(strict=True)
    if not root.is_relative_to(store) or root==store:
        raise ValueError('Only external stage directories can be registered')
    target=Path(workspace)/'project_control/result_index'/f'{root.name}.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as handle:
        json.dump({'status':status,'store_relative_path':root.relative_to(store).as_posix(),
                   'manifest_sha256':manifest_sha256,'raw_data_in_git':False},handle,indent=2)
